"""Theory versus measurement: the probability models behind the design decisions.

Each subcommand states what a model predicts *before* looking at the
pipeline's numbers, then measures the same quantity, and writes both to
results/validation/theory_<name>.json (docs/STATISTICAL_FOUNDATIONS.md).

    python validation/theory.py all
    python validation/theory.py h1_noise | wpli_bias | blinks | power | whittle | robust_z
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from scipy import optimize, special, stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neurosignal.core.config import PipelineConfig
from neurosignal.core.recording import Recording
from neurosignal.core.seeds import rng
from neurosignal.core.stats import poisson_upper, wilson
from neurosignal.detection.seizure import (
    DetectorParams,
    background_spectra,
    band_limit,
    dominant_frequency,
    events_from_z,
    line_length_z,
)
from neurosignal.features.aperiodic import FittedPeak, _model, fit_spectrum
from neurosignal.features.connectivity import phase_coupling
from neurosignal.features.spectral import welch
from neurosignal.pipeline import detector_params, preprocess
from neurosignal.preprocessing.qc import MAD_TO_SD
from neurosignal.synth.eeg import (
    ChannelSpectrum,
    Peak,
    SynthSpec,
    make_recording,
    mixed_sources,
    random_spectrum,
    shaped_noise,
)
from validation.common import RESULTS, write_result

FS = 256.0
WORKERS = 4
LN10 = math.log(10.0)


# ----------------------------------------------------------------- shared theory


def welch_dof(n_segments: int, overlap_corr: float = 1 / 6) -> float:
    """Equivalent degrees of freedom of a Welch estimate (Welch 1967):
    nu = 2K / (1 + 2 rho^2), rho = correlation of adjacent Hann segments at 50 %
    overlap (1/6)."""
    return 2.0 * n_segments / (1.0 + 2.0 * overlap_corr**2)


def log10_bin_sd(nu: float) -> float:
    """SD of log10 of a scaled chi-squared(nu)/nu variable: sqrt(psi'(nu/2)) / ln 10."""
    return math.sqrt(float(special.polygamma(1, nu / 2.0))) / LN10


def hann_bin_correlation(n: int) -> np.ndarray:
    """Correlation of Hann-windowed periodogram ordinates between bins k apart for
    white-like noise: |rho_k|^2 with rho_1 = -2/3, rho_2 = 1/6 (Hann's three-term
    spectral kernel 1/2, -1/4, -1/4)."""
    r = np.eye(n)
    for k, c in ((1, (2 / 3) ** 2), (2, (1 / 6) ** 2)):
        r += np.diag(np.full(n - k, c), k) + np.diag(np.full(n - k, c), -k)
    return r


def jacobian(
    freqs: np.ndarray, offset: float, exponent: float, peaks: tuple[Peak, ...]
) -> np.ndarray:
    """d log10 P / d theta for theta = (offset, exponent, then freq, height, sd per peak)."""
    cols = [np.ones_like(freqs), -np.log10(freqs)]
    for p in peaks:
        g = np.exp(-((freqs - p.freq) ** 2) / (2 * p.sd**2))
        cols += [
            p.height * g * (freqs - p.freq) / p.sd**2,
            g,
            p.height * g * (freqs - p.freq) ** 2 / p.sd**3,
        ]
    return np.stack(cols, axis=1)


def ols_covariance(j: np.ndarray, sigma: float, corr: np.ndarray) -> np.ndarray:
    """Sandwich covariance of the unweighted least-squares estimate under
    correlated errors with covariance sigma^2 * corr."""
    bread = np.linalg.inv(j.T @ j)
    return bread @ j.T @ (sigma**2 * corr) @ j @ bread


def _load(name: str) -> dict[str, Any]:
    return json.loads((RESULTS / f"{name}.json").read_text())


# ----------------------------------------------------------------- 1. H1 noise floor


def _h1_base(seed: int) -> ChannelSpectrum:
    """The baseline spectrum of H1 case `seed`, rebuilt exactly as validation/campaign.py does."""
    g = rng(seed, 101)
    base = random_spectrum(g, alpha=True)
    return ChannelSpectrum(offset=base.offset, exponent=min(base.exponent, 1.7), peaks=base.peaks)


def _h1_refit(seed: int) -> dict[str, float]:
    """Re-run H1's independent design, recording how many peaks each fit found."""
    from validation.campaign import _single

    base = _h1_base(seed)
    out = {}
    for k, cs in enumerate((base, ChannelSpectrum(base.offset, base.exponent + 0.5, base.peaks))):
        sp = welch(_single(shaped_noise(cs, 256 * 180, 256.0, rng(seed, 102, k))))
        fit = fit_spectrum(sp.freqs, sp.psd[0])
        pk = fit.peak_in((7.0, 14.0))
        out[f"n_peaks_{k}"] = len(fit.peaks)
        out[f"height_{k}"] = pk.height if pk else 0.0
    return out


def exp_h1_noise() -> None:
    """Predicted SD of the fitted alpha-height difference between two independent
    3-minute recordings, from Welch sampling theory alone, versus H1's measurement."""
    duration, window = 180.0, 2.0
    k = int((duration - window) / (window / 2)) + 1
    nu = welch_dof(k)
    sigma = log10_bin_sd(nu)
    f = np.arange(2.0, 40.0 + 1e-9, 0.5)
    corr = hann_bin_correlation(f.size)
    h1 = _load("h1_confound")
    measured = {r["seed"]: r["independent_steeper_peak_change"] for r in h1["rows"]}
    pred_sd, pred_within = [], []
    for seed in sorted(measured):
        base = _h1_base(seed)
        cov = ols_covariance(jacobian(f, base.offset, base.exponent, base.peaks), sigma, corr)
        se_h = math.sqrt(cov[3, 3])  # alpha height is the first peak's height (index 3)
        sd_diff = math.sqrt(2.0) * se_h  # both conditions share J: same SE
        pred_sd.append(sd_diff)
        pred_within.append(math.erf(0.05 / (sd_diff * math.sqrt(2.0))))
    diffs = np.array([measured[s] for s in sorted(measured)])
    robust_sd = MAD_TO_SD * float(np.median(np.abs(diffs - np.median(diffs))))
    rms_pred = float(np.sqrt(np.mean(np.square(pred_sd))))
    # recording length at which 90 % of differences fall within 0.05 (SD scales as 1/sqrt(K))
    target_sd = 0.05 / stats.norm.ppf(0.95)
    t_needed = duration * (rms_pred / target_sd) ** 2
    with ProcessPoolExecutor(WORKERS) as ex:
        refits = list(ex.map(_h1_refit, sorted(measured)))
    same = np.array([r["n_peaks_0"] == r["n_peaks_1"] for r in refits])
    d2 = np.array([r["height_1"] - r["height_0"] for r in refits])

    def rsd(v: np.ndarray) -> float:
        return MAD_TO_SD * float(np.median(np.abs(v - np.median(v)))) if v.size else float("nan")

    write_result(
        "theory_h1_noise",
        {
            "refit_matches_registered_run": bool(np.allclose(d2, diffs)),
            "model_selection": {
                "fraction_same_peak_count": float(same.mean()),
                "robust_sd_same_peak_count": rsd(d2[same]),
                "robust_sd_different_peak_count": rsd(d2[~same]),
                "fraction_within_0.05_same_peak_count": float(np.mean(np.abs(d2[same]) <= 0.05)),
            },
            "model": "Welch bins ~ scaled chi-squared(nu); log10 error SD sqrt(psi'(nu/2))/ln10; "
            "Hann bin correlation 0.444 (lag 1), 0.028 (lag 2); OLS sandwich covariance",
            "segments": k,
            "nu": nu,
            "per_bin_log10_sd": sigma,
            "predicted_sd_of_difference_rms": rms_pred,
            "measured_sd_of_difference_robust": robust_sd,
            "predicted_fraction_within_0.05": float(np.mean(pred_within)),
            "measured_fraction_within_0.05": float(np.mean(np.abs(diffs) <= 0.05)),
            "paired_design_predicted": 0.0,
            "paired_design_measured_median_abs": h1["secondary_paired"]["median_abs_peak_change"],
            "recording_length_for_90pct_within_0.05_s": t_needed,
        },
    )


# ----------------------------------------------------------------- 2. wPLI bias


def _independent_channels(seed: int, n_ch: int, duration: float) -> Recording:
    alpha = ChannelSpectrum(offset=0.0, exponent=1.0, peaks=(Peak(10.0, 1.5, 1.0),))
    n = int(duration * FS)
    data = np.stack([shaped_noise(alpha, n, FS, rng(seed, 30, c)) for c in range(n_ch)])
    return Recording(data=data, sfreq=FS, channels=tuple(f"C{c}" for c in range(n_ch)))


def _wpli_case(args: tuple[int, float]) -> dict[str, float]:
    seed, duration = args
    null = phase_coupling(_independent_channels(seed, 19, duration))
    mix = phase_coupling(mixed_sources(seed, duration_s=duration))
    return {
        "n_epochs": null.n_epochs,
        "null_wpli_mean": float(np.mean(null.upper("wpli"))),
        "null_dwpli_mean": float(np.mean(null.upper("dwpli"))),
        "mixed_wpli_mean": float(np.mean(mix.upper("wpli"))),
        "mixed_dwpli_mean": float(np.mean(mix.upper("dwpli"))),
    }


def exp_wpli_bias() -> None:
    """Null expectation of wPLI with N epochs.

    Im S of two independent complex Gaussians is Laplace(0, b): SD/E|X| = sqrt(2).
    E|sum X| ~ SD sqrt(2N/pi) and sum |X| ~ N E|X|, so E[wPLI] ~ 2 / sqrt(pi N).
    The debiased estimator's numerator is a U-statistic with expectation 0.
    """
    out: dict[str, Any] = {
        "model": "E[wPLI | no coupling] ~ 2/sqrt(pi*N); E[dwPLI^2 | no coupling] = 0"
    }
    for duration in (120.0, 600.0):
        with ProcessPoolExecutor(WORKERS) as ex:
            rows = list(ex.map(_wpli_case, [(s, duration) for s in range(20)]))
        n = rows[0]["n_epochs"]
        out[f"{duration:g}s"] = {
            "n_epochs": n,
            "predicted_wpli_mean": 2.0 / math.sqrt(math.pi * n),
            **{k: float(np.mean([r[k] for r in rows])) for k in rows[0] if k != "n_epochs"},
            "seeds": 20,
        }
    write_result("theory_wpli_bias", out)


# ----------------------------------------------------------------- 3. blinks


BLINK_SD_S = 0.08  # Gaussian blink shape used by the generator (synth/eeg.py)


def blink_ratio_peak(exponent: float, sigma: float = BLINK_SD_S) -> float:
    """Peak of the blink-train spectrum divided by a 1/f^chi background.

    A Poisson train of Gaussian bumps has PSD lambda |G(f)|^2 with
    |G(f)|^2 ~ exp(-4 pi^2 sigma^2 f^2). Divided by f^-chi, the ratio
    f^chi exp(-4 pi^2 sigma^2 f^2) peaks at f* = sqrt(chi / (8 pi^2 sigma^2)).
    """
    return math.sqrt(exponent / (8 * math.pi**2 * sigma**2))


def poisson_run_rate(
    rate_per_s: float, span_s: float, gap_s: float, min_s: float, hours: float, seed: int = 0
) -> float:
    """Rate per hour of merged runs at least `min_s` long when Poisson events each
    make an active span `span_s` and spans closer than `gap_s` merge (point-process
    model, simulated; no EEG involved)."""
    g = np.random.default_rng(seed)
    t_total = hours * 3600.0
    times = np.cumsum(g.exponential(1 / rate_per_s, size=int(rate_per_s * t_total * 1.2) + 10))
    times = times[times < t_total]
    runs, start, end = 0, times[0], times[0] + span_s
    for t in times[1:]:
        if t - end <= gap_s:
            end = t + span_s
        else:
            runs += end - start >= min_s
            start, end = t, t + span_s
    runs += end - start >= min_s
    return runs / hours


def _blink_case(seed: int) -> dict[str, Any]:
    spec = SynthSpec(duration_s=600.0, blinks_per_min=15.0, line_noise_uv=0.0)
    rec, gt = make_recording(7000 + seed, spec)
    clean = preprocess(rec, PipelineConfig())
    p = detector_params(PipelineConfig())
    chans = clean.good_channels
    x = band_limit(clean.data[clean.index(list(chans))], clean.sfreq, p.band_hz)
    z = line_length_z(x, clean.sfreq, p.window_s, p.step_s)
    singles = events_from_z(z, chans, dataclasses.replace(p, merge_gap_s=0.0, min_duration_s=0.0))
    counts = {}
    for gap in (1.0, 5.0):
        counts[gap] = len(events_from_z(z, chans, dataclasses.replace(p, merge_gap_s=gap)))
    bg = background_spectra(x, clean.sfreq)
    long_runs = events_from_z(z, chans, dataclasses.replace(p, merge_gap_s=5.0))
    fundamentals = []
    for e in long_runs:
        idx = [chans.index(c) for c in e.channels] or list(range(len(chans)))
        seg = x[idx, int(e.onset_s * clean.sfreq) : int(e.offset_s * clean.sfreq)]
        if seg.shape[-1] >= 2 * clean.sfreq:
            fundamentals.append(
                dominant_frequency(seg, clean.sfreq, p.band_hz, bg[idx].mean(axis=0))
            )
    exponent = float(np.mean([s.exponent for s in gt.spectra.values()]))
    return {
        "single_spans": [e.duration_s for e in singles],
        "runs_gap1": counts[1.0],
        "runs_gap5": counts[5.0],
        "fundamentals": fundamentals,
        "exponent": exponent,
        "predicted_peak_hz": blink_ratio_peak(exponent),
    }


def exp_blinks() -> None:
    """(a) Fourier: a band-limited blink train looks like a ~2 Hz rhythm;
    (b) point process: how the merge gap turns isolated blinks into long events."""
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_blink_case, range(20)))
    hours = 20 * 600 / 3600
    span = float(np.median([s for r in rows for s in r["single_spans"]]))
    # effective rate: blinks the detector sees (isolated supra-threshold runs), not the
    # generator's nominal 15/min; smaller blinks never cross the threshold
    rate = sum(len(r["single_spans"]) for r in rows) / (hours * 3600.0)
    nominal = 15.0 / 60.0
    p = DetectorParams()
    fund = [f for r in rows for f in r["fundamentals"]]
    pred_peaks = [r["predicted_peak_hz"] for r in rows]
    write_result(
        "theory_blinks",
        {
            "fourier_model": "ratio peak f* = sqrt(chi/(8 pi^2 sigma^2)), sigma = 80 ms",
            "predicted_ratio_peak_hz_median": float(np.median(pred_peaks)),
            "measured_fundamental_hz_median": float(np.median(fund)) if fund else None,
            "measured_fundamental_hz_iqr": [
                float(np.percentile(fund, 25)),
                float(np.percentile(fund, 75)),
            ]
            if fund
            else None,
            "n_measured_blink_events": len(fund),
            "gate_floor_hz": p.rhythm_hz[0],
            "point_process_model": "Poisson blinks (15/min), each active for the measured median "
            "single-blink span; spans closer than the merge gap merge; count runs >= 10 s",
            "single_blink_span_s_median": span,
            "nominal_blink_rate_per_min": nominal * 60,
            "effective_blink_rate_per_min": rate * 60,
            "predicted_long_runs_per_hour_nominal_rate": {
                "gap_1s": poisson_run_rate(nominal, span, 1.0, p.min_duration_s, 2000.0),
                "gap_5s": poisson_run_rate(nominal, span, 5.0, p.min_duration_s, 2000.0),
            },
            "predicted_long_runs_per_hour": {
                "gap_1s": poisson_run_rate(rate, span, 1.0, p.min_duration_s, 2000.0),
                "gap_5s": poisson_run_rate(rate, span, 5.0, p.min_duration_s, 2000.0),
            },
            "measured_long_runs_per_hour_before_gate": {
                "gap_1s": sum(r["runs_gap1"] for r in rows) / hours,
                "gap_5s": sum(r["runs_gap5"] for r in rows) / hours,
            },
            "hours": hours,
        },
    )


