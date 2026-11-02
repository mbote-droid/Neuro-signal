"""R-03 and generator correctness: the ground truth must itself be right."""

from __future__ import annotations

import hashlib
import subprocess
import sys

import numpy as np
from scipy import signal

from neurosignal.core.seeds import rng
from neurosignal.synth.eeg import (
    ChannelSpectrum,
    Peak,
    SynthSpec,
    make_recording,
    shaped_noise,
    spike_wave,
)

_HASH = (
    "import hashlib;from neurosignal.synth.eeg import make_recording,SynthSpec;"
    "r,_=make_recording(11,SynthSpec(duration_s=30,n_events=0,n_flat=1,n_noisy=1,"
    "blinks_per_min=10,muscle_per_min=2));print(hashlib.sha256(r.data.tobytes()).hexdigest())"
)


def test_same_seed_same_data_across_processes():
    """R-03."""
    outs = {
        subprocess.run(
            [sys.executable, "-c", _HASH], capture_output=True, text=True, check=True
        ).stdout.strip()
        for _ in range(2)
    }
    assert len(outs) == 1
    rec, _ = make_recording(
        11,
        SynthSpec(
            duration_s=30, n_events=0, n_flat=1, n_noisy=1, blinks_per_min=10, muscle_per_min=2
        ),
    )
    assert hashlib.sha256(rec.data.tobytes()).hexdigest() in outs


def test_different_seeds_differ():
    a, _ = make_recording(1, SynthSpec(duration_s=10))
    b, _ = make_recording(2, SynthSpec(duration_s=10))
    assert not np.allclose(a.data, b.data)


def test_shaped_noise_has_the_specified_spectrum():
    """The generator's PSD matches the model within Welch's sampling error."""
    cs = ChannelSpectrum(offset=1.2, exponent=1.5, peaks=(Peak(10.0, 0.8, 1.0),))
    x = shaped_noise(cs, 256 * 600, 256.0, rng(3))
    f, p = signal.welch(x, fs=256.0, nperseg=512)
    m = (f >= 2) & (f <= 40)
    err = np.log10(p[m]) - cs.log_power(f[m])
    assert abs(np.median(err)) < 0.03
    assert np.percentile(np.abs(err), 95) < 0.15


def test_spike_wave_is_unit_rms_and_rhythmic():
    t = np.arange(0, 20, 1 / 256)
    w = spike_wave(t, 3.0, 3.0)
    assert abs(np.sqrt(np.mean(w**2)) - 1) < 1e-9
    f, p = signal.welch(w, fs=256, nperseg=1024)
    assert abs(f[np.argmax(p)] - 3.0) < 0.3


def test_ground_truth_lists_events_and_bad_channels():
    rec, gt = make_recording(4, SynthSpec(duration_s=300, n_events=2, n_flat=1, n_noisy=2))
    assert len(gt.events) == 2
    assert sorted(gt.bad_channels.values()) == ["flat", "noisy", "noisy"]
    for e in gt.events:
        assert 0 < e.onset_s < e.offset_s < rec.duration_s
    # ground truth never leaks into the recording
    assert rec.annotations == ()


def test_default_event_options_reproduce_existing_recordings():
    """PROBLEM_STATEMENT §11: new generator options must not change the
    recordings every earlier result was measured on."""
    from validation.common import detection_spec

    rec, gt = make_recording(0, detection_spec(0))
    assert hashlib.sha256(rec.data.tobytes()).hexdigest()[:16] == "57dc97656131d757"
    assert [round(e.onset_s, 3) for e in gt.events] == [88.056, 235.914]


def test_slow_discharges_have_a_slow_fundamental():
    t = np.arange(0, 30, 1 / 256)
    wave = spike_wave(t, 1.6, 1.2)
    f, pxx = signal.welch(wave, fs=256, nperseg=1024)
    assert 1.0 <= f[np.argmax(pxx)] <= 1.8


def test_discharges_can_be_centred_on_chosen_electrodes():
    spec = SynthSpec(duration_s=200.0, n_events=2, event_centres=("Fp1", "Fp2"))
    _, gt = make_recording(5, spec)
    for e in gt.events:
        assert "Fp1" in e.channels or "Fp2" in e.channels


def test_bipolar_rendering_matches_chbmit():
    from neurosignal.synth.eeg import bipolar_montage

    rec, _ = make_recording(1, SynthSpec(duration_s=30.0))
    bip = bipolar_montage(rec)
    assert bip.channels[0] == "FP1-F7" and bip.channels[-1] == "CZ-PZ"
    assert bip.n_channels == 18 and bip.is_bipolar
    i, j = rec.channels.index("Fp1"), rec.channels.index("F7")
    np.testing.assert_allclose(bip.data[0], rec.data[i] - rec.data[j])
