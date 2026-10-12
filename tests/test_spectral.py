"""F-08, F-10: Welch spectra and band power."""

from __future__ import annotations

import numpy as np
import pytest

from neurosignal.core.recording import Recording
from neurosignal.features.spectral import band_power, relative_band_power, welch

FS = 256.0


def _rec(x):
    return Recording(data=np.atleast_2d(x).astype(float), sfreq=FS, channels=("A",))


def test_resolution_and_segments():
    """F-08: 2 s Hann windows, 50 % overlap -> 0.5 Hz bins."""
    sp = welch(_rec(np.random.default_rng(0).standard_normal(int(60 * FS))))
    assert np.isclose(sp.freqs[1] - sp.freqs[0], 0.5)
    assert sp.n_segments == 59


def test_parseval_total_power_equals_variance():
    x = np.random.default_rng(1).standard_normal(int(120 * FS)) * 7.0
    sp = welch(_rec(x))
    total = band_power(sp, (0.0, FS / 2))[0]
    assert abs(total / np.var(x) - 1) < 0.03


def test_sinusoid_band_power():
    """F-10: a 10 Hz sinusoid of amplitude A has power A²/2 in the alpha band."""
    t = np.arange(int(60 * FS)) / FS
    sp = welch(_rec(20.0 * np.sin(2 * np.pi * 10.0 * t)))
    assert abs(band_power(sp, (8.0, 12.0))[0] - 200.0) < 2.0
    assert relative_band_power(sp, (8.0, 12.0))[0] > 0.99


def test_excluded_windows_are_dropped():
    t = np.arange(int(60 * FS)) / FS
    x = np.random.default_rng(2).standard_normal(t.size)
    x[int(20 * FS) : int(40 * FS)] += 200 * np.sin(2 * np.pi * 3 * t[int(20 * FS) : int(40 * FS)])
    full = welch(_rec(x))
    clean = welch(_rec(x), exclude=[(20.0, 40.0)])
    assert clean.n_segments < full.n_segments
    assert band_power(clean, (2.5, 3.5))[0] < 0.01 * band_power(full, (2.5, 3.5))[0]


def test_too_short_recording_refused():
    with pytest.raises(ValueError):
        welch(_rec(np.zeros(100)))