# ----------------------------------------------------------------- 4. power analysis


def p_wilson_lower_at_least(n: int, p_true: float, bound: float) -> float:
    """P(Wilson 95 % lower bound >= bound) when X ~ Binomial(n, p_true)."""
    return float(
        sum(stats.binom.pmf(x, n, p_true) for x in range(n + 1) if wilson(x, n)[0] >= bound)
    )


def n_for_power(p_true: float, bound: float, power: float = 0.8) -> int:
    for n in range(5, 2000):
        if p_wilson_lower_at_least(n, p_true, bound) >= power:
            return n
    return -1


def hours_for_rate(true_rate: float, limit: float, power: float = 0.8) -> float:
    """Hours of recording so that the 95 % Poisson upper bound is below `limit`
    with probability `power` when the true false-detection rate is `true_rate`."""
    for tenth in range(10, 20000):
        hours = tenth / 10
        mean = true_rate * hours
        ok = sum(
            stats.poisson.pmf(k, mean)
            for k in range(int(mean * 4) + 20)
            if poisson_upper(k, hours) <= limit
        )
        if ok >= power:
            return hours
    return float("nan")


def exp_power() -> None:
    """Was H6 able to answer its question? What would a confirmatory test need?"""
    held = _load("chbmit_heldout")
    n, hits = held["seizures"], held["hits"]
    rule_pass = {
        f"{p:.2f}": float(1 - stats.binom.cdf(math.ceil(0.6 * n) - 1, n, p))
        for p in (0.5, 0.6, 0.7, 0.8, 0.9)
    }
    write_result(
        "theory_power",
        {
            "h6_seizures": n,
            "h6_hits": hits,
            "h6_wilson": wilson(hits, n),
            "h6_wilson_width": wilson(hits, n)[1] - wilson(hits, n)[0],
            "p_pass_point_estimate_rule_by_true_sensitivity": rule_pass,
            "seizures_needed_wilson_lower_ge_0.6_power_0.8": {
                f"true_{p}": n_for_power(p, 0.6) for p in (0.7, 0.75, 0.8, 0.85)
            },
            "hours_needed_upper_bound_le_2_per_h_power_0.8": {
                f"true_{r}": hours_for_rate(r, 2.0) for r in (0.5, 1.0, 1.5)
            },
        },
    )


