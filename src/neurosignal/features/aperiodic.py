"""Aperiodic + periodic parameterisation of power spectra (F-09, ADR-006).

Model (fixed mode, no knee), as in Donoghue et al. (2020):

    log10 P(f) = b - chi * log10 f + sum_k h_k exp(-(f - c_k)^2 / (2 s_k^2))

Algorithm (EQUATIONS §5):
1. robust aperiodic start: fit a line in log-log space, then refit on the
   points at or below the median residual (peaks sit above the line);
2. greedy peak search on the flattened spectrum: take the maximum, stop
   below max(peak_threshold_sd * SD of the flattened spectrum,
   min_peak_height), estimate the width from the half-height crossings,
   subtract the Gaussian, repeat;
3. joint bounded least squares over all parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import optimize

from neurosignal.core.recording import FloatArray

FWHM_TO_SD = 1.0 / (2.0 * np.sqrt(2.0 * np.log(2.0)))


@dataclass(frozen=True)
class FittedPeak:
    freq: float
    height: float  # log10 power above the aperiodic fit
    sd: float  # Hz (specparam's "bandwidth" is 2 * sd)


@dataclass(frozen=True)
class AperiodicFit:
    offset: float
    exponent: float
    peaks: tuple[FittedPeak, ...]
    r_squared: float
    error: float  # mean absolute error in log10 power
    freq_range: tuple[float, float]

    def model(self, freqs: FloatArray) -> FloatArray:
        return _model(freqs, self.offset, self.exponent, self.peaks)

    def aperiodic(self, freqs: FloatArray) -> FloatArray:
        return np.asarray(self.offset - self.exponent * np.log10(freqs))

    def peak_in(self, band: tuple[float, float]) -> FittedPeak | None:
        """The highest peak whose centre lies in band."""
        cands = [p for p in self.peaks if band[0] <= p.freq <= band[1]]
        return max(cands, key=lambda p: p.height) if cands else None


def _model(
    freqs: FloatArray, offset: float, exponent: float, peaks: tuple[FittedPeak, ...]
) -> FloatArray:
    out = offset - exponent * np.log10(freqs)
    for p in peaks:
        out = out + p.height * np.exp(-((freqs - p.freq) ** 2) / (2 * p.sd**2))
    return np.asarray(out, dtype=np.float64)


def _robust_line(logf: FloatArray, logp: FloatArray) -> tuple[float, float]:
    slope, icpt = np.polyfit(logf, logp, 1)
    for _ in range(3):
        resid = logp - (icpt + slope * logf)
        keep = resid <= np.median(resid)
        slope, icpt = np.polyfit(logf[keep], logp[keep], 1)
    return float(icpt), float(-slope)


def _half_height_sd(f: FloatArray, flat: FloatArray, i: int, step: float) -> float:
    half = flat[i] / 2
    left = i
    while left > 0 and flat[left] > half:
        left -= 1
    right = i
    while right < flat.size - 1 and flat[right] > half:
        right += 1
    # the shorter side is less contaminated by neighbouring peaks
    half_width = min(i - left, right - i) * step
    return float(2 * half_width * FWHM_TO_SD) if half_width > 0 else step


def _greedy_peaks(
    f: FloatArray,
    flat: FloatArray,
    max_peaks: int,
    threshold_sd: float,
    min_height: float,
    width_limits: tuple[float, float],
) -> list[FittedPeak]:
    work = flat.copy()
    step = float(f[1] - f[0])
    peaks: list[FittedPeak] = []
    for _ in range(max_peaks):
        i = int(np.argmax(work))
        height = float(work[i])
        if height < max(threshold_sd * float(np.std(work)), min_height):
            break
        sd = float(
            np.clip(_half_height_sd(f, work, i, step), width_limits[0] / 2, width_limits[1] / 2)
        )
        work = work - height * np.exp(-((f - f[i]) ** 2) / (2 * sd**2))
        if f[i] - f[0] < sd or f[-1] - f[i] < sd:
            continue  # edge peaks are mostly aperiodic misfit
        peaks.append(FittedPeak(float(f[i]), height, sd))
    return peaks


def fit_spectrum(
    freqs: FloatArray,
    psd: FloatArray,
    freq_range: tuple[float, float] = (2.0, 40.0),
    max_peaks: int = 4,
    peak_threshold_sd: float = 2.0,
    min_peak_height: float = 0.1,
    peak_width_limits: tuple[float, float] = (1.0, 8.0),
) -> AperiodicFit:
    """Fit one spectrum. `peak_width_limits` are specparam-style bandwidths (2 sd)."""
    m = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
    f = freqs[m]
    if f.size < 8 or np.any(psd[m] <= 0):
        raise ValueError("need at least 8 positive spectral bins in the fit range")
    logp = np.log10(psd[m])
    logf = np.log10(f)
    offset, exponent = _robust_line(logf, logp)
    flat = logp - (offset - exponent * logf)
    peaks = _greedy_peaks(f, flat, max_peaks, peak_threshold_sd, min_peak_height, peak_width_limits)
    offset, exponent, peaks = _refine(f, logp, offset, exponent, peaks, peak_width_limits)
    pred = _model(f, offset, exponent, tuple(peaks))
    ss_res = float(np.sum((logp - pred) ** 2))
    ss_tot = float(np.sum((logp - logp.mean()) ** 2))
    return AperiodicFit(
        offset=offset,
        exponent=exponent,
        peaks=tuple(sorted(peaks, key=lambda p: p.freq)),
        r_squared=1 - ss_res / ss_tot if ss_tot > 0 else 0.0,
        error=float(np.mean(np.abs(logp - pred))),
        freq_range=(float(freq_range[0]), float(freq_range[1])),
    )


def _refine(
    f: FloatArray,
    logp: FloatArray,
    offset: float,
    exponent: float,
    peaks: list[FittedPeak],
    width_limits: tuple[float, float],
) -> tuple[float, float, list[FittedPeak]]:
    x0 = [offset, exponent]
    lo = [-np.inf, -1.0]
    hi = [np.inf, 5.0]
    for p in peaks:
        x0 += [p.freq, p.height, p.sd]
        lo += [p.freq - 2 * p.sd, 0.0, width_limits[0] / 2]
        hi += [p.freq + 2 * p.sd, np.inf, width_limits[1] / 2]
    x0 = list(np.clip(x0, np.array(lo) + 1e-9, np.array(hi) - 1e-9))

    def resid(x: FloatArray) -> FloatArray:
        ps = tuple(FittedPeak(*x[2 + 3 * k : 5 + 3 * k]) for k in range(len(peaks)))
        return _model(f, x[0], x[1], ps) - logp

    sol = optimize.least_squares(resid, x0, bounds=(lo, hi), method="trf")
    x = sol.x
    refined = [FittedPeak(*map(float, x[2 + 3 * k : 5 + 3 * k])) for k in range(len(peaks))]
    return float(x[0]), float(x[1]), [p for p in refined if p.height > 1e-3]
