"""F-12, V-06, V-10: event detector and event scoring."""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np

from neurosignal.core.config import PipelineConfig
from neurosignal.detection.events import Interval, score_events
from neurosignal.detection.seizure import DetectorParams, detect
from neurosignal.pipeline import detector_params, preprocess
from neurosignal.synth.eeg import SynthSpec, make_recording
from validation.common import EVAL_SEEDS, RESULTS, TUNING_SEEDS


def _clean(seed, **kw):
    rec, gt = make_recording(seed, SynthSpec(**{"duration_s": 300.0, **kw}))
    return preprocess(rec, PipelineConfig()), gt


def test_injected_discharge_detected_with_correct_rhythm():
    """F-12."""
    clean, gt = _clean(21, n_events=1, snr_db=10.0)
    events = detect(clean, detector_params(PipelineConfig()))
    truth = Interval(gt.events[0].onset_s, gt.events[0].offset_s)
    hits = [e for e in events if e.interval().overlaps(truth)]
    assert hits
    assert 2.0 <= hits[0].dominant_freq_hz <= 5.0
    assert abs(hits[0].onset_s - truth.onset_s) < 5.0


def test_background_alone_gives_no_detections():
    clean, _ = _clean(22, n_events=0, blinks_per_min=15.0)
    assert detect(clean, detector_params(PipelineConfig())) == []


def test_negative_control_rhythm_gate_removes_muscle_false_alarms():
    """Without the 2-13 Hz rhythm gate, muscle bursts become detections."""
    p = detector_params(PipelineConfig())
    gated = ungated = 0
    for seed in range(30, 36):
        clean, _ = _clean(seed, n_events=0, muscle_per_min=4.0)
        gated += len(detect(clean, p))
        ungated += len(detect(clean, replace(p, rhythm_hz=(0.0, 100.0))))
    assert ungated >= 3 * max(gated, 1)


def test_score_events_any_overlap():
    truth = [Interval(10, 20), Interval(50, 60)]
    det = [Interval(15, 25), Interval(30, 35), Interval(18, 19)]
    s = score_events(truth, det, 3600.0)
    assert (s.hits, s.false_detections, s.n_detected) == (1, 1, 3)
    assert s.sensitivity == 0.5
    assert s.false_per_hour == 1.0
    assert s.onset_latencies_s == (5,)


def test_tuning_and_evaluation_seeds_disjoint():
    """V-10."""
    assert not set(TUNING_SEEDS) & set(EVAL_SEEDS)


def test_config_thresholds_come_from_the_tuning_result():
    """V-10: the shipped thresholds are the ones the tuning rule selected."""
    path = RESULTS / "detector_tuning.json"
    sel = json.loads(path.read_text())["selected"]
    cfg = PipelineConfig()
    assert cfg.ll_z_threshold == sel["z_threshold"]
    assert cfg.ll_channel_fraction == sel["channel_fraction"]
    assert cfg.ll_min_duration_s == sel["min_duration_s"]
    assert list(cfg.rhythm_band_hz) == sel["rhythm_hz"]
    assert cfg.ll_merge_gap_s == sel["merge_gap_s"]


def test_detector_params_defaults_match_config():
    cfg = PipelineConfig()
    d = DetectorParams()
    assert (d.z_threshold, d.channel_fraction, d.min_duration_s, d.rhythm_hz) == (
        cfg.ll_z_threshold, cfg.ll_channel_fraction, cfg.ll_min_duration_s, cfg.rhythm_band_hz,
    )  # fmt: skip
    assert np.isclose(d.window_s, cfg.ll_window_s)


def test_rhythm_gate_reads_the_fundamental_not_a_harmonic():
    """A 3 Hz spike-wave train over a 1/f background: the background-normalised
    spectrum peaks on a harmonic, but the fundamental is 3 Hz."""
    from neurosignal.core.seeds import rng
    from neurosignal.detection.seizure import background_spectra, dominant_frequency
    from neurosignal.synth.eeg import ChannelSpectrum, shaped_noise, spike_wave

    fs = 256.0
    t = np.arange(int(60 * fs)) / fs
    bg = shaped_noise(ChannelSpectrum(1.5, 2.0), t.size, fs, rng(9))
    event = bg + 3 * np.std(bg) * spike_wave(t, 3.0, 3.0)
    ref = background_spectra(bg[None, :], fs)[0]
    assert abs(dominant_frequency(event[None, :], fs, (1.0, 20.0), ref) - 3.0) <= 0.5
