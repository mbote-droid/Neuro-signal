"""Bug hunt: fuzzing the readers with damaged files (S-01, F-02).

A damaged or hostile file must either be read into a valid Recording or be
refused with RefusedFile: never another exception (a traceback in the CLI),
never a hang, and never a Recording holding NaN or infinite samples.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from neurosignal.io.readers import RefusedFile, read, write_npz
from neurosignal.synth.eeg import SynthSpec, make_recording
from tests.conftest import write_edf

FUZZ = settings(
    max_examples=60, deadline=10_000, suppress_health_check=[HealthCheck.function_scoped_fixture]
)


def _valid_edf(path: Path) -> bytes:
    rng = np.random.default_rng(0)
    write_edf(path, rng.normal(0, 20, (3, 256 * 4)), 256, ["Fz", "Cz", "Pz"])
    return path.read_bytes()


def _outcome(path: Path) -> str:
    try:
        rec = read(path)
    except RefusedFile:
        return "refused"
    assert np.isfinite(rec.data).all(), "a Recording with non-finite samples"
    return "read"


@FUZZ
@given(cut=st.floats(0.0, 1.0))
def test_truncated_edf(tmp_path, cut):
    good = _valid_edf(tmp_path / "good.edf")
    bad = tmp_path / "bad.edf"
    bad.write_bytes(good[: int(len(good) * cut)])
    _outcome(bad)


@FUZZ
@given(flips=st.lists(st.tuples(st.integers(0, 1023), st.integers(0, 255)), min_size=1, max_size=8))
def test_edf_with_damaged_header_bytes(tmp_path, flips):
    data = bytearray(_valid_edf(tmp_path / "good.edf"))
    for pos, value in flips:
        data[pos] = value
    bad = tmp_path / "bad.edf"
    bad.write_bytes(bytes(data))
    _outcome(bad)


# header fields a hostile file would lie about: (offset, width) in the EDF header
FIELDS = {"n_records": (236, 8), "record_seconds": (244, 8), "n_signals": (252, 4)}


@FUZZ
@given(
    field=st.sampled_from(sorted(FIELDS)),
    value=st.sampled_from(["-1", "0", "999999", "1e9", "nan", "abc", "", "0.0001"]),
)
def test_edf_with_lying_header_fields(tmp_path, field, value):
    data = bytearray(_valid_edf(tmp_path / "good.edf"))
    offset, width = FIELDS[field]
    data[offset : offset + width] = value.ljust(width)[:width].encode()
    bad = tmp_path / "bad.edf"
    bad.write_bytes(bytes(data))
    _outcome(bad)


@FUZZ
@given(signal_field=st.sampled_from(["phys_min", "phys_max", "dig_min", "dig_max"]))
def test_edf_with_degenerate_scaling(tmp_path, signal_field):
    """Physical or digital minimum equal to its maximum makes the scale 0/0."""
    data = bytearray(_valid_edf(tmp_path / "good.edf"))
    n = 3
    base = 256 + n * (16 + 80 + 8)  # labels, transducer, units
    order = ["phys_min", "phys_max", "dig_min", "dig_max"]
    start = base + order.index(signal_field) * 8 * n
    partner = base + (order.index(signal_field) ^ 1) * 8 * n
    data[start : start + 8 * n] = data[partner : partner + 8 * n]
    bad = tmp_path / "bad.edf"
    bad.write_bytes(bytes(data))
    _outcome(bad)


@FUZZ
@given(junk=st.binary(min_size=0, max_size=4096), ext=st.sampled_from([".edf", ".bdf", ".npz"]))
def test_random_bytes(tmp_path, junk, ext):
    bad = tmp_path / f"bad{ext}"
    bad.write_bytes(junk)
    _outcome(bad)


@FUZZ
@given(cut=st.floats(0.0, 0.99))
def test_truncated_npz(tmp_path, cut):
    rec, _ = make_recording(0, SynthSpec(duration_s=20.0, n_events=0))
    good = tmp_path / "good.npz"
    write_npz(rec, good)
    raw = good.read_bytes()
    bad = tmp_path / "bad.npz"
    bad.write_bytes(raw[: int(len(raw) * cut)])
    _outcome(bad)


def test_brainvision_with_missing_data_file(tmp_path):
    header = tmp_path / "rec.vhdr"
    header.write_text(
        "Brain Vision Data Exchange Header File Version 1.0\n[Common Infos]\n"
        "DataFile=missing.eeg\nMarkerFile=missing.vmrk\nDataFormat=BINARY\n"
        "DataOrientation=MULTIPLEXED\nNumberOfChannels=1\nSamplingInterval=4000\n"
        "[Binary Infos]\nBinaryFormat=INT_16\n[Channel Infos]\nCh1=Fz,,0.1,µV\n"
    )
    assert _outcome(header) == "refused"


def test_npz_with_nan_samples_is_refused(tmp_path):
    rec, _ = make_recording(0, SynthSpec(duration_s=20.0, n_events=0))
    path = tmp_path / "nan.npz"
    write_npz(rec, path)
    with np.load(path, allow_pickle=False) as z:
        arrays = dict(z)
    arrays["data"] = arrays["data"].copy()
    arrays["data"][0, 100] = np.nan
    np.savez(path, **arrays)
    assert _outcome(path) == "refused"


def test_npz_decompression_bomb_is_refused_before_loading(tmp_path):
    """A 1000:1 compressible array: small on disk, large in memory (ISSUE-018)."""
    path = tmp_path / "bomb.npz"
    np.savez_compressed(
        path, data=np.zeros((4, 4_000_000)), sfreq=np.array(256.0), channels=np.array(["a"] * 4)
    )
    size = path.stat().st_size
    assert size < 1_000_000
    try:
        read(path, max_bytes=10 * size)
    except RefusedFile as exc:
        assert "expands to" in str(exc)
    else:
        raise AssertionError("bomb accepted")
