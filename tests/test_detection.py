"""F-12, V-06, V-10: event detector and event scoring."""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np

from neurosignal.core.config import PipelineConfig
from neurosignal.detection.events import Interval, score_events
from neurosignal.detection.seizure import DetectorParams, detect, robust_rms
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


def test_clean_background_gives_no_detections():
    """Artifact-free background never produces a candidate. (With blinks,
    muscle and alpha bursts it does: that false-detection rate is measured in
    the validation campaign, not asserted away here; BUILD_JOURNAL ISSUE-011.)"""
    for seed in (22, 23, 24):
        clean, _ = _clean(seed, n_events=0)
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


# --------------------------------------------------------------- blink cue (§11)


def _cue_inputs(gains: dict[str, float], channels: tuple[str, ...], seed: int = 0):
    """Background noise on every channel plus a 1.5 Hz train with the given
    spatial gains between 40 and 60 s; returns (x, background RMS)."""
    rng = np.random.default_rng(seed)
    sfreq, n = 256.0, 256 * 120
    x = rng.normal(0.0, 10.0, (len(channels), n))
    t = np.arange(n) / sfreq
    burst = (t >= 40) & (t < 60)
    train = 60.0 * np.sin(2 * np.pi * 1.5 * t) * burst
    for ch, g in gains.items():
        x[channels.index(ch)] += g * train
    return x, robust_rms(x, sfreq, 2.0)


REF = ("Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T7", "C3", "Cz", "C4", "T8",
       "P7", "P3", "Pz", "P4", "P8", "O1", "O2")  # fmt: skip
BLINK = {"Fp1": 1.0, "Fp2": 1.0, "F7": 0.4, "F3": 0.4, "Fz": 0.4, "F4": 0.4, "F8": 0.4}


def test_anterior_electrode_reads_both_montages():
    from neurosignal.detection.seizure import anterior_electrode

    assert anterior_electrode("Fp1") == "FP1"
    assert anterior_electrode("FP2-F4") == "FP2"
    assert anterior_electrode("T8-P8-0") == "T8"
    assert anterior_electrode("EEG Fp1-REF") == "FP1"


def test_a_blink_field_is_blink_like():
    from neurosignal.detection.seizure import blink_cue

    x, bg = _cue_inputs(BLINK, REF)
    cue = blink_cue(x, REF, 256.0, 40.0, 60.0, bg)
    assert cue is not None
    assert cue.frontality > 3.0 and cue.symmetry > 0.8
    assert cue.blink_like(DetectorParams())


def test_a_posterior_slow_rhythm_is_not_blink_like():
    from neurosignal.detection.seizure import blink_cue

    x, bg = _cue_inputs({"Pz": 1.0, "P3": 0.7, "P4": 0.7, "O1": 0.5, "O2": 0.5, "Cz": 0.4}, REF)
    cue = blink_cue(x, REF, 256.0, 40.0, 60.0, bg)
    assert cue is not None and cue.frontality < 1.0
    assert not cue.blink_like(DetectorParams())


def test_a_lateral_frontal_rhythm_is_not_symmetric():
    """§11 D5: a lateralised frontal seizure is frontal enough to look like a
    blink; its asymmetry is what keeps it."""
    from neurosignal.detection.seizure import blink_cue

    x, bg = _cue_inputs({"Fp1": 1.0, "Fp2": 0.4, "F7": 0.8, "F3": 0.6}, REF)
    cue = blink_cue(x, REF, 256.0, 40.0, 60.0, bg)
    assert cue is not None
    assert cue.frontality >= DetectorParams().blink_frontality  # frontality alone would reject it
    assert cue.symmetry < DetectorParams().blink_symmetry
    assert not cue.blink_like(DetectorParams())


def test_the_cue_is_unavailable_without_both_frontopolar_sides():
    from neurosignal.detection.seizure import blink_cue

    chans = tuple(c for c in REF if c != "Fp2")
    x, bg = _cue_inputs({k: v for k, v in BLINK.items() if k != "Fp2"}, chans)
    assert blink_cue(x, chans, 256.0, 40.0, 60.0, bg) is None


