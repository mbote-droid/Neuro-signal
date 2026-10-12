"""Ground-truth generators (playbook §6.13, docs/DATA.md).

Each generator returns the signal and, separately, the answer the methods
must recover. Only tests and validation code ever hold a `GroundTruth`
(ARCHITECTURE §2).

Spectral synthesis: the expected one-sided PSD of a generated channel is
exactly the specparam model
    log10 P(f) = b - chi * log10 f + sum_k h_k exp(-(f - c_k)^2 / (2 s_k^2)),
built by shaping complex Gaussian noise in the frequency domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import signal

from neurosignal.core.recording import FloatArray, Recording
from neurosignal.core.seeds import rng

# Approximate 2-D scalp positions (unit disc, nose up) of the 10-20 system.
POSITIONS_1020: dict[str, tuple[float, float]] = {
    "Fp1": (-0.31, 0.95), "Fp2": (0.31, 0.95),
    "F7": (-0.81, 0.59), "F3": (-0.40, 0.52), "Fz": (0.0, 0.50), "F4": (0.40, 0.52),
    "F8": (0.81, 0.59),
    "T7": (-1.0, 0.0), "C3": (-0.50, 0.0), "Cz": (0.0, 0.0), "C4": (0.50, 0.0), "T8": (1.0, 0.0),
    "P7": (-0.81, -0.59), "P3": (-0.40, -0.52), "Pz": (0.0, -0.50), "P4": (0.40, -0.52),
    "P8": (0.81, -0.59),
    "O1": (-0.31, -0.95), "O2": (0.31, -0.95),
}  # fmt: skip
CHANNELS_1020: tuple[str, ...] = tuple(POSITIONS_1020)


@dataclass(frozen=True)
class Peak:
    """A Gaussian peak in log10 power: centre (Hz), height (log10 units), sd (Hz)."""

    freq: float
    height: float
    sd: float


@dataclass(frozen=True)
class ChannelSpectrum:
    offset: float
    exponent: float
    peaks: tuple[Peak, ...] = ()

    def log_power(self, freqs: FloatArray) -> FloatArray:
        f = np.maximum(freqs, 1e-12)
        out = self.offset - self.exponent * np.log10(f)
        for p in self.peaks:
            out = out + p.height * np.exp(-((f - p.freq) ** 2) / (2 * p.sd**2))
        return np.asarray(out, dtype=np.float64)


@dataclass(frozen=True)
class Event:
    onset_s: float
    offset_s: float
    channels: tuple[str, ...]
    snr_db: float


@dataclass(frozen=True)
class GroundTruth:
    spectra: dict[str, ChannelSpectrum]
    bad_channels: dict[str, str] = field(default_factory=dict)  # name -> "flat" | "noisy"
    events: tuple[Event, ...] = ()
    line_noise_uv: float = 0.0


def shaped_noise(
    spectrum: ChannelSpectrum, n: int, sfreq: float, gen: np.random.Generator
) -> FloatArray:
    """Gaussian noise whose expected one-sided PSD (µV²/Hz) is 10**log_power."""
    freqs = np.fft.rfftfreq(n, 1 / sfreq)
    psd = np.zeros_like(freqs)
    psd[1:] = 10.0 ** spectrum.log_power(freqs[1:])
    amp = np.sqrt(psd * sfreq * n / 2.0)
    coef = amp * (gen.standard_normal(freqs.size) + 1j * gen.standard_normal(freqs.size))
    coef /= np.sqrt(2.0)
    coef[0] = 0.0
    if n % 2 == 0:  # the Nyquist bin is real
        coef[-1] = coef[-1].real * np.sqrt(2.0)
    return np.fft.irfft(coef, n)


def random_spectrum(gen: np.random.Generator, alpha: bool = True) -> ChannelSpectrum:
    """Physiological ranges: exponent 0.8-2.2, alpha 8-12 Hz, optional beta."""
    peaks: list[Peak] = []
    if alpha:
        peaks.append(Peak(gen.uniform(8.0, 12.0), gen.uniform(0.3, 1.0), gen.uniform(0.8, 1.8)))
    if gen.random() < 0.5:
        peaks.append(Peak(gen.uniform(17.0, 28.0), gen.uniform(0.15, 0.5), gen.uniform(1.5, 3.0)))
    return ChannelSpectrum(
        offset=gen.uniform(1.0, 2.0), exponent=gen.uniform(0.8, 2.2), peaks=tuple(peaks)
    )


def spike_wave(
    t: FloatArray, f_start: float, f_end: float, spike_ms: float = 25.0, wave_ms: float = 120.0
) -> FloatArray:
    """Unit-RMS spike-and-slow-wave train whose rate glides from f_start to f_end."""
    duration = t[-1] - t[0] if t.size > 1 else 1.0
    freq = f_start + (f_end - f_start) * (t - t[0]) / duration
    phase = 2 * np.pi * np.cumsum(freq) * (t[1] - t[0] if t.size > 1 else 0.0)

    def bump(centre: float, width_s: float) -> FloatArray:
        d = np.angle(np.exp(1j * (phase - centre)))  # wrapped phase distance
        width = 2 * np.pi * freq * width_s
        return np.asarray(np.exp(-(d**2) / (2 * width**2)))

    wave = -1.0 * bump(0.0, spike_ms / 1000) + 0.6 * bump(np.pi * 0.7, wave_ms / 1000)
    wave -= wave.mean()
    rms = np.sqrt(np.mean(wave**2))
    return wave / rms if rms > 0 else wave


def _envelope(n: int, sfreq: float, ramp_s: float = 2.0) -> FloatArray:
    env = np.ones(n)
    r = min(int(ramp_s * sfreq), n // 2)
    if r > 0:
        ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, r))
        env[:r] = ramp
        env[-r:] = ramp[::-1]
    return env


def _neighbours(centre: str, radius: float, channels: tuple[str, ...]) -> list[tuple[str, float]]:
    cx, cy = POSITIONS_1020[centre]
    out = []
    for ch in channels:
        x, y = POSITIONS_1020[ch]
        d = float(np.hypot(x - cx, y - cy))
        if d <= radius:
            out.append((ch, float(np.exp(-((d / radius) ** 2)))))
    return out


@dataclass(frozen=True)
class SynthSpec:
    """What to put in a synthetic recording."""

    duration_s: float = 300.0
    sfreq: float = 256.0
    n_events: int = 0
    snr_db: float = 6.0
    event_duration_s: tuple[float, float] = (15.0, 60.0)
    n_flat: int = 0
    n_noisy: int = 0
    line_noise_uv: float = 10.0
    blinks_per_min: float = 0.0
    muscle_per_min: float = 0.0
    alpha_bursts_per_min: float = 0.0
    alpha: bool = True


def make_recording(seed: int, spec: SynthSpec | None = None) -> tuple[Recording, GroundTruth]:
    """A 19-channel 10-20 recording with known spectra, events and bad channels."""
    spec = spec or SynthSpec()
    n = round(spec.duration_s * spec.sfreq)
    t = np.arange(n) / spec.sfreq
    channels = CHANNELS_1020
    base = random_spectrum(rng(seed, 0), alpha=spec.alpha)
    spectra: dict[str, ChannelSpectrum] = {}
    data = np.empty((len(channels), n))
    for i, ch in enumerate(channels):
        g = rng(seed, 1, i)
        # channel spectra vary around the recording's spectrum
        peaks = tuple(
            Peak(p.freq + g.normal(0, 0.3), max(0.1, p.height + g.normal(0, 0.1)), p.sd)
            for p in base.peaks
        )
        cs = ChannelSpectrum(
            offset=base.offset + g.normal(0, 0.1),
            exponent=float(np.clip(base.exponent + g.normal(0, 0.1), 0.5, 2.5)),
            peaks=peaks,
        )
        spectra[ch] = cs
        data[i] = shaped_noise(cs, n, spec.sfreq, g)

    background_rms = np.sqrt(np.mean(data**2, axis=1))
    events = _add_events(data, t, seed, spec, channels, background_rms)
    _add_blinks(data, t, seed, spec, channels)
    _add_muscle(data, seed, spec, channels, background_rms)
    _add_alpha_bursts(data, seed, spec, channels, background_rms)
    if spec.line_noise_uv > 0:
        phase = rng(seed, 4).uniform(0, 2 * np.pi)
        data += spec.line_noise_uv * np.sin(2 * np.pi * 50.0 * t + phase)
    bad = _add_bad_channels(data, seed, spec, channels)
    # ground truth stays out of the recording (no annotations): ARCHITECTURE §2
    rec = Recording(
        data=data,
        sfreq=spec.sfreq,
        channels=channels,
        subject_id=f"synth-{seed}",
    )
    return rec, GroundTruth(
        spectra=spectra, bad_channels=bad, events=tuple(events), line_noise_uv=spec.line_noise_uv
    )


def _add_events(
    data: FloatArray,
    t: FloatArray,
    seed: int,
    spec: SynthSpec,
    channels: tuple[str, ...],
    background_rms: FloatArray,
) -> list[Event]:
    """Non-overlapping spike-wave discharges with at least 30 s between them."""
    g = rng(seed, 2)
    events: list[Event] = []
    slots = _event_slots(g, spec)
    for onset, dur in slots:
        centre = str(g.choice(channels))
        region = _neighbours(centre, radius=g.uniform(0.6, 1.2), channels=channels)
        f0 = g.uniform(3.0, 5.0)
        f1 = g.uniform(2.0, f0)
        i0, i1 = int(onset * spec.sfreq), int((onset + dur) * spec.sfreq)
        wave = spike_wave(t[i0:i1], f0, f1) * _envelope(i1 - i0, spec.sfreq)
        for ch, gain in region:
            k = channels.index(ch)
            amp = background_rms[k] * 10 ** (spec.snr_db / 20) * gain
            data[k, i0:i1] += amp * wave
        events.append(
            Event(onset, onset + dur, tuple(ch for ch, w in region if w > 0.3), spec.snr_db)
        )
    return events


def _event_slots(g: np.random.Generator, spec: SynthSpec) -> list[tuple[float, float]]:
    slots: list[tuple[float, float]] = []
    lo, hi = spec.event_duration_s
    for _ in range(spec.n_events * 50):
        if len(slots) == spec.n_events:
            break
        dur = float(g.uniform(lo, hi))
        onset = float(g.uniform(10.0, spec.duration_s - dur - 10.0))
        if all(onset > b + 30.0 or onset + dur < a - 30.0 for a, b in slots):
            slots.append((onset, onset + dur))
    if len(slots) < spec.n_events:
        raise ValueError("recording too short for the requested events")
    return sorted((a, b - a) for a, b in slots)


def _add_blinks(
    data: FloatArray, t: FloatArray, seed: int, spec: SynthSpec, channels: tuple[str, ...]
) -> None:
    if spec.blinks_per_min <= 0:
        return
    g = rng(seed, 3)
    n_blinks = g.poisson(spec.blinks_per_min * spec.duration_s / 60)
    gains = {"Fp1": 1.0, "Fp2": 1.0, "F7": 0.4, "F3": 0.4, "Fz": 0.4, "F4": 0.4, "F8": 0.4}
    for _ in range(n_blinks):
        centre = g.uniform(0, t[-1])
        amp = g.uniform(80, 200)
        bump = amp * np.exp(-((t - centre) ** 2) / (2 * 0.08**2))
        for ch, w in gains.items():
            data[channels.index(ch)] += w * bump


def _add_muscle(
    data: FloatArray,
    seed: int,
    spec: SynthSpec,
    channels: tuple[str, ...],
    background_rms: FloatArray,
) -> None:
    """Bursts of 20-60 Hz muscle activity (1-6 s) over temporal and frontal sites:
    high line length, short, not rhythmic; the detector must not report them."""
    if spec.muscle_per_min <= 0:
        return
    g = rng(seed, 6)
    sites = [c for c in ("T7", "T8", "F7", "F8", "P7", "P8") if c in channels]
    emg = ChannelSpectrum(offset=0.0, exponent=0.0)
    n_total = data.shape[1]
    for _ in range(g.poisson(spec.muscle_per_min * spec.duration_s / 60)):
        dur = int(g.uniform(1.0, 6.0) * spec.sfreq)
        i0 = int(g.uniform(0, n_total - dur))
        burst = shaped_noise(emg, dur, spec.sfreq, g)
        lo, hi = 20.0 / (spec.sfreq / 2), min(60.0, 0.45 * spec.sfreq) / (spec.sfreq / 2)
        b, a = signal.butter(4, [lo, hi], btype="band")
        burst = signal.filtfilt(b, a, burst) * _envelope(dur, spec.sfreq, ramp_s=0.3)
        burst /= max(np.sqrt(np.mean(burst**2)), 1e-12)
        for ch in g.choice(sites, size=int(g.integers(1, 4)), replace=False):
            k = channels.index(str(ch))
            data[k, i0 : i0 + dur] += g.uniform(1.0, 3.0) * background_rms[k] * burst


def _add_alpha_bursts(
    data: FloatArray,
    seed: int,
    spec: SynthSpec,
    channels: tuple[str, ...],
    background_rms: FloatArray,
) -> None:
    """Normal rhythms that are not events: posterior alpha bursts (eyes closed,
    drowsiness) of 3-30 s at 8-13 Hz, and spindle-like 11-15 Hz trains.
    Added after the CHB-MIT development run showed them as the main source of
    false detections (BUILD_JOURNAL ISSUE-009)."""
    if spec.alpha_bursts_per_min <= 0:
        return
    g = rng(seed, 7)
    posterior = [c for c in ("P3", "Pz", "P4", "P7", "P8", "O1", "O2") if c in channels]
    central = [c for c in ("F3", "Fz", "F4", "C3", "Cz", "C4") if c in channels]
    n_total = data.shape[1]
    for _ in range(g.poisson(spec.alpha_bursts_per_min * spec.duration_s / 60)):
        spindle = g.random() < 0.3
        dur = int((g.uniform(0.8, 2.5) if spindle else g.uniform(3.0, 30.0)) * spec.sfreq)
        i0 = int(g.uniform(0, n_total - dur))
        f0 = g.uniform(11.0, 15.0) if spindle else g.uniform(8.0, 13.0)
        rhythm = ChannelSpectrum(offset=0.0, exponent=0.0, peaks=(Peak(f0, 2.0, 0.4),))
        burst = shaped_noise(rhythm, dur, spec.sfreq, g) * _envelope(dur, spec.sfreq, ramp_s=0.5)
        burst /= max(float(np.sqrt(np.mean(burst**2))), 1e-12)
        for ch in central if spindle else posterior:
            k = channels.index(ch)
            data[k, i0 : i0 + dur] += g.uniform(1.5, 4.0) * background_rms[k] * burst


def _add_bad_channels(
    data: FloatArray, seed: int, spec: SynthSpec, channels: tuple[str, ...]
) -> dict[str, str]:
    g = rng(seed, 5)
    picks = g.choice(len(channels), size=spec.n_flat + spec.n_noisy, replace=False)
    bad: dict[str, str] = {}
    for j, k in enumerate(picks):
        if j < spec.n_flat:
            data[k] = g.uniform(-5, 5)  # disconnected: constant offset
            bad[channels[k]] = "flat"
        else:
            mad = np.median(np.abs(data - np.median(data, axis=1, keepdims=True)))
            data[k] = data[k] + g.normal(0, 15 * mad / 0.6745, data.shape[1])
            bad[channels[k]] = "noisy"
    return bad


def mixed_sources(
    seed: int,
    n_sources: int = 6,
    channels: tuple[str, ...] = CHANNELS_1020,
    duration_s: float = 120.0,
    sfreq: float = 256.0,
) -> Recording:
    """Independent alpha-band sources mixed instantaneously into sensors (H3).

    No source is coupled to any other, so every true coupling is zero; any
    phase locking between sensors comes from volume conduction alone.
    """
    n = int(duration_s * sfreq)
    g = rng(seed, 10)
    alpha = ChannelSpectrum(offset=0.0, exponent=1.0, peaks=(Peak(10.0, 1.5, 1.0),))
    sources = np.stack([shaped_noise(alpha, n, sfreq, rng(seed, 11, k)) for k in range(n_sources)])
    positions = g.uniform(-0.9, 0.9, size=(n_sources, 2))
    mixing = np.empty((len(channels), n_sources))
    for i, ch in enumerate(channels):
        x, y = POSITIONS_1020[ch]
        d = np.hypot(positions[:, 0] - x, positions[:, 1] - y)
        mixing[i] = 1.0 / (0.3 + d) ** 2
    sensors = mixing @ sources
    sensors += 0.05 * sensors.std() * g.standard_normal(sensors.shape)
    return Recording(data=sensors, sfreq=sfreq, channels=channels, subject_id=f"mix-{seed}")


def coupled_pair(
    seed: int,
    lag_s: float = 0.025,
    mixing: float = 0.3,
    duration_s: float = 120.0,
    sfreq: float = 256.0,
) -> Recording:
    """Two sensors over two truly coupled sources; the second lags the first."""
    n = int(duration_s * sfreq)
    lag = round(lag_s * sfreq)
    alpha = ChannelSpectrum(offset=0.0, exponent=1.0, peaks=(Peak(10.0, 1.5, 1.0),))
    s1 = shaped_noise(alpha, n + lag, sfreq, rng(seed, 20))
    s2 = s1[:n].copy()
    s1 = s1[lag:]
    noise = rng(seed, 21).standard_normal((2, n)) * 0.3 * s1.std()
    a = s1 + mixing * s2 + noise[0]
    b = s2 + mixing * s1 + noise[1]
    return Recording(
        data=np.stack([a, b]), sfreq=sfreq, channels=("A", "B"), subject_id=f"pair-{seed}"
    )