# ----------------------------------------------------------------- 5. Whittle MLE


def _peaks_from(x: np.ndarray, n_peaks: int) -> tuple[FittedPeak, ...]:
    return tuple(FittedPeak(*map(float, x[2 + 3 * k : 5 + 3 * k])) for k in range(n_peaks))


def _whittle_case(seed: int) -> dict[str, float]:
    """Log-space least squares (the pipeline) versus the Gamma/Whittle maximum
    likelihood for a Welch spectrum with nu degrees of freedom, same model."""
    g = rng(seed, 77)
    cs = random_spectrum(g)
    x = shaped_noise(cs, int(FS * 180), FS, g)
    sp = welch(Recording(data=x[None, :], sfreq=FS, channels=("X",)))
    m = (sp.freqs >= 2.0) & (sp.freqs <= 40.0)
    f, pw = sp.freqs[m], sp.psd[0][m]
    nu = welch_dof(sp.n_segments)
    ls = fit_spectrum(sp.freqs, sp.psd[0])
    x0 = [ls.offset, ls.exponent]
    lo, hi = [-np.inf, -1.0], [np.inf, 5.0]
    for p in ls.peaks:
        x0 += [p.freq, p.height, p.sd]
        lo += [p.freq - 2 * p.sd, 0.0, 0.5]
        hi += [p.freq + 2 * p.sd, np.inf, 4.0]

    def nll(theta: np.ndarray) -> float:
        logp = _model(f, theta[0], theta[1], _peaks_from(theta, len(ls.peaks))) * LN10
        return float(np.sum((nu / 2) * (logp + pw / np.exp(logp))))

    res = optimize.minimize(nll, x0, bounds=list(zip(lo, hi, strict=True)), method="L-BFGS-B")
    ml_offset, ml_exp = float(res.x[0]), float(res.x[1])
    ml_peaks = _peaks_from(res.x, len(ls.peaks))
    alpha_ls, alpha_ml = ls.peak_in((7, 14)), None
    cands = [p for p in ml_peaks if 7 <= p.freq <= 14]
    alpha_ml = max(cands, key=lambda p: p.height) if cands else None
    return {
        "nu": nu,
        "true_exponent": cs.exponent,
        "ls_exponent": ls.exponent,
        "ml_exponent": ml_exp,
        "true_offset": cs.offset,
        "ls_offset": ls.offset,
        "ml_offset": ml_offset,
        "true_alpha_height": cs.peaks[0].height,
        "ls_alpha_height": alpha_ls.height if alpha_ls else float("nan"),
        "ml_alpha_height": alpha_ml.height if alpha_ml else float("nan"),
    }


