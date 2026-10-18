"""The composite: recording -> cleaned recording -> features -> metrics.

`analyse` runs the stages; `build_metrics` turns the results into the
`metrics.json` dictionary whose dotted keys are what explanations cite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from neurosignal.core import provenance
from neurosignal.core.config import PipelineConfig
from neurosignal.core.recording import Recording
from neurosignal.core.stage import Pipeline
from neurosignal.detection.seizure import DetectedEvent, DetectorParams, detect
from neurosignal.features.aperiodic import AperiodicFit, fit_spectrum
from neurosignal.features.connectivity import Connectivity, phase_coupling
from neurosignal.features.spectral import (
    Spectrum,
    band_power,
    relative_band_power,
    welch,
)
from neurosignal.preprocessing.filters import FilterStage
from neurosignal.preprocessing.qc import (
    LINE_REFERENCE_BAND_HZ,
    AmplitudeChannels,
    FlatChannels,
    line_noise_ratio,
)
from neurosignal.preprocessing.reference import CommonAverage

SIG_DIGITS = 6


@dataclass(frozen=True)
class Analysis:
    raw: Recording
    clean: Recording
    spectrum: Spectrum
    fits: dict[str, AperiodicFit]
    connectivity: Connectivity | None
    events: list[DetectedEvent]
    line_noise_before: np.ndarray
    line_noise_after: np.ndarray
    config: PipelineConfig


def detector_params(cfg: PipelineConfig) -> DetectorParams:
    return DetectorParams(
        window_s=cfg.ll_window_s,
        step_s=cfg.ll_step_s,
        z_threshold=cfg.ll_z_threshold,
        channel_fraction=cfg.ll_channel_fraction,
        min_duration_s=cfg.ll_min_duration_s,
        merge_gap_s=cfg.ll_merge_gap_s,
        band_hz=cfg.ll_band_hz,
        rhythm_hz=cfg.rhythm_band_hz,
    )


def preprocess(rec: Recording, cfg: PipelineConfig) -> Recording:
    chain = Pipeline(
        [
            FlatChannels(cfg.flat_tolerance_uv, cfg.flat_max_duration_s),
            FilterStage(cfg.highpass_hz, cfg.lowpass_hz, cfg.line_freq_hz, cfg.notch_width_hz),
            AmplitudeChannels(cfg.noisy_mad_ratio, cfg.low_mad_ratio),
            CommonAverage(),
        ]
    )
    return chain(rec)


def analyse(rec: Recording, cfg: PipelineConfig | None = None) -> Analysis:
    cfg = cfg or PipelineConfig()
    clean = preprocess(rec, cfg)
    # events first: background spectra and coupling are measured outside them
    events = detect(clean, detector_params(cfg))
    exclude = [(e.onset_s, e.offset_s) for e in events]
    spectrum = welch(clean, cfg.welch_window_s, cfg.welch_overlap, exclude)
    fits = {}
    for i, ch in enumerate(spectrum.channels):
        if ch in clean.bad_channels:
            continue
        fits[ch] = fit_spectrum(
            spectrum.freqs,
            spectrum.psd[i],
            freq_range=cfg.fit_range_hz,
            max_peaks=cfg.max_peaks,
            peak_threshold_sd=cfg.peak_threshold_sd,
            min_peak_height=cfg.min_peak_height,
            peak_width_limits=cfg.peak_width_limits_hz,
        )
    conn = None
    if len(clean.good_channels) >= 2:
        conn = phase_coupling(
            clean,
            cfg.alpha_band_hz,
            cfg.connectivity_epoch_s,
            cfg.max_connectivity_s,
            exclude=exclude,
        )
    return Analysis(
        raw=rec,
        clean=clean,
        spectrum=spectrum,
        fits=fits,
        connectivity=conn,
        events=events,
        line_noise_before=line_noise_ratio(rec.data, rec.sfreq, cfg.line_freq_hz),
        line_noise_after=line_noise_ratio(clean.data, clean.sfreq, cfg.line_freq_hz),
        config=cfg,
    )


def _round(x: Any) -> Any:
    """Round floats to SIG_DIGITS significant digits; recurse into containers."""
    if isinstance(x, dict):
        return {str(k): _round(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [_round(v) for v in x]
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, float):
        if not math.isfinite(x):
            return None
        return float(f"{x:.{SIG_DIGITS}g}")
    return x


def _summary(values: dict[str, float]) -> dict[str, Any]:
    arr = np.array(list(values.values()), dtype=float)
    if arr.size == 0:
        return {"mean": None, "sd": None, "min": None, "max": None, "by_channel": {}}
    return {
        "mean": float(arr.mean()),
        "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "min": float(arr.min()),
        "max": float(arr.max()),
        "by_channel": values,
    }


def _top_pairs(conn: Connectivity, k: int = 5) -> list[dict[str, Any]]:
    n = len(conn.channels)
    i, j = np.triu_indices(n, k=1)
    vals = conn.dwpli[i, j]
    order = np.argsort(-vals, kind="stable")[:k]
    return [
        {
            "a": conn.channels[i[o]],
            "b": conn.channels[j[o]],
            "dwpli": float(vals[o]),
            "plv": float(conn.plv[i[o], j[o]]),
        }
        for o in order
    ]


def build_metrics(an: Analysis, input_sha256: str | None = None) -> dict[str, Any]:
    cfg = an.config
    clean = an.clean
    good = [c for c in clean.channels if c not in clean.bad_channels]
    gidx = clean.index(good)
    alpha_bp = band_power(an.spectrum, cfg.alpha_band_hz)
    alpha_rel = relative_band_power(an.spectrum, cfg.alpha_band_hz)
    poor = {
        ch: f
        for ch, f in an.fits.items()
        if f.r_squared < cfg.min_fit_r_squared or not 0 <= f.exponent <= cfg.max_exponent
    }
    fits = {ch: f for ch, f in an.fits.items() if ch not in poor}
    alpha_peaks = {ch: f.peak_in(cfg.alpha_search_hz) for ch, f in fits.items()}
    with_alpha = {ch: p for ch, p in alpha_peaks.items() if p is not None}
    hist = {h["stage"]: h for h in clean.history}
    conn = an.connectivity
    total_event_s = sum(e.duration_s for e in an.events)
    metrics: dict[str, Any] = {
        "recording": {
            "subject_id": clean.subject_id,
            "n_channels": clean.n_channels,
            "channels": list(clean.channels),
            "sfreq_hz": clean.sfreq,
            "duration_s": clean.duration_s,
            "montage": "bipolar" if clean.is_bipolar else "referential",
        },
        "qc": {
            "bad_channels": list(clean.bad_channels),
            "n_bad": len(clean.bad_channels),
            "n_good": len(good),
            "flat": hist.get("qc_flat", {}).get("flat_channels", {}),
            "noisy": hist.get("qc_amplitude", {}).get("noisy_channels", {}),
            "low": hist.get("qc_amplitude", {}).get("low_channels", {}),
            "line_noise_reference_band_hz": list(LINE_REFERENCE_BAND_HZ),
            "line_noise_ratio_before_median": float(np.nanmedian(an.line_noise_before)),
            "line_noise_ratio_after_median": float(np.nanmedian(an.line_noise_after[gidx]))
            if good
            else None,
            "rereferenced": bool(hist.get("reference", {}).get("applied", False)),
        },
        "spectral": {
            "alpha_band_power_uv2": _summary(
                {c: float(alpha_bp[clean.channels.index(c)]) for c in good}
            ),
            "relative_alpha_power": _summary(
                {c: float(alpha_rel[clean.channels.index(c)]) for c in good}
            ),
            "n_segments": an.spectrum.n_segments,
            "event_windows_excluded": bool(an.events),
        },
        "aperiodic": {
            "exponent": _summary({c: f.exponent for c, f in fits.items()}),
            "offset": _summary({c: f.offset for c, f in fits.items()}),
            "r_squared": _summary({c: f.r_squared for c, f in fits.items()}),
            "poor_fit_channels": sorted(poor),
            "n_poor_fits": len(poor),
            "alpha_peak_freq_hz": _summary({c: p.freq for c, p in with_alpha.items()}),
            "alpha_peak_power": _summary({c: p.height for c, p in with_alpha.items()}),
            "n_channels_with_alpha": len(with_alpha),
        },
        "connectivity": None
        if conn is None
        else {
            "n_epochs": conn.n_epochs,
            "dwpli_mean": float(np.nanmean(conn.upper("dwpli"))),
            "wpli_mean": float(np.nanmean(conn.upper("wpli"))),
            "plv_mean": float(np.nanmean(conn.upper("plv"))),
            "top_pairs": _top_pairs(conn),
        },
        "events": {
            "n_events": len(an.events),
            "total_duration_s": float(total_event_s),
            "rate_per_hour": len(an.events) / (clean.duration_s / 3600.0),
            "list": [
                {
                    "onset_s": e.onset_s,
                    "offset_s": e.offset_s,
                    "duration_s": e.duration_s,
                    "channels": list(e.channels),
                    "n_channels": len(e.channels),
                    "peak_z": e.peak_z,
                    "dominant_freq_hz": e.dominant_freq_hz,
                }
                for e in an.events
            ],
        },
        "config": cfg.to_dict(),
        "processing": list(clean.history),
        "provenance": provenance.collect(input_sha256=input_sha256 or clean.source_sha256),
    }
    return dict(_round(metrics))


def flatten(metrics: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Dotted keys for every leaf: {"a": {"b": [1, 2]}} -> {"a.b.0": 1, "a.b.1": 2, "a.b": [1, 2]}.

    Lists of scalars are also kept whole so a channel list can be cited.
    """
    out: dict[str, Any] = {}
    items = metrics.items() if isinstance(metrics, dict) else enumerate(metrics)
    for k, v in items:
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        elif isinstance(v, list):
            if all(not isinstance(e, dict | list) for e in v):
                out[key] = v
            out.update(flatten(v, key + "."))  # type: ignore[arg-type]
        else:
            out[key] = v
    return out
