"""Zero-phase linear-phase FIR filters (F-06, ADR-004, EQUATIONS §2).

A symmetric FIR of odd length N delays every frequency by (N-1)/2 samples.
Convolving with mode="same" removes exactly that delay, so the output has
zero phase and magnitude |H(f)| (not |H|² as forward-backward filtering
would give). Edges are padded by odd reflection to limit transients.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import signal

from neurosignal.core.recording import FloatArray, Recording
from neurosignal.core.stage import Stage

HAMMING_FACTOR = 3.3  # main-lobe width of the Hamming window: N ≈ 3.3 fs / Δf


def fir_length(sfreq: float, transition_hz: float) -> int:
    """Odd Hamming-window FIR length for a transition band of `transition_hz`."""
    n = math.ceil(HAMMING_FACTOR * sfreq / transition_hz)
    return n + 1 if n % 2 == 0 else n


def highpass_transition(l_freq: float) -> float:
    """Transition width rule from Widmann et al. (2015), as used by MNE."""
    return min(max(0.25 * l_freq, 2.0), l_freq)


def lowpass_transition(h_freq: float, sfreq: float) -> float:
    return min(max(0.25 * h_freq, 2.0), sfreq / 2 - h_freq)


def design_bandpass(l_freq: float, h_freq: float, sfreq: float) -> FloatArray:
    l_trans = highpass_transition(l_freq)
    h_trans = lowpass_transition(h_freq, sfreq)
    n = fir_length(sfreq, min(l_trans, h_trans))
    cutoffs = [l_freq - l_trans / 2, h_freq + h_trans / 2]
    return np.asarray(
        signal.firwin(n, cutoffs, window="hamming", pass_zero=False, fs=sfreq), dtype=np.float64
    )


def design_notch(freq: float, width: float, sfreq: float) -> FloatArray:
    """Band-stop with -6 dB at freq ± width/2 and full attenuation at freq ± width/4."""
    n = fir_length(sfreq, width / 2)
    cutoffs = [freq - width / 2, freq + width / 2]
    return np.asarray(
        signal.firwin(n, cutoffs, window="hamming", pass_zero=True, fs=sfreq), dtype=np.float64
    )


def zero_phase(x: FloatArray, h: FloatArray) -> FloatArray:
    """Apply a symmetric odd-length FIR along the last axis with zero phase."""
    if h.size % 2 == 0 or not np.allclose(h, h[::-1]):
        raise ValueError("zero_phase needs a symmetric, odd-length FIR")
    pad = min(h.size, x.shape[-1] - 1)
    left = 2 * x[..., :1] - x[..., pad:0:-1]
    right = 2 * x[..., -1:] - x[..., -2 : -pad - 2 : -1]
    padded = np.concatenate([left, x, right], axis=-1)
    y = signal.oaconvolve(padded, h[np.newaxis, :] if x.ndim == 2 else h, mode="same", axes=-1)
    return np.asarray(y[..., pad : pad + x.shape[-1]], dtype=np.float64)


def causal(x: FloatArray, h: FloatArray) -> FloatArray:
    """Causal (real-time) application: delays the signal by (N-1)/2 samples.
    Kept for the negative-control tests only; the pipeline never uses it."""
    return np.asarray(signal.lfilter(h, 1.0, x, axis=-1), dtype=np.float64)


class FilterStage(Stage):
    """Mains notch (and harmonics) then band-pass, one channel at a time (ADR-012)."""

    name = "filter"

    def __init__(self, l_freq: float, h_freq: float, line_freq: float, notch_width: float) -> None:
        self.l_freq, self.h_freq = l_freq, h_freq
        self.line_freq, self.notch_width = line_freq, notch_width
        self._lengths: dict[str, float] = {}
        self._notches: list[float] = []

    def process(self, rec: Recording) -> Recording:
        nyq = rec.sfreq / 2
        if self.h_freq >= nyq:
            raise ValueError(f"low-pass {self.h_freq} Hz is at or above Nyquist {nyq} Hz")
        bp = design_bandpass(self.l_freq, self.h_freq, rec.sfreq)
        self._notches = [
            k * self.line_freq
            for k in range(1, int(nyq // self.line_freq) + 1)
            if k * self.line_freq + self.notch_width < nyq
        ]
        notches = [design_notch(f, self.notch_width, rec.sfreq) for f in self._notches]
        self._lengths = {
            "bandpass_taps": int(bp.size),
            "lowpass_transition_hz": lowpass_transition(self.h_freq, rec.sfreq),
        }
        if notches:
            self._lengths["notch_taps"] = int(notches[0].size)
        out = np.empty_like(rec.data)
        for i in range(rec.n_channels):
            x = rec.data[i]
            for h in notches:
                x = zero_phase(x, h)
            out[i] = zero_phase(x, bp)
        return rec.evolve(data=out)

    def params(self) -> dict[str, Any]:
        return {
            "type": "FIR, Hamming window, zero-phase (single pass, delay compensated)",
            "highpass_hz": self.l_freq,
            "lowpass_hz": self.h_freq,
            "highpass_transition_hz": highpass_transition(self.l_freq),
            "notch_hz": self._notches,
            "notch_width_hz": self.notch_width,
            **self._lengths,
        }
