"""Welch spectra and band power (F-08, F-10, EQUATIONS §4)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import integrate, signal

from neurosignal.core.recording import FloatArray, Recording


@dataclass(frozen=True)
class Spectrum:
    freqs: FloatArray  # (n_freqs,) Hz
    psd: FloatArray  # (n_channels, n_freqs) µV²/Hz, one-sided
    channels: tuple[str, ...]
    window_s: float
    n_segments: int


def welch(
    rec: Recording,
    window_s: float = 2.0,
    overlap: float = 0.5,
    exclude: list[tuple[float, float]] | None = None,
) -> Spectrum:
    """Welch PSD; segments overlapping any `exclude` interval (s) are dropped.

    Excluding detected events keeps the background spectrum a background
    spectrum: a 3 Hz discharge otherwise bends the aperiodic fit.
    """
    nper = round(window_s * rec.sfreq)
    if nper > rec.n_samples:
        raise ValueError(f"recording ({rec.duration_s:.1f} s) shorter than one {window_s} s window")
    nover = round(overlap * nper)
    psd = []
    keep = np.ones(0, dtype=bool)
    f = np.zeros(0)
    for row in rec.data:  # one channel at a time bounds memory (ADR-012)
        f, t, sxx = signal.spectrogram(
            row, fs=rec.sfreq, window="hann", nperseg=nper, noverlap=nover,
            detrend="constant", scaling="density", mode="psd",
        )  # fmt: skip
        if keep.size != t.size:
            keep = np.ones(t.size, dtype=bool)
            for a, b in exclude or []:
                keep &= ~((t + window_s / 2 > a) & (t - window_s / 2 < b))
            if not keep.any():
                keep[:] = True  # nothing left: use every segment rather than fail
        psd.append(sxx[:, keep].mean(axis=-1))
    return Spectrum(
        freqs=np.asarray(f, dtype=np.float64),
        psd=np.asarray(psd, dtype=np.float64),
        channels=rec.channels,
        window_s=window_s,
        n_segments=int(keep.sum()),
    )


def band_power(spec: Spectrum, band: tuple[float, float]) -> FloatArray:
    """Integrated power (µV²) in [lo, hi] Hz per channel, trapezoid rule."""
    lo, hi = band
    m = (spec.freqs >= lo) & (spec.freqs <= hi)
    if m.sum() < 2:
        raise ValueError(f"band {band} has fewer than two frequency bins")
    return np.asarray(integrate.trapezoid(spec.psd[:, m], spec.freqs[m], axis=-1))


def relative_band_power(
    spec: Spectrum, band: tuple[float, float], total: tuple[float, float] = (1.0, 45.0)
) -> FloatArray:
    return band_power(spec, band) / band_power(spec, total)