def exp_whittle() -> None:
    """Prediction: for large nu, least squares on log power is asymptotically
    as efficient as the Whittle MLE, with a constant offset bias
    (psi(nu/2) - ln(nu/2)) / ln 10 ~ -1/(nu ln 10) and no exponent bias."""
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_whittle_case, range(200)))
    a = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    nu = float(np.median(a["nu"]))

    def rmse(est: str, true: str) -> float:
        d = a[est] - a[true]
        d = d[np.isfinite(d)]
        return float(np.sqrt(np.mean(d**2)))

    write_result(
        "theory_whittle",
        {
            "n_spectra": len(rows),
            "nu": nu,
            "predicted_ls_offset_bias": float((special.digamma(nu / 2) - math.log(nu / 2)) / LN10),
            "measured_ls_offset_bias_vs_ml": float(np.median(a["ls_offset"] - a["ml_offset"])),
            "exponent_rmse_ls": rmse("ls_exponent", "true_exponent"),
            "exponent_rmse_ml": rmse("ml_exponent", "true_exponent"),
            "relative_efficiency_exponent_ml_over_ls": (
                rmse("ml_exponent", "true_exponent") / rmse("ls_exponent", "true_exponent")
            )
            ** 2,
            "alpha_height_rmse_ls": rmse("ls_alpha_height", "true_alpha_height"),
            "alpha_height_rmse_ml": rmse("ml_alpha_height", "true_alpha_height"),
            "exponent_ls_minus_ml_median": float(np.median(a["ls_exponent"] - a["ml_exponent"])),
        },
    )


