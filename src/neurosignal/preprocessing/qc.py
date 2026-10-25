"""Channel quality control (F-03, F-04, F-05)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import ndimage, signal

from neurosignal.core.recording import FloatArray, Recording
from neurosignal.core.stage import Stage

MAD_TO_SD = 1.4826  # MAD of a Gaussian times this is its standard deviation
LINE_REFERENCE_BAND_HZ = (1.0, 45.0)


def robust_sd(x: FloatArray, axis: int = -1) -> FloatArray:
    med = np.median(x, axis=axis, keepdims=True)
    return np.asarray(MAD_TO_SD * np.median(np.abs(x - med), axis=axis), dtype=np.float64)


def _flat_window(x: FloatArray, w: int, tolerance: float) -> bool:
    """Is any window of w samples lying wholly inside the signal flat? The
    filters reflect the signal at its ends, so windows that overhang an end are
    discarded: a 3 s flat start would otherwise mirror into 6 s (ISSUE-016)."""
    span = ndimage.maximum_filter1d(x, w) - ndimage.minimum_filter1d(x, w)
    inside = span[w // 2 : x.size - (w - 1) // 2]
    return bool(np.any(inside <= 2 * tolerance))


def longest_flat_run_s(x: FloatArray, sfreq: float, tolerance: float) -> float:
    """Longest stretch (s) over which the signal stays inside a 2*tolerance band.

    A sliding max-min over a window W is <= 2*tolerance iff the window is
    flat; the longest flat stretch is found by doubling W.
    """
    n = x.size
    best = 0
    w = max(2, int(0.5 * sfreq))
    while w <= n:
        if not _flat_window(x, w, tolerance):
            break
        best = w
        w *= 2
    if best == 0:
        return 0.0
    lo, hi = best, min(2 * best, n)  # refine between best and the failing size
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if _flat_window(x, mid, tolerance):
            lo = mid
        else:
            hi = mid
    return lo / sfreq


def line_noise_ratio(x: FloatArray, sfreq: float, line_freq: float) -> FloatArray:
    """Power within ±1 Hz of mains over power in 1-45 Hz, per channel."""
    if line_freq + 1 >= sfreq / 2:
        return np.full(x.shape[0], np.nan)
    nper = int(min(x.shape[-1], 2 * sfreq))
    f, p = signal.welch(x, fs=sfreq, nperseg=nper, axis=-1)
    line = (f >= line_freq - 1) & (f <= line_freq + 1)
    band = (f >= LINE_REFERENCE_BAND_HZ[0]) & (f <= LINE_REFERENCE_BAND_HZ[1])
    with np.errstate(invalid="ignore", divide="ignore"):  # flat channels give 0/0 -> nan
        ratio = p[:, line].sum(axis=1) / p[:, band].sum(axis=1)
    return np.asarray(ratio, dtype=np.float64)


@dataclass(frozen=True)
class QCResult:
    flat: dict[str, float]  # channel -> longest flat run (s)
    noisy: dict[str, float]  # channel -> MAD ratio
    low: dict[str, float]
    mad_uv: dict[str, float]

    @property
    def bad(self) -> dict[str, str]:
        out = {c: "flat" for c in self.flat}
        out.update({c: "noisy" for c in self.noisy if c not in out})
        out.update({c: "low" for c in self.low if c not in out})
        return out


class FlatChannels(Stage):
    """Runs on raw data: filtering would make a flat line ring."""

    name = "qc_flat"

    def __init__(self, tolerance_uv: float, max_duration_s: float) -> None:
        self.tolerance_uv, self.max_duration_s = tolerance_uv, max_duration_s
        self.found: dict[str, float] = {}

    def process(self, rec: Recording) -> Recording:
        self.found = {}
        for i, ch in enumerate(rec.channels):
            run = longest_flat_run_s(rec.data[i], rec.sfreq, self.tolerance_uv)
            if run > self.max_duration_s:
                self.found[ch] = round(run, 3)
        bad = tuple(dict.fromkeys(rec.bad_channels + tuple(self.found)))
        return rec.evolve(bad_channels=bad)

    def params(self) -> dict[str, Any]:
        return {
            "tolerance_uv": self.tolerance_uv,
            "max_duration_s": self.max_duration_s,
            "flat_channels": dict(self.found),
        }


class AmplitudeChannels(Stage):
    """Runs on band-passed data: drifts would otherwise inflate the MAD."""

    name = "qc_amplitude"

    def __init__(self, noisy_ratio: float, low_ratio: float) -> None:
        self.noisy_ratio, self.low_ratio = noisy_ratio, low_ratio
        self.mad: dict[str, float] = {}
        self.noisy: dict[str, float] = {}
        self.low: dict[str, float] = {}

    def process(self, rec: Recording) -> Recording:
        sd = robust_sd(rec.data)
        self.mad = {c: float(v) for c, v in zip(rec.channels, sd, strict=True)}
        ref_idx = [i for i, c in enumerate(rec.channels) if c not in rec.bad_channels]
        reference = float(np.median(sd[ref_idx])) if ref_idx else float("nan")
        self.noisy, self.low = {}, {}
        for i in ref_idx:
            ratio = float(sd[i] / reference) if reference > 0 else float("inf")
            if ratio > self.noisy_ratio:
                self.noisy[rec.channels[i]] = round(ratio, 3)
            elif ratio < self.low_ratio:
                self.low[rec.channels[i]] = round(ratio, 3)
        bad = tuple(dict.fromkeys(rec.bad_channels + tuple(self.noisy) + tuple(self.low)))
        return rec.evolve(bad_channels=bad)

    def params(self) -> dict[str, Any]:
        return {
            "noisy_mad_ratio": self.noisy_ratio,
            "low_mad_ratio": self.low_ratio,
            "noisy_channels": dict(self.noisy),
            "low_channels": dict(self.low),
        }
