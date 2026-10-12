"""F-01, F-02, S-01, S-02, S-05: readers."""

from __future__ import annotations

import numpy as np
import pytest

from neurosignal.core.recording import Recording
from neurosignal.io.readers import RefusedFile, read, write_npz
from tests.conftest import write_edf

FS = 128


def _signal(n_ch: int = 3, seconds: int = 4) -> np.ndarray:
    t = np.arange(seconds * FS) / FS
    return np.stack([50 * np.sin(2 * np.pi * (5 + k) * t) for k in range(n_ch)])


def test_edf_roundtrip_in_microvolts(tmp_path):
    """F-01: EDF data arrive as float64 µV, (channels, samples)."""
    x = _signal()
    p = tmp_path / "rec.edf"
    write_edf(p, x, FS, ["Fz", "Cz", "Pz"])
    rec = read(p)
    assert rec.data.dtype == np.float64
    assert rec.data.shape == x.shape
    assert rec.channels == ("Fz", "Cz", "Pz")
    assert rec.sfreq == FS
    np.testing.assert_allclose(rec.data, x, atol=0.06)  # 0.1 µV quantisation


def test_units_are_microvolts(tmp_path):
    """F-01: a file stored in mV is converted to µV (x1000), not passed through."""
    x_mv = _signal() / 1000.0
    p = tmp_path / "mv.edf"
    write_edf(p, x_mv, FS, ["Fz", "Cz", "Pz"], unit="mV", phys_range=3.2767)
    rec = read(p)
    np.testing.assert_allclose(rec.data, x_mv * 1000.0, atol=0.06)


def test_identifying_header_fields_never_cross_the_boundary(tmp_path):
    """S-02: patient name and dates are not in the Recording or its history."""
    p = tmp_path / "id.edf"
    write_edf(p, _signal(), FS, ["Fz", "Cz", "Pz"], patient="X F 01-JAN-1970 Jane_Doe")
    rec = read(p)
    blob = repr(rec.annotations) + repr(rec.history) + rec.subject_id + repr(rec.channels)
    for secret in ("Jane_Doe", "1970", "secret-hospital", "2020"):
        assert secret not in blob
    assert rec.subject_id.startswith("rec-")


def test_duplicate_identical_channels_collapse(tmp_path):
    """F-01: CHB-MIT repeats T8-P8 with identical samples; keep one copy."""
    x = _signal(3)
    x[2] = x[1]
    p = tmp_path / "dup.edf"
    write_edf(p, x, FS, ["FP1-F7", "T8-P8", "T8-P8"])
    rec = read(p)
    assert rec.channels == ("FP1-F7", "T8-P8")
    assert rec.is_bipolar


def test_unknown_extension_refused(tmp_path):
    """F-02: no content sniffing."""
    p = tmp_path / "rec.csv"
    p.write_text("1,2,3\n")
    with pytest.raises(RefusedFile, match="unsupported extension"):
        read(p)


def test_size_limit_checked_before_parsing(tmp_path):
    """S-01: a file above the limit is refused, whatever it contains."""
    p = tmp_path / "big.edf"
    p.write_bytes(b"not an edf at all" * 100)
    with pytest.raises(RefusedFile, match="limit"):
        read(p, max_bytes=100)


def test_npz_roundtrip(tmp_path):
    rec = Recording(data=_signal(), sfreq=float(FS), channels=("A", "B", "C"))
    p = tmp_path / "r.npz"
    write_npz(rec, p)
    back = read(p)
    np.testing.assert_array_equal(back.data, rec.data)
    assert back.channels == rec.channels


def test_npz_with_object_array_refused(tmp_path):
    """S-05: pickled object arrays are never loaded."""
    p = tmp_path / "evil.npz"
    np.savez(p, data=np.array([object()], dtype=object), sfreq=128.0, channels=np.array(["A"]))
    with pytest.raises(RefusedFile):
        read(p)


def test_recording_rejects_wrong_dtype_and_shape():
    with pytest.raises(TypeError):
        Recording(data=np.zeros((2, 10), dtype=np.float32), sfreq=100.0, channels=("a", "b"))
    with pytest.raises(ValueError):
        Recording(data=np.zeros((2, 10)), sfreq=100.0, channels=("a",))
    with pytest.raises(ValueError):
        Recording(data=np.zeros((2, 10)), sfreq=100.0, channels=("a", "a"))