# ----------------------------------------------------------------- 6. robust z


def mixture_z(eps: float, delta: float, robust: bool) -> float:
    """z of an event window (shift delta in background SD units) when a fraction
    eps of windows are events: N(0,1) background, N(delta,1) events."""
    if not robust:
        mean = eps * delta
        sd = math.sqrt(1 + eps * (1 - eps) * delta**2)
        return (delta - mean) / sd

    def cdf(x: float) -> float:
        return (1 - eps) * stats.norm.cdf(x) + eps * stats.norm.cdf(x - delta)

    med = optimize.brentq(lambda x: cdf(x) - 0.5, -10, 10 + delta)
    mad = optimize.brentq(lambda r: cdf(med + r) - cdf(med - r) - 0.5, 1e-9, 10 + delta)
    return (delta - med) / (MAD_TO_SD * mad)


def _robust_case(args: tuple[int, int]) -> dict[str, float]:
    seed, n_events = args
    spec = SynthSpec(duration_s=600.0, n_events=n_events, snr_db=6.0, event_duration_s=(55.0, 60.0))
    rec, gt = make_recording(8000 + seed, spec)
    clean = preprocess(rec, PipelineConfig())
    p = DetectorParams()
    chans = clean.good_channels
    x = band_limit(clean.data[clean.index(list(chans))], clean.sfreq, p.band_hz)
    win, step = int(p.window_s * FS), int(p.step_s * FS)
    diff = np.abs(np.diff(x, axis=-1))
    cs = np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(diff, axis=-1)], axis=-1)
    starts = np.arange(0, diff.shape[-1] - win + 1, step)
    log_ll = np.log((cs[:, starts + win] - cs[:, starts]) / win)
    t = starts / FS
    inside = np.zeros(t.size, dtype=bool)
    involved = set()
    for e in gt.events:
        inside |= (t >= e.onset_s + 3) & (t + p.window_s <= e.offset_s - 3)
        involved |= set(e.channels)
    rows = [chans.index(c) for c in involved if c in chans]
    out = {"eps": float(inside.mean())}
    for name, robust in (("robust", True), ("classical", False)):
        zs = []
        for i in rows:
            v = log_ll[i]
            if robust:
                med = np.median(v)
                z = (v - med) / (MAD_TO_SD * np.median(np.abs(v - med)))
            else:
                z = (v - v.mean()) / v.std()
            zs.append(np.median(z[inside]))
        out[f"{name}_event_z"] = float(np.median(zs))
    return out


