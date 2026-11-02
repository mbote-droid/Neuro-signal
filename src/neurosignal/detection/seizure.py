"""Rhythmic seizure-like event detector (F-12, ADR-008, EQUATIONS §7).

The signal is first band-limited to 1-20 Hz, where ictal rhythms live and
muscle (EMG) activity does not (docs/BUILD_JOURNAL.md ISSUE-002). Then line
length (Esteller et al. 2001) per channel in sliding windows,
    LL_w = (1 / N) sum_n |x[n] - x[n-1]|,
is compared with the recording's own baseline through a robust z-score of
log LL. A window is active when at least `channel_fraction` of the good
channels exceed `z_threshold`; active windows closer than `merge_gap_s`
are merged and events shorter than `min_duration_s` are dropped. Finally a
rhythmicity gate keeps an event only if its fundamental frequency lies in a
physiological band (delta-theta 2-7.5 Hz or delta-alpha 2-13 Hz; the
synthetic tuning rule chose between these two). The fundamental is the
lowest strong peak of the event spectrum *divided by the background
spectrum of the same channels*: a raw spectrum peaks at the lowest
frequencies because of the 1/f background (the H1 confound; BUILD_JOURNAL
ISSUE-008), and the largest ratio peak is often a harmonic (ISSUE-010).
Blinks and drift put the ratio peak near 1 Hz, muscle near 20 Hz.

Below the gate's floor a spatial cue can still admit an event
(PROBLEM_STATEMENT §11): blinks are frontopolar, bilateral and symmetric,
and slow ictal delta usually is not. An event whose fundamental lies in
[slow_floor_hz, rhythm_hz[0]) is kept when the cue is available and the
event is not blink-like. With slow_floor_hz equal to rhythm_hz[0] (the
default) the slow band is empty and the detector is exactly the one frozen
for H6.

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
    z_threshold: float = 2.5
    channel_fraction: float = 0.05
    min_duration_s: float = 10.0
    merge_gap_s: float = 1.0
    band_hz: tuple[float, float] = (1.0, 20.0)
    rhythm_hz: tuple[float, float] = (2.0, 7.5)
    # spatial blink cue (§11); slow_floor_hz == rhythm_hz[0] switches it off
    slow_floor_hz: float = 2.0
    blink_frontality: float = 3.0  # blink-like at or above this frontality...
    blink_symmetry: float = 0.5  # ...and at or above this left/right symmetry
    # baseline measured outside active windows (PROBLEM_STATEMENT §12); off = H6
    quiet_baseline: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {k: list(v) if isinstance(v, tuple) else v for k, v in self.__dict__.items()}


def log_line_length(x: FloatArray, sfreq: float, window_s: float, step_s: float) -> FloatArray:
    """Log line length per channel and window; x is (n_channels, n_samples)."""
    win = round(window_s * sfreq)
    step = round(step_s * sfreq)
    diff = np.abs(np.diff(x, axis=-1))
    if diff.shape[-1] < win:
        raise ValueError("recording shorter than one detection window")
    csum = np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(diff, axis=-1)], axis=-1)
    starts = np.arange(0, diff.shape[-1] - win + 1, step)
    ll = (csum[:, starts + win] - csum[:, starts]) / win
    return np.asarray(np.log(np.maximum(ll, 1e-12)), dtype=np.float64)


def robust_z(log_ll: FloatArray, baseline: np.ndarray | None = None) -> FloatArray:
    """(value - median) / (1.4826 MAD) per channel, the median and MAD taken over
    the windows in `baseline` (a boolean mask), or over all windows."""
    ref = log_ll if baseline is None else log_ll[:, baseline]
    med = np.median(ref, axis=-1, keepdims=True)
    spread = MAD_TO_SD * np.median(np.abs(ref - med), axis=-1, keepdims=True)
    return np.asarray((log_ll - med) / np.maximum(spread, 1e-6), dtype=np.float64)


def line_length_z(x: FloatArray, sfreq: float, window_s: float, step_s: float) -> FloatArray:
    """Robust z-score of log line length over the whole recording (the detector
    frozen for H6); x is (n_channels, n_samples)."""
    return robust_z(log_line_length(x, sfreq, window_s, step_s))


def quiet_baseline_z(log_ll: FloatArray, z_threshold: float, channel_fraction: float) -> FloatArray:
    """Robust z-score with each channel's baseline measured outside the windows
    where the detector is active (PROBLEM_STATEMENT §12).

    Over the whole recording, the baseline contains the discharges it is used
    to find: they widen the spread (by a median factor of 1.31 when a common
    average carries them into every channel) and make every other burst look
    smaller, so a recording's false-alarm rate fell with the number of its
    seizures. Pass 1 finds the active windows with the whole-recording z;
    each is widened by one step on each side, since a window spans more than
    one step; pass 2 measures median and MAD outside them. A recording with
    fewer than half its windows quiet keeps pass 1."""
    z1 = robust_z(log_ll)
    active = (z1 > z_threshold).mean(axis=0) >= channel_fraction
    widened = active.copy()
    widened[1:] |= active[:-1]
    widened[:-1] |= active[1:]
    quiet = ~widened
    if quiet.sum() < 0.5 * quiet.size:
        return z1
    return robust_z(log_ll, quiet)


def detector_z(x: FloatArray, sfreq: float, p: DetectorParams) -> FloatArray:
    """The z-scores `detect` thresholds; shared with tuning so the two cannot drift."""
    if p.quiet_baseline:
        return quiet_baseline_z(
            log_line_length(x, sfreq, p.window_s, p.step_s), p.z_threshold, p.channel_fraction
        )
    return line_length_z(x, sfreq, p.window_s, p.step_s)


def _runs(active: np.ndarray) -> list[tuple[int, int]]:
    """Inclusive (start, end) index pairs of True runs."""
    if not active.any():
        return []
    padded = np.concatenate([[False], active, [False]])
    edges = np.flatnonzero(np.diff(padded.astype(np.int8)))
    return [(int(a), int(b) - 1) for a, b in zip(edges[::2], edges[1::2], strict=True)]


def detect(rec: Recording, params: DetectorParams | None = None) -> list[DetectedEvent]:
    p = params or DetectorParams()
    chans = rec.analysed_channels  # EEG only: an ECG channel must not vote (ISSUE-017)
    if not chans:
        return []
    x = band_limit(rec.data[rec.index(list(chans))], rec.sfreq, p.band_hz)
    z = detector_z(x, rec.sfreq, p)
    return rhythm_gate(events_from_z(z, chans, p), x, chans, rec.sfreq, p)


def dominant_frequency(
    seg: FloatArray,
    sfreq: float,
    band: tuple[float, float],
    background: FloatArray | None = None,
    rel: float = 0.5,
) -> float:
    """Fundamental frequency of seg (channels, samples) within band: the lowest
    spectral peak reaching `rel` of the largest one, in the channel-averaged
    Welch spectrum divided by `background` when given.

    The lowest strong peak, not the largest: dividing by a 1/f background
    boosts the harmonics of a spike-wave train above its fundamental
    (BUILD_JOURNAL ISSUE-010)."""
    nper = min(seg.shape[-1], int(2 * sfreq))
    f, pxx = signal.welch(seg, fs=sfreq, nperseg=nper, axis=-1)
    spec = pxx.mean(axis=0) if pxx.ndim == 2 else pxx
    if background is not None and background.shape == spec.shape:
        spec = spec / np.maximum(background, 1e-30)
    m = (f >= band[0]) & (f <= band[1])
    fb, sb = f[m], spec[m]
    peaks, _ = signal.find_peaks(np.concatenate([[0.0], sb, [0.0]]))
    peaks = peaks - 1
    peaks = peaks[sb[peaks] >= rel * sb.max()]
    return float(fb[peaks.min()]) if peaks.size else float(fb[np.argmax(sb)])


def background_spectra(x: FloatArray, sfreq: float) -> FloatArray:
    """Per-channel Welch spectra of the whole band-limited recording."""
    nper = min(int(2 * sfreq), x.shape[-1])
    return np.asarray(signal.welch(x, fs=sfreq, nperseg=nper, axis=-1)[1], dtype=np.float64)


def rhythm_gate(
    events: list[DetectedEvent],
    x: FloatArray,
    chans: tuple[str, ...],
    sfreq: float,
    p: DetectorParams,
    background: FloatArray | None = None,
) -> list[DetectedEvent]:
    """`background` is background_spectra(x, sfreq), computed here if not given."""
    kept: list[DetectedEvent] = []
    if not events:
        return kept
    nper = int(2 * sfreq)
    bg = background if background is not None else background_spectra(x, sfreq)
    bg_rms: FloatArray | None = None  # computed only if an event falls in the slow band
    for e in events:
        idx = [chans.index(c) for c in e.channels] or list(range(len(chans)))
        seg = x[idx, int(e.onset_s * sfreq) : int(e.offset_s * sfreq)]
        ref = bg[idx].mean(axis=0) if seg.shape[-1] >= nper else None
        f_dom = dominant_frequency(seg, sfreq, p.band_hz, ref)
        if p.rhythm_hz[0] <= f_dom <= p.rhythm_hz[1]:
            kept.append(replace(e, dominant_freq_hz=f_dom))
        elif p.slow_floor_hz <= f_dom < p.rhythm_hz[0]:
            if bg_rms is None:
                bg_rms = robust_rms(x, sfreq, p.window_s)
            cue = blink_cue(x, chans, sfreq, e.onset_s, e.offset_s, bg_rms)
            if cue is not None and not cue.blink_like(p):
                kept.append(replace(e, dominant_freq_hz=f_dom))
    return kept


# Electrodes over the eyes, where a blink is largest (PROBLEM_STATEMENT §11).
FRONTOPOLAR_LEFT = frozenset({"FP1", "AF3", "AF7"})
FRONTOPOLAR_RIGHT = frozenset({"FP2", "AF4", "AF8"})
FRONTOPOLAR_MIDLINE = frozenset({"FPZ", "AFZ"})


def robust_rms(x: FloatArray, sfreq: float, window_s: float) -> FloatArray:
    """Each channel's typical level: the median RMS over non-overlapping
    windows. Not the RMS of the whole recording, which contains the event being
    measured and so caps an event's excess at sqrt(recording / event length)
    (PROBLEM_STATEMENT §11, amendment)."""
    win = max(1, round(window_s * sfreq))
    n = x.shape[-1] // win
    if n == 0:
        return np.asarray(np.sqrt(np.mean(x**2, axis=-1)), dtype=np.float64)
    windows = x[:, : n * win].reshape(x.shape[0], n, win)
    return np.asarray(np.median(np.sqrt(np.mean(windows**2, axis=-1)), axis=-1), dtype=np.float64)


def anterior_electrode(channel: str) -> str:
    """The electrode a channel mostly reflects: its own name in a referential
    montage, the first electrode of a derivation "A-B" (FP1-F7 -> FP1)."""
    name = channel.upper().removeprefix("EEG ").strip()
    return name.split("-", 1)[0]


@dataclass(frozen=True)
class BlinkCue:
    frontality: float  # median frontopolar excess / median excess elsewhere
    symmetry: float  # min / max of mean left and right frontopolar excess

    def blink_like(self, p: DetectorParams) -> bool:
        return self.frontality >= p.blink_frontality and self.symmetry >= p.blink_symmetry


def blink_cue(
    x: FloatArray,
    chans: tuple[str, ...],
    sfreq: float,
    onset_s: float,
    offset_s: float,
    background_rms: FloatArray,
) -> BlinkCue | None:
    """Where an event's amplitude rises above each channel's own level.

    Excess per channel is the RMS during the event over the channel's typical
    level (robust_rms), so a channel's impedance and baseline cancel. None
    when the cue cannot be measured: no analysed left or right frontopolar
    channel, or no other channel to compare with."""
    seg = x[:, int(onset_s * sfreq) : int(offset_s * sfreq)]
    if seg.shape[-1] == 0:
        return None
    excess = np.sqrt(np.mean(seg**2, axis=-1)) / np.maximum(background_rms, 1e-12)
    anterior = [anterior_electrode(c) for c in chans]
    left = [i for i, a in enumerate(anterior) if a in FRONTOPOLAR_LEFT]
    right = [i for i, a in enumerate(anterior) if a in FRONTOPOLAR_RIGHT]
    front = set(left) | set(right)
    front |= {i for i, a in enumerate(anterior) if a in FRONTOPOLAR_MIDLINE}
    other = [i for i in range(len(chans)) if i not in front]
    if not left or not right or not other:
        return None
    frontality = float(np.median(excess[sorted(front)]) / max(np.median(excess[other]), 1e-12))
    lm, rm = float(np.mean(excess[left])), float(np.mean(excess[right]))
    symmetry = min(lm, rm) / max(lm, rm, 1e-12)
    return BlinkCue(frontality, symmetry)


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
