"""Readers: one adapter per file format behind one function (ADR-002).

Every adapter returns a `Recording` in microvolts with no identifying
header fields (S-02): only the signal, sampling rate, channel names and
annotations cross the boundary. The size limit and extension check run
before any parser touches the file (F-02, S-01).
"""

from __future__ import annotations

import re
import zipfile
from collections.abc import Callable
from pathlib import Path

import numpy as np

from neurosignal.core.provenance import sha256_file
from neurosignal.core.recording import Annotation, Recording
from neurosignal.core.registry import Registry

DEFAULT_MAX_BYTES = 2 * 1024**3

Reader = Callable[[Path], Recording]
READERS: Registry[Reader] = Registry("reader")


class RefusedFile(ValueError):
    """The file was refused before or during parsing."""


def read(path: str | Path, max_bytes: int = DEFAULT_MAX_BYTES) -> Recording:
    """Read any supported file; refuse unknown extensions and oversized files."""
    path = Path(path)
    if not path.is_file():
        raise RefusedFile(f"not a regular file: {path}")
    ext = path.suffix.lower()
    if ext not in READERS.keys():  # noqa: SIM118 (Registry, not dict)
        raise RefusedFile(f"unsupported extension {ext!r}; supported: {READERS.keys()}")
    size = path.stat().st_size
    if size > max_bytes:
        raise RefusedFile(f"file is {size} bytes, above the {max_bytes}-byte limit")
    try:
        if ext == ".npz" and (inflated := _npz_inflated_bytes(path)) > max_bytes:
            raise RefusedFile(
                f"{path.name} expands to {inflated} bytes, above the {max_bytes}-byte limit"
            )
        rec = READERS.get(ext)(path)
    except RefusedFile:
        raise
    except MemoryError:
        raise RefusedFile(f"not enough memory to read {path.name}") from None
    except Exception as exc:  # a damaged file must be refused, not crash (ISSUE-014)
        raise RefusedFile(f"could not read {ext} file {path.name}: {exc}") from exc
    if not np.isfinite(rec.data).all():
        raise RefusedFile(f"{path.name} contains non-finite samples (NaN or infinity)")
    digest = sha256_file(path)
    return rec.evolve(
        {"stage": "read", "format": ext, "bytes": size},
        source_sha256=digest,
        subject_id=f"rec-{digest[:12]}",
    )


def _npz_inflated_bytes(path: Path) -> int:
    """Bytes the arrays of an .npz occupy once loaded, from each .npy header and
    without decompressing the data: a small compressed file can expand a
    thousandfold, past the size limit checked on disk (ISSUE-018)."""
    total = 0
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            with archive.open(info) as member:
                version = np.lib.format.read_magic(member)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(member)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(member)
                else:
                    raise RefusedFile(f"unsupported .npy version {version} in {path.name}")
                total += int(np.prod(shape, dtype=np.int64)) * dtype.itemsize
    return total


def _from_mne(raw: object) -> Recording:
    import mne

    assert isinstance(raw, mne.io.BaseRaw)
    raw.pick("data", exclude=())
    data = raw.get_data(units="uV").astype(np.float64, copy=False)
    names, data = _drop_duplicate_channels(list(raw.ch_names), data)
    annotations = tuple(
        Annotation(float(a["onset"]), float(a["duration"]), str(a["description"])[:200])
        for a in raw.annotations
    )
    return Recording(
        data=np.ascontiguousarray(data),
        sfreq=float(raw.info["sfreq"]),
        channels=tuple(names),
        annotations=annotations,
    )


_DUP = re.compile(r"^(?P<base>.+)-(?P<n>\d+)$")


def _drop_duplicate_channels(names: list[str], data: np.ndarray) -> tuple[list[str], np.ndarray]:
    """MNE renames repeated labels to `X-0`, `X-1`. When the copies carry
    identical samples (CHB-MIT repeats T8-P8), keep the first under the
    original label; otherwise keep all of them as renamed."""
    bases = [m.group("base") if (m := _DUP.match(n)) else n for n in names]
    keep: list[int] = []
    out: list[str] = []
    for i, name in enumerate(names):
        copies = [j for j, b in enumerate(bases) if b == bases[i] and _DUP.match(names[j])]
        if len(copies) > 1 and all(np.array_equal(data[copies[0]], data[j]) for j in copies):
            if i == copies[0]:
                keep.append(i)
                out.append(bases[i])
            continue
        keep.append(i)
        out.append(name)
    return out, data[keep]


@READERS.register(".edf")
def _read_edf(path: Path) -> Recording:
    import mne

    return _from_mne(mne.io.read_raw_edf(path, preload=True, verbose="error"))


@READERS.register(".bdf")
def _read_bdf(path: Path) -> Recording:
    import mne

    return _from_mne(mne.io.read_raw_bdf(path, preload=True, verbose="error"))


@READERS.register(".vhdr")
def _read_brainvision(path: Path) -> Recording:
    import mne

    return _from_mne(mne.io.read_raw_brainvision(path, preload=True, verbose="error"))


@READERS.register(".npz")
def _read_npz(path: Path) -> Recording:
    """Native format: `data` (µV), `sfreq`, `channels`, optional annotation arrays."""
    try:
        with np.load(path, allow_pickle=False) as z:
            data = np.asarray(z["data"], dtype=np.float64)
            sfreq = float(z["sfreq"])
            channels = tuple(str(c) for c in z["channels"])
            ann: tuple[Annotation, ...] = ()
            if "ann_onset" in z.files:
                ann = tuple(
                    Annotation(float(o), float(d), str(s))
                    for o, d, s in zip(
                        z["ann_onset"], z["ann_duration"], z["ann_description"], strict=True
                    )
                )
    except (ValueError, KeyError) as exc:
        raise RefusedFile(f"invalid .npz recording: {exc}") from exc
    return Recording(data=data, sfreq=sfreq, channels=channels, annotations=ann)


def write_npz(rec: Recording, path: str | Path) -> None:
    np.savez_compressed(
        path,
        data=rec.data,
        sfreq=np.float64(rec.sfreq),
        channels=np.array(rec.channels, dtype=str),
        ann_onset=np.array([a.onset_s for a in rec.annotations], dtype=float),
        ann_duration=np.array([a.duration_s for a in rec.annotations], dtype=float),
        ann_description=np.array([a.description for a in rec.annotations], dtype=str),
    )
