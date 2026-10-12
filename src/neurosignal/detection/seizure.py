"""Rhythmic seizure-like event detector (F-12, ADR-008, EQUATIONS §7).

The signal is first band-limited to 1-20 Hz, where ictal rhythms live and
muscle (EMG) activity does not (docs/BUILD_JOURNAL.md ISSUE-002). Then line
length (Esteller et al. 2001) per channel in sliding windows,
    LL_w = (1 / N) sum_n |x[n] - x[n-1]|,
is compared with the recording's own baseline through a robust z-score of
log LL. A window is active when at least `channel_fraction` of the good
channels exceed `z_threshold`; active windows closer than `merge_gap_s`
are merged and events shorter than `min_duration_s` are dropped. Finally a
rhythmicity gate keeps an event only if the dominant frequency of its
band-limited spectrum lies in 2-13 Hz (delta to alpha, where ictal rhythms
are); spectra peaking at the band edges come from blinks and drift (about
1 Hz) or muscle leaking into the band (about 20 Hz). The gate limits come
from physiology, not from tuning.

The detector is unsupervised: it never sees labels. Its thresholds were
chosen on synthetic tuning seeds only (validation/tune_detector.py).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from scipy import signal

from neurosignal.core.recording import FloatArray, Recording
from neurosignal.detection.events import Interval
from neurosignal.preprocessing.filters import design_bandpass, zero_phase
from neurosignal.preprocessing.qc import MAD_TO_SD


@dataclass(frozen=True)
class DetectedEvent:
    onset_s: float
    offset_s: float
    channels: tuple[str, ...]
    peak_z: float
    dominant_freq_hz: float | None = None

    @property
    def duration_s(self) -> float:
        return self.offset_s - self.onset_s

    def interval(self) -> Interval:
        return Interval(self.onset_s, self.offset_s)


@dataclass(frozen=True)
class DetectorParams:
    window_s: float = 2.0
    step_s: float = 1.0
    z_threshold: float = 3.0
    channel_fraction: float = 0.05
    min_duration_s: float = 8.0
    merge_gap_s: float = 5.0
    band_hz: tuple[float, float] = (1.0, 20.0)
    rhythm_hz: tuple[float, float] = (2.0, 13.0)

    def to_dict(self) -> dict[str, Any]:
        return {k: list(v) if isinstance(v, tuple) else v for k, v in self.__dict__.items()}


def line_length_z(x: FloatArray, sfreq: float, window_s: float, step_s: float) -> FloatArray:
    """Robust z-score of log line length; x is (n_channels, n_samples)."""
    win = round(window_s * sfreq)
    step = round(step_s * sfreq)
    diff = np.abs(np.diff(x, axis=-1))
    if diff.shape[-1] < win:
        raise ValueError("recording shorter than one detection window")
    csum = np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(diff, axis=-1)], axis=-1)
    starts = np.arange(0, diff.shape[-1] - win + 1, step)
    ll = (csum[:, starts + win] - csum[:, starts]) / win
    log_ll = np.log(np.maximum(ll, 1e-12))
    med = np.median(log_ll, axis=-1, keepdims=True)
    spread = MAD_TO_SD * np.median(np.abs(log_ll - med), axis=-1, keepdims=True)
    return np.asarray((log_ll - med) / np.maximum(spread, 1e-6), dtype=np.float64)


def _runs(active: np.ndarray) -> list[tuple[int, int]]:
    """Inclusive (start, end) index pairs of True runs."""
    if not active.any():
        return []
    padded = np.concatenate([[False], active, [False]])
    edges = np.flatnonzero(np.diff(padded.astype(np.int8)))
    return [(int(a), int(b) - 1) for a, b in zip(edges[::2], edges[1::2], strict=True)]


def detect(rec: Recording, params: DetectorParams | None = None) -> list[DetectedEvent]:
    p = params or DetectorParams()
    chans = rec.good_channels
    if not chans:
        return []
    x = band_limit(rec.data[rec.index(list(chans))], rec.sfreq, p.band_hz)
    z = line_length_z(x, rec.sfreq, p.window_s, p.step_s)
    return rhythm_gate(events_from_z(z, chans, p), x, chans, rec.sfreq, p)


def dominant_frequency(seg: FloatArray, sfreq: float, band: tuple[float, float]) -> float:
    """Peak of the channel-averaged Welch spectrum of seg (channels, samples) within band."""
    nper = min(seg.shape[-1], int(2 * sfreq))
    f, pxx = signal.welch(seg, fs=sfreq, nperseg=nper, axis=-1)
    mean = pxx.mean(axis=0) if pxx.ndim == 2 else pxx
    m = (f >= band[0]) & (f <= band[1])
    return float(f[m][np.argmax(mean[m])])


def rhythm_gate(
    events: list[DetectedEvent],
    x: FloatArray,
    chans: tuple[str, ...],
    sfreq: float,
    p: DetectorParams,
) -> list[DetectedEvent]:
    kept = []
    for e in events:
        idx = [chans.index(c) for c in e.channels] or list(range(len(chans)))
        seg = x[idx, int(e.onset_s * sfreq) : int(e.offset_s * sfreq)]
        f_dom = dominant_frequency(seg, sfreq, p.band_hz)
        if p.rhythm_hz[0] <= f_dom <= p.rhythm_hz[1]:
            kept.append(replace(e, dominant_freq_hz=f_dom))
    return kept


def band_limit(x: FloatArray, sfreq: float, band: tuple[float, float]) -> FloatArray:
    h = design_bandpass(band[0], band[1], sfreq)
    return np.stack([zero_phase(row, h) for row in x])


def events_from_z(z: FloatArray, chans: tuple[str, ...], p: DetectorParams) -> list[DetectedEvent]:
    """Threshold, vote, merge and filter; z is (n_channels, n_windows)."""
    frac = (z > p.z_threshold).mean(axis=0)
    active = frac >= p.channel_fraction
    gap = round(p.merge_gap_s / p.step_s)
    runs: list[tuple[int, int]] = []
    for a, b in _runs(active):
        if runs and a - runs[-1][1] - 1 <= gap:
            runs[-1] = (runs[-1][0], b)
        else:
            runs.append((a, b))
    events: list[DetectedEvent] = []
    for a, b in runs:
        onset = a * p.step_s
        offset = b * p.step_s + p.window_s
        if offset - onset < p.min_duration_s:
            continue
        seg = z[:, a : b + 1]
        med = np.median(seg, axis=1)
        involved = tuple(c for c, v in zip(chans, med, strict=True) if v > p.z_threshold)
        peak = float(np.max(np.median(seg, axis=0)))
        events.append(DetectedEvent(onset, offset, involved, peak))
    return events
