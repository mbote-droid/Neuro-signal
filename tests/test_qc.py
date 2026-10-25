"""F-03, F-04, F-05, V-04: channel quality control."""

from __future__ import annotations

import numpy as np

from neurosignal.core.config import PipelineConfig
from neurosignal.core.recording import Recording
from neurosignal.pipeline import preprocess
from neurosignal.preprocessing.qc import (
    AmplitudeChannels,
    FlatChannels,
    line_noise_ratio,
    longest_flat_run_s,
)
from neurosignal.synth.eeg import SynthSpec, make_recording

FS = 256.0


def test_flat_run_length_measured():
    x = np.random.default_rng(0).standard_normal(int(30 * FS)) * 10
    x[1000 : 1000 + int(7 * FS)] = 3.0
    assert abs(longest_flat_run_s(x, FS, 0.1) - 7.0) < 0.05


def test_flat_channel_over_5_s_marked_bad_under_5_s_kept():
    """F-03."""
    g = np.random.default_rng(1)
    x = g.standard_normal((3, int(60 * FS))) * 20
    x[0, 100 : 100 + int(6 * FS)] = 1.0  # 6 s flat
    x[1, 100 : 100 + int(4 * FS)] = 1.0  # 4 s flat
    rec = Recording(data=x, sfreq=FS, channels=("A", "B", "C"))
    out = FlatChannels(0.1, 5.0)(rec)
    assert out.bad_channels == ("A",)


def test_noisy_and_low_channels_marked():
    """F-04."""
    g = np.random.default_rng(2)
    x = g.standard_normal((8, int(60 * FS))) * 20
    x[2] *= 8
    x[5] *= 0.1
    rec = Recording(data=x, sfreq=FS, channels=tuple("ABCDEFGH"))
    stage = AmplitudeChannels(5.0, 0.2)
    out = stage(rec)
    assert set(out.bad_channels) == {"C", "F"}
    assert "C" in stage.noisy and "F" in stage.low


def test_line_noise_ratio_falls_after_cleaning():
    """F-05: measured before and after; the notch removes most of it."""
    rec, _ = make_recording(3, SynthSpec(duration_s=60, line_noise_uv=20.0))
    before = line_noise_ratio(rec.data, rec.sfreq, 50.0)
    after = line_noise_ratio(preprocess(rec, PipelineConfig()).data, rec.sfreq, 50.0)
    assert np.median(before) > 0.05
    assert np.median(after) < 0.01 * np.median(before)


def test_bad_channel_recall_and_precision_on_synthetic_recordings():
    """V-04 (subset; the full campaign uses 100 recordings)."""
    tp = fp = fn = 0
    for seed in range(12):
        rec, gt = make_recording(
            500 + seed, SynthSpec(duration_s=60, n_flat=seed % 2, n_noisy=1 + seed % 2)
        )
        found = set(preprocess(rec, PipelineConfig()).bad_channels)
        truth = set(gt.bad_channels)
        tp += len(found & truth)
        fp += len(found - truth)
        fn += len(truth - found)
    assert tp / (tp + fn) >= 0.95
    assert tp / (tp + fp) >= 0.95


def test_a_flat_stretch_at_the_edge_is_not_doubled():
    """The filters reflect at the ends: a 3 s flat start was measured as 6 s and
    the channel marked bad (ISSUE-016)."""
    from neurosignal.preprocessing.qc import longest_flat_run_s

    fs = 256
    x = np.random.default_rng(0).normal(0, 20, fs * 60)
    start, end, middle = x.copy(), x.copy(), x.copy()
    start[: 3 * fs] = 0
    end[-3 * fs :] = 0
    middle[20 * fs : 23 * fs] = 0
    for signal in (start, end, middle):
        assert longest_flat_run_s(signal, fs, 0.5) < 3.1