def exp_robust_z() -> None:
    """Breakdown of mean/SD versus median/MAD z-scores as events fill the baseline."""
    analytic = {
        f"eps_{eps:.2f}": {
            "classical": mixture_z(eps, 6.0, robust=False),
            "robust": mixture_z(eps, 6.0, robust=True),
        }
        for eps in (0.0, 0.05, 0.1, 0.2, 0.3, 0.4)
    }
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_robust_case, [(s, n) for n in (1, 2, 3, 4) for s in range(5)]))
    by_n: dict[str, Any] = {}
    for n in (1, 2, 3, 4):
        sub = rows[(n - 1) * 5 : n * 5]
        by_n[f"{n}_events"] = {k: float(np.median([r[k] for r in sub])) for k in sub[0]}
    write_result(
        "theory_robust_z",
        {
            "model": "background N(0,1), events N(delta,1), contamination eps; delta = 6",
            "analytic_event_z": analytic,
            "threshold": DetectorParams().z_threshold,
            "measured_event_z_by_contamination": by_n,
        },
    )


EXPERIMENTS = {
    "h1_noise": exp_h1_noise,
    "wpli_bias": exp_wpli_bias,
    "blinks": exp_blinks,
    "power": exp_power,
    "whittle": exp_whittle,
    "robust_z": exp_robust_z,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment", choices=[*EXPERIMENTS, "all"])
    a = ap.parse_args()
    for name in EXPERIMENTS if a.experiment == "all" else [a.experiment]:
        EXPERIMENTS[name]()
        print(f"{name}: done", flush=True)


if __name__ == "__main__":
    main()
