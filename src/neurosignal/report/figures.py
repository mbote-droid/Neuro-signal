"""Report figures, generated (never hand-edited), units on every axis.

Colours: two-series figures use slots 1 and 2 of a CVD-validated categorical
palette (blue, orange); matrices use a single-hue sequential map (Blues).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from neurosignal.pipeline import Analysis

BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#52514e"
GRID = "#e4e3df"

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "axes.edgecolor": INK,
        "axes.labelcolor": "#0b0b0b",
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 9,
        "svg.hashsalt": "neurosignal",  # deterministic SVG ids
    }
)


def spectrum_figure(an: Analysis, path: Path) -> Path:
    """Mean spectrum of good channels with the mean aperiodic and full fits."""
    good = [an.spectrum.channels.index(c) for c in an.fits]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    if good:
        f = an.spectrum.freqs
        lo, hi = an.config.fit_range_hz
        m = (f >= 1) & (f <= an.config.lowpass_hz)
        mean_psd = an.spectrum.psd[good].mean(axis=0)
        ax.loglog(f[m], mean_psd[m], color=BLUE, lw=2, label="mean spectrum")
        fm = (f >= lo) & (f <= hi)
        offs = np.mean([fit.offset for fit in an.fits.values()])
        expo = np.mean([fit.exponent for fit in an.fits.values()])
        ax.loglog(f[fm], 10 ** (offs - expo * np.log10(f[fm])), color=ORANGE, lw=2, ls="--",
                  label=f"aperiodic fit (mean exponent {expo:.2f})")  # fmt: skip
        a, b = an.config.alpha_band_hz
        ax.axvspan(a, b, color=GRID, alpha=0.6, lw=0, label=f"{a:g}-{b:g} Hz band")
        ax.legend(frameon=False)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel("power spectral density (µV²/Hz)")
    ax.set_title("Power spectrum, good channels", loc="left")
    return _save(fig, path)


def channel_figure(an: Analysis, path: Path) -> Path:
    """Per-channel aperiodic exponent and alpha peak power (two panels, one axis each)."""
    chans = list(an.fits)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.4, 4.4), sharex=True)
    x = np.arange(len(chans))
    ax1.bar(x, [an.fits[c].exponent for c in chans], color=BLUE, width=0.7)
    ax1.set_ylabel("aperiodic exponent")
    peaks = [an.fits[c].peak_in(an.config.alpha_search_hz) for c in chans]
    ax2.bar(x, [p.height if p else 0.0 for p in peaks], color=BLUE, width=0.7)
    ax2.set_ylabel("alpha peak power\n(log10 above fit)")
    ax2.set_xticks(x, chans, rotation=90)
    ax1.set_title("Per-channel spectral parameters", loc="left")
    return _save(fig, path)


def connectivity_figure(an: Analysis, path: Path) -> Path | None:
    c = an.connectivity
    if c is None:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6))
    vmax = max(float(np.nanmax(c.plv)), 1e-3)
    for ax, mat, title in ((axes[0], c.dwpli, "debiased wPLI"), (axes[1], c.plv, "PLV")):
        im = ax.imshow(np.clip(mat, 0, None), cmap="Blues", vmin=0, vmax=vmax)
        ax.set_title(f"{title} ({c.band[0]:g}-{c.band[1]:g} Hz)", loc="left")
        ax.set_xticks(range(len(c.channels)), c.channels, rotation=90, fontsize=6)
        ax.set_yticks(range(len(c.channels)), c.channels, fontsize=6)
        ax.grid(False)
    fig.colorbar(im, ax=axes, shrink=0.8, label="coupling (0-1, same scale)")
    return _save(fig, path, tight=False)


def events_figure(an: Analysis, path: Path) -> Path:
    from neurosignal.detection.seizure import band_limit, line_length_z
    from neurosignal.pipeline import detector_params

    p = detector_params(an.config)
    clean = an.clean
    fig, ax = plt.subplots(figsize=(7.6, 2.6))
    if clean.good_channels:
        x = band_limit(clean.data[clean.index(list(clean.good_channels))], clean.sfreq, p.band_hz)
        z = line_length_z(x, clean.sfreq, p.window_s, p.step_s)
        t = np.arange(z.shape[1]) * p.step_s + p.window_s / 2
        ax.plot(t, z.max(axis=0), color=BLUE, lw=1.0, label="max channel z (line length)")
        ax.axhline(p.z_threshold, color=INK, lw=1, ls=":", label=f"threshold z = {p.z_threshold:g}")
        for e in an.events:
            ax.axvspan(e.onset_s, e.offset_s, color=ORANGE, alpha=0.25, lw=0)
        ax.legend(frameon=False, loc="upper right")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("robust z")
    ax.set_title("Rhythmic seizure-like event candidates (shaded)", loc="left")
    return _save(fig, path)


def _save(fig: Figure, path: Path, tight: bool = True) -> Path:
    if tight:
        fig.tight_layout()
    fig.savefig(path, format="png", metadata={"Software": None})
    plt.close(fig)
    return path
