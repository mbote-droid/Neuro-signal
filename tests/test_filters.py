"""F-06, V-05: FIR design meets its specification, and zero phase is zero."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy import signal

from neurosignal.core.recording import Recording
from neurosignal.preprocessing.filters import (
    FilterStage,
    causal,
    design_bandpass,
    design_notch,
    fir_length,
    highpass_transition,
    lowpass_transition,
    zero_phase,
)

FS = 256.0


def _response_db(h: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    _, H = signal.freqz(h, worN=freqs, fs=FS)
    return 20 * np.log10(np.maximum(np.abs(H), 1e-12))


def test_bandpass_meets_ripple_and_attenuation():
    """V-05: passband ripple <= 0.1 dB, stopband >= 40 dB."""
    lo, hi = 0.5, 45.0
    h = design_bandpass(lo, hi, FS)
    passband = np.linspace(lo + 0.05, hi, 400)
    ht = lowpass_transition(hi, FS)
    stop = np.linspace(hi + ht + 0.5, FS / 2, 300)
    assert np.max(np.abs(_response_db(h, passband))) <= 0.1
    assert np.max(_response_db(h, stop)) <= -40
    assert _response_db(h, np.array([0.0]))[0] <= -40


def test_notch_removes_mains_and_spares_neighbours():
    h = design_notch(50.0, 2.0, FS)
    assert _response_db(h, np.array([49.6, 50.0, 50.4])).max() <= -40
    assert np.abs(_response_db(h, np.array([10.0, 40.0, 45.0]))).max() <= 0.1


def test_fir_length_is_odd_and_follows_hamming_rule():
    n = fir_length(FS, 0.5)
    assert n % 2 == 1
    assert n >= 3.3 * FS / 0.5
    assert highpass_transition(0.5) == 0.5
    assert highpass_transition(20.0) == 5.0


def test_zero_phase_does_not_shift_an_impulse():
    """V-05: the impulse peak stays at its sample (zero phase)."""
    x = np.zeros(4096)
    x[2048] = 1.0
    h = design_bandpass(1.0, 30.0, FS)
    y = zero_phase(x, h)
    assert int(np.argmax(np.abs(y))) == 2048
    np.testing.assert_allclose(y[2048 - 200 : 2048], y[2049 : 2049 + 200][::-1], atol=1e-12)


def test_negative_control_causal_filter_delays_by_half_its_length():
    """A causal FIR in an offline pipeline shifts events by (N-1)/2 samples."""
    x = np.zeros(4096)
    x[1000] = 1.0
    h = design_bandpass(1.0, 30.0, FS)
    y = causal(x, h)
    assert int(np.argmax(np.abs(y))) - 1000 == (h.size - 1) // 2


def test_passband_sinusoid_amplitude_preserved():
    t = np.arange(int(60 * FS)) / FS
    x = 40.0 * np.sin(2 * np.pi * 10.0 * t)
    y = zero_phase(x, design_bandpass(0.5, 45.0, FS))
    mid = slice(int(10 * FS), int(50 * FS))
    assert abs(np.std(y[mid]) * np.sqrt(2) - 40.0) < 0.1


def test_filter_stage_records_parameters_and_removes_mains():
    t = np.arange(int(30 * FS)) / FS
    x = np.stack([10 * np.sin(2 * np.pi * 10 * t) + 20 * np.sin(2 * np.pi * 50 * t)] * 2)
    rec = Recording(data=x, sfreq=FS, channels=("A", "B"))
    out = FilterStage(0.5, 45.0, 50.0, 2.0)(rec)
    step = out.history[-1]
    assert step["stage"] == "filter"
    assert step["notch_hz"] == [50.0, 100.0]
    assert step["bandpass_taps"] % 2 == 1
    f, p_in = signal.welch(x[0], fs=FS, nperseg=512)
    _, p_out = signal.welch(out.data[0], fs=FS, nperseg=512)
    i50 = np.argmin(np.abs(f - 50))
    assert p_out[i50] < 1e-4 * p_in[i50]


def test_zero_phase_rejects_asymmetric_filters():
    with pytest.raises(ValueError):
        zero_phase(np.zeros(100), np.array([1.0, 2.0, 3.0]))


@settings(max_examples=25, deadline=None)
@given(
    a=st.floats(-5, 5, allow_nan=False),
    b=st.floats(-5, 5, allow_nan=False),
    seed=st.integers(0, 10_000),
)
def test_property_zero_phase_is_linear(a, b, seed):
    g = np.random.default_rng(seed)
    x, y = g.standard_normal(1024), g.standard_normal(1024)
    h = design_bandpass(2.0, 30.0, 128.0)
    lhs = zero_phase(a * x + b * y, h)
    rhs = a * zero_phase(x, h) + b * zero_phase(y, h)
    np.testing.assert_allclose(lhs, rhs, atol=1e-9)


@settings(max_examples=15, deadline=None)
@given(shift=st.integers(1, 200), seed=st.integers(0, 10_000))
def test_property_time_shift_equivariance_away_from_edges(shift, seed):
    g = np.random.default_rng(seed)
    x = g.standard_normal(4096)
    h = design_bandpass(2.0, 30.0, 128.0)
    y1 = zero_phase(x, h)
    y2 = zero_phase(np.roll(x, shift), h)
    core = slice(1000, 3000)
    np.testing.assert_allclose(np.roll(y1, shift)[core], y2[core], atol=1e-9)
