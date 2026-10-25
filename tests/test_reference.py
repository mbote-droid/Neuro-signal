"""F-07: common average reference only for referential montages."""

from __future__ import annotations

import numpy as np
import pytest

from neurosignal.core.recording import Recording
from neurosignal.preprocessing.reference import CommonAverage


def _rec(names, bad=()):
    g = np.random.default_rng(0)
    return Recording(
        data=g.standard_normal((len(names), 1000)) + 5.0, sfreq=100.0, channels=names,
        bad_channels=bad,
    )  # fmt: skip


def test_car_zeroes_the_mean_of_good_channels_and_lowers_rank():
    rec = _rec(("Fz", "Cz", "Pz", "Oz"))
    out = CommonAverage()(rec)
    np.testing.assert_allclose(out.data.mean(axis=0), 0, atol=1e-12)
    assert np.linalg.matrix_rank(out.data) == rec.n_channels - 1
    assert out.history[-1]["applied"] is True


def test_bad_channel_excluded_from_the_average():
    rec = _rec(("Fz", "Cz", "Pz", "Oz"), bad=("Oz",))
    rec = rec.evolve(data=rec.data + np.array([[0], [0], [0], [1000.0]]))
    out = CommonAverage()(rec)
    good = out.data[:3]
    np.testing.assert_allclose(good.mean(axis=0), 0, atol=1e-12)
    assert np.all(np.abs(good) < 50)  # the 1000 µV channel did not leak in


def test_bipolar_montage_left_unchanged():
    rec = _rec(("FP1-F7", "F7-T7", "T7-P7", "P7-O1"))
    assert rec.is_bipolar
    out = CommonAverage()(rec)
    np.testing.assert_array_equal(out.data, rec.data)
    assert out.history[-1]["applied"] is False


@pytest.mark.parametrize(
    ("names", "bipolar"),
    [
        (["FP1-F7", "F7-T7", "T7-P7", "ECG"], True),  # a non-EEG channel is ignored
        (["FP1-F7", "F7-T7", "T7-P7", "-", "--0"], True),  # placeholders too
        (["FP1-F7", "F7-T7", "T8-P8-0", "T8-P8-1"], True),  # MNE's duplicate suffix
        (["Fp1-A1", "Fp2-A2", "C3-A1", "C4-A2"], False),  # common ear references
        (["Fp1-REF", "Fp2-REF", "Cz-REF"], False),
        (["Fp1", "Fp2", "Cz"], False),
    ],
)
def test_montage_detection(names, bipolar):
    """ISSUE-017: one ECG channel used to make a bipolar montage 'referential'."""
    rec = Recording(data=np.zeros((len(names), 10)), sfreq=256.0, channels=tuple(names))
    assert rec.is_bipolar is bipolar


def test_average_reference_excludes_non_eeg_channels():
    data = np.zeros((4, 256))
    data[3] = 1000.0  # a large ECG channel must not leak into the average
    rec = Recording(data=data, sfreq=256.0, channels=("Fp1", "Cz", "O1", "ECG"))
    out = CommonAverage().process(rec)
    assert np.allclose(out.data[:3], 0.0)