def test_the_cue_works_on_a_bipolar_montage():
    from neurosignal.detection.seizure import blink_cue
    from neurosignal.synth.eeg import BIPOLAR_1020

    x_ref, _ = _cue_inputs(BLINK, REF)
    idx = {c: i for i, c in enumerate(REF)}
    x = np.stack([x_ref[idx[a]] - x_ref[idx[b]] for a, b in BIPOLAR_1020])
    names = tuple(f"{a.upper()}-{b.upper()}" for a, b in BIPOLAR_1020)
    cue = blink_cue(x, names, 256.0, 40.0, 60.0, robust_rms(x, 256.0, 2.0))
    # a derivation subtracts part of the field (FP1-F7 sees 1.0 - 0.4), so
    # frontality is lower than in a referential montage: the reason the cue is
    # tuned on both montages (§11)
    assert cue is not None and cue.frontality > 1.8 and cue.symmetry > 0.9


def test_the_default_detector_has_no_slow_band():
    """§11: with the default floor equal to the gate's lower edge, the detector
    is exactly the one frozen for H6."""
    p = detector_params(PipelineConfig())
    assert p.slow_floor_hz == p.rhythm_hz[0] == 2.0


def test_the_cue_admits_a_slow_discharge_and_rejects_blinks():
    """§11: below 2 Hz, a posterior slow discharge is kept with the cue on, and
    an event-free recording full of blinks still produces no detection."""
    on = replace(detector_params(PipelineConfig()), slow_floor_hz=1.0)
    slow, gt = _clean(31, n_events=1, snr_db=10.0, event_f0_hz=(1.2, 1.6),
                      event_f1_min_hz=1.0, event_centres=("Pz",))  # fmt: skip
    truth = Interval(gt.events[0].onset_s, gt.events[0].offset_s)
    assert not any(
        e.interval().overlaps(truth) for e in detect(slow, detector_params(PipelineConfig()))
    )
    hits = [e for e in detect(slow, on) if e.interval().overlaps(truth)]
    assert hits and hits[0].dominant_freq_hz < 2.0
    blinks, _ = _clean(32, blinks_per_min=30.0)
    assert detect(blinks, on) == []


def test_robust_rms_ignores_the_event_it_will_be_compared_with():
    """§11 amendment: the whole-recording RMS contains the event and capped the
    excess of a strong event near sqrt(recording / event length)."""
    rng = np.random.default_rng(1)
    x = rng.normal(0.0, 10.0, (1, 256 * 120))
    x[0, 256 * 40 : 256 * 60] *= 10.0
    assert 9.0 < robust_rms(x, 256.0, 2.0)[0] < 11.0


def test_without_frontopolar_channels_the_slow_band_stays_closed():
    """§11: when the cue cannot be measured, events below 2 Hz are rejected as
    in the detector frozen for H6."""
    on = replace(detector_params(PipelineConfig()), slow_floor_hz=1.0)
    slow, gt = _clean(31, n_events=1, snr_db=10.0, event_f0_hz=(1.2, 1.6),
                      event_f1_min_hz=1.0, event_centres=("Pz",))  # fmt: skip
    no_fp2 = slow.evolve(bad_channels=(*slow.bad_channels, "Fp2"))
    truth = Interval(gt.events[0].onset_s, gt.events[0].offset_s)
    assert not any(e.interval().overlaps(truth) for e in detect(no_fp2, on))


def test_a_sustained_bilateral_frontal_slow_wave_is_rejected():
    """§11 amendment, through the whole detector: a 60 s bilateral frontal
    1.5 Hz wave (a blink-like field; in real EEG, FIRDA looks like this) must
    stay rejected with the cue on. Measured against the whole-recording RMS,
    which contains the wave, its frontality is capped near sqrt(300 / 60) and
    it would be admitted."""
    from neurosignal.core.recording import Recording

    rng = np.random.default_rng(0)
    sfreq, n = 256.0, 256 * 300
    t = np.arange(n) / sfreq
    x = rng.normal(0.0, 10.0, (len(REF), n))
    wave = 60.0 * np.sin(2 * np.pi * 1.5 * t) * ((t >= 100) & (t < 160))
    for ch, g in BLINK.items():
        x[REF.index(ch)] += g * wave
    rec = Recording(data=x, sfreq=sfreq, channels=REF)
    assert detect(rec, replace(DetectorParams(), slow_floor_hz=1.0)) == []
