"""F-09, V-01, V-02, V-03: aperiodic fit against ground truth and specparam."""

from __future__ import annotations

import numpy as np
import pytest

from neurosignal.core.recording import Recording
from neurosignal.core.seeds import rng
from neurosignal.features.aperiodic import fit_spectrum
from neurosignal.features.spectral import welch
from neurosignal.synth.eeg import random_spectrum, shaped_noise

N_CASES = 30


def _case(seed: int):
    g = rng(seed, 77)
    cs = random_spectrum(g)
    x = shaped_noise(cs, 256 * 180, 256.0, g)
    sp = welch(Recording(data=x[None, :], sfreq=256.0, channels=("X",)))
    return cs, sp.freqs, sp.psd[0]


@pytest.fixture(scope="module")
def cases():
    return [_case(s) for s in range(N_CASES)]


def test_fit_returns_all_parameters(cases):
    """F-09."""
    _, f, p = cases[0]
    fit = fit_spectrum(f, p)
    assert fit.freq_range == (2.0, 40.0)
    assert 0.9 < fit.r_squared <= 1.0
    assert fit.error >= 0
    assert all(2.0 <= pk.freq <= 40.0 for pk in fit.peaks)


def test_exponent_recovered(cases):
    """V-01: median absolute error <= 0.1."""
    errs = [abs(fit_spectrum(f, p).exponent - cs.exponent) for cs, f, p in cases]
    assert np.median(errs) <= 0.1


def test_alpha_peak_frequency_recovered(cases):
    """V-02: median absolute error <= 0.5 Hz."""
    errs = []
    for cs, f, p in cases:
        peak = fit_spectrum(f, p).peak_in((7.0, 14.0))
        assert peak is not None
        errs.append(abs(peak.freq - cs.peaks[0].freq))
    assert np.median(errs) <= 0.5


def test_agrees_with_specparam(cases):
    """V-03: independent implementation; |exponent difference| <= 0.1 in >= 90 %."""
    specparam = pytest.importorskip("specparam")
    agree = 0
    for _, f, p in cases:
        sm = specparam.SpectralModel(
            peak_width_limits=(1.0, 8.0), max_n_peaks=4, aperiodic_mode="fixed", verbose=False
        )
        sm.fit(f, p, [2, 40])
        theirs = float(sm.results.get_params("aperiodic", "exponent"))
        agree += abs(fit_spectrum(f, p).exponent - theirs) <= 0.1
    assert agree / len(cases) >= 0.9


def test_flat_spectrum_has_no_peaks():
    f = np.arange(0.5, 64, 0.5)
    p = f**-1.5 * 10
    fit = fit_spectrum(f, p)
    assert fit.peaks == ()
    assert abs(fit.exponent - 1.5) < 1e-6


def test_rejects_too_few_bins():
    with pytest.raises(ValueError):
        fit_spectrum(np.array([1.0, 2.0, 3.0]), np.array([1.0, 1.0, 1.0]))
