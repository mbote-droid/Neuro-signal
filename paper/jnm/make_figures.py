"""Figures for the Journal of Neuroscience Methods manuscript.

Every value is read from results/validation/*.json, except the first synthetic
campaign (sensitivity 0.955 at 0.69 false/h), whose result file is kept at
commit 19198f7. Writes vector PDF and 600 dpi TIFF (for upload) and 300 dpi
PNG (embedded in the manuscript) to paper/jnm/figures/.

    uv run --frozen python paper/jnm/make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results" / "validation"
OUT = Path(__file__).resolve().parent / "figures"

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#222222", "#6b6b6b", "#d9d9d9"
MM = 1 / 25.4  # Elsevier widths: 90 mm (single), 140 mm (1.5), 190 mm (double)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 7,
        "axes.titlesize": 8,
        "axes.labelsize": 7,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "legend.fontsize": 6.5,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "lines.linewidth": 1.2,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)


def load(name: str) -> dict:
    return json.loads((RES / f"{name}.json").read_text("utf-8"))


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(
        OUT / f"{name}.tiff", dpi=600, bbox_inches="tight", pil_kwargs={"compression": "tiff_lzw"}
    )
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")  # embedded in the manuscript
    plt.close(fig)


def panel(ax: plt.Axes, letter: str) -> None:
    ax.text(-0.16, 1.04, letter, transform=ax.transAxes, fontsize=9, fontweight="bold")


def fig1_workflow() -> None:
    """Pipeline, citation contract and the validation layer around them."""
    fig, ax = plt.subplots(figsize=(190 * MM, 84 * MM))
    ax.set_xlim(0, 190)
    ax.set_ylim(0, 84)
    ax.axis("off")

    def box(x, y, w, h, text, edge=INK, fill="white", bold=False, size=6.3):
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0,rounding_size=2", fc=fill, ec=edge, lw=0.8
            )
        )
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha="center",
            va="center",
            fontsize=size,
            color=INK,
            fontweight="bold" if bold else "normal",
            linespacing=1.3,
        )

    def arrow(x0, y0, x1, y1, color=INK, ls="-"):
        ax.add_patch(
            FancyArrowPatch(
                (x0, y0),
                (x1, y1),
                arrowstyle="-|>",
                mutation_scale=7,
                color=color,
                lw=0.8,
                linestyle=ls,
                shrinkA=0,
                shrinkB=0,
            )
        )

    w, gap, h = 28, 4, 17
    xs = [1 + i * (w + gap) for i in range(6)]
    stages = [
        "EEG file\nEDF, BDF,\nBrainVision",
        "Quality control\nflat, noisy and\nlow channels",
        "Zero-phase FIR\nfilters; average\nreference",
        "Event detector\nline length and\nrhythm gate",
        "Spectra outside\nevents; aperiodic\nfit; dwPLI",
        "metrics.json\nbyte-identical\nacross runs",
    ]
    ya = 56
    ax.text(1, 77, "A  Pipeline", fontsize=8, fontweight="bold", color=INK)
    for i, (x, t) in enumerate(zip(xs, stages, strict=True)):
        box(x, ya, w, h, t, fill="#eef4fc" if i in (0, 5) else "white", bold=i == 5)
        if i:
            arrow(x - gap, ya + h / 2, x, ya + h / 2)

    yb = 22
    ax.text(xs[3], 44, "B  Citation contract", fontsize=8, fontweight="bold", color=INK)
    box(xs[3], yb, w, h, "Report\nHTML and\nMarkdown", fill="#eef4fc")
    box(xs[4], yb, w, h, "Explainer\ntemplate, or LLM\n(metrics only)")
    box(xs[5], yb, w, h, "Claim checker\nrules, no model:\nvalue [[metric.key]]")
    arrow(xs[5] + w / 2, ya, xs[5] + w / 2, yb + h)
    arrow(xs[4] + w, yb + h * 0.7, xs[5], yb + h * 0.7)
    arrow(xs[5], yb + h * 0.3, xs[4] + w, yb + h * 0.3, color=ORANGE, ls="--")
    arrow(xs[4], yb + h / 2, xs[3] + w, yb + h / 2, color=BLUE)
    ax.text(
        xs[4] + w / 2,
        yb - 4,
        "rejected text: one repair round, then the template",
        fontsize=5.8,
        color=ORANGE,
        ha="center",
    )
    ax.text(
        xs[4] + w / 2,
        yb + h + 2,
        "accepted text goes to the report",
        fontsize=5.8,
        color=BLUE,
        ha="center",
    )

    ax.text(1, 44, "C  Validation-first protocol", fontsize=8, fontweight="bold", color=INK)
    items = [
        "Hypotheses H1-H7 with\nnumeric thresholds, committed\nbefore the code and data",
        "Synthetic ground truth;\ndisjoint tuning and\nevaluation seeds",
        "Held-out CHB-MIT subject\nnamed before download;\nfrozen detector, one run",
        "Mutation testing of the\ntest suite and the checker;\nfuzzing; outside reports",
    ]
    bw = (xs[3] - 2 * gap - xs[0]) / 2
    for i, t in enumerate(items):
        box(xs[0] + (i % 2) * (bw + gap), yb + 1 - (i // 2) * 21, bw, h, t, edge=MUTED)
    save(fig, "fig1_workflow")


def fig2_detector() -> None:
    syn, h5, h6 = load("detection_synthetic"), load("chbmit_h5_registered"), load("chbmit_heldout")
    fig, (a, b) = plt.subplots(
        1, 2, figsize=(190 * MM, 70 * MM), gridspec_kw={"width_ratios": [1.25, 1]}
    )
    a.axhspan(0.9, 1.15, xmin=0, xmax=2 / 4, color="#eef4fc", lw=0)
    a.text(
        1.95, 1.135, "H2 pass region (≥ 0.90, ≤ 2/h)", fontsize=6, color=BLUE, ha="right", va="top"
    )
    a.axvline(2, color=GRID, lw=0.8, ls="--")
    a.axhline(0.6, xmin=0, xmax=2 / 4, color=MUTED, lw=0.8, ls=":")
    a.text(0.08, 0.615, "H6: ≥ 0.60 at ≤ 2/h", fontsize=6, color=MUTED)
    pts = [
        ("Synthetic, first benchmark\n(commit 19198f7)", 0.955, None, 0.69, None, BLUE, "o"),
        (
            "Synthetic, final benchmark (H2)",
            syn["sensitivity"],
            syn["sensitivity_wilson"],
            syn["false_per_hour"],
            syn["false_per_hour_upper95"],
            BLUE,
            "s",
        ),
        (
            "CHB-MIT chb01, detector v1 (H5)",
            h5["sensitivity"],
            h5["sensitivity_wilson"],
            h5["false_per_hour"],
            h5["false_per_hour_upper95"],
            ORANGE,
            "^",
        ),
        (
            "CHB-MIT chb03, held out (H6)",
            h6["sensitivity"],
            h6["sensitivity_wilson"],
            h6["false_per_hour"],
            h6["false_per_hour_upper95"],
            ORANGE,
            "D",
        ),
    ]
    offsets = [(6, 2), (6, -10), (6, 4), (-6, 8)]
    for (label, s, ci, f, fu, c, m), (dx, dy) in zip(pts, offsets, strict=True):
        if ci:
            a.plot([f, f], ci, color=c, lw=0.8)
        if fu:
            a.plot([f, fu], [s, s], color=c, lw=0.8, ls=":")
        a.plot(f, s, m, ms=5.5, color=c, mec="white", mew=0.8)
        a.annotate(
            label,
            (f, s),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=6,
            color=INK,
            ha="right" if dx < 0 else "left",
        )
    a.set_xlim(0, 4)
    a.set_ylim(0, 1.15)
    a.set_xlabel("False detections per hour (dotted: one-sided 95 % upper bound)")
    a.set_ylabel("Sensitivity (bars: Wilson 95 % CI)")
    a.grid(axis="y", color=GRID, lw=0.4)
    panel(a, "A")

    snr = sorted(syn["by_snr_db"], key=float)
    x = np.arange(len(snr))
    sens = [syn["by_snr_db"][k]["sensitivity"] for k in snr]
    lo = [syn["by_snr_db"][k]["wilson"][0] for k in snr]
    hi = [syn["by_snr_db"][k]["wilson"][1] for k in snr]
    b.bar(x, sens, width=0.55, color=BLUE)
    b.errorbar(
        x,
        sens,
        yerr=[np.subtract(sens, lo), np.subtract(hi, sens)],
        fmt="none",
        ecolor=INK,
        elinewidth=0.7,
        capsize=2,
    )
    for xi, k in zip(x, snr, strict=True):
        n = syn["by_snr_db"][k]
        b.text(xi, 0.04, f"{n['hits']}/{n['n']}", ha="center", fontsize=6, color="white")
    b.axhline(0.9, color=MUTED, lw=0.8, ls="--")
    b.text(-0.45, 0.915, "H2 threshold 0.90", fontsize=6, color=MUTED)
    b.set_xticks(x, [f"{float(k):g}" for k in snr])
    b.set_xlabel("Event SNR (dB), final synthetic benchmark")
    b.set_ylabel("Sensitivity")
    b.set_ylim(0, 1.02)
    panel(b, "B")
    fig.tight_layout(w_pad=3)
    save(fig, "fig2_detector")


def fig3_wpli() -> None:
    con, th = load("connectivity"), load("theory_wpli_bias")
    fig, ax = plt.subplots(figsize=(90 * MM, 70 * MM))
    rng = np.random.default_rng(0)
    groups = [
        ("120s", "wpli_p95", "wPLI\n2 min", BLUE),
        ("600s", "wpli_p95", "wPLI\n10 min", BLUE),
        ("120s", "dwpli_p95", "dwPLI\n2 min", ORANGE),
        ("600s", "dwpli_p95", "dwPLI\n10 min", ORANGE),
    ]
    for i, (dur, key, _, c) in enumerate(groups):
        v = np.array([r[key] for r in con[dur]["rows"]])
        ax.plot(i + rng.uniform(-0.15, 0.15, v.size), v, "o", ms=2.6, color=c, alpha=0.75, mew=0)
        ax.plot([i - 0.25, i + 0.25], [np.median(v)] * 2, color=INK, lw=1.2)
    for i, dur in enumerate(("120s", "600s")):
        p = th[dur]["predicted_wpli_mean"]
        ax.plot([i - 0.3, i + 0.3], [p, p], color=MUTED, lw=0.8, ls=":")
    ax.axhline(0.15, color=MUTED, lw=0.8, ls="--")
    ax.text(3.45, 0.155, "H3 threshold 0.15", fontsize=6, color=MUTED, ha="right")
    ax.set_xticks(range(4), [g[2] for g in groups])
    ax.set_xlim(-0.6, 3.6)
    ax.set_ylabel("95th percentile over sensor pairs\n(no true coupling; 50 seeds)")
    ax.grid(axis="y", color=GRID, lw=0.4)
    save(fig, "fig3_wpli_bias")


def fig4_aperiodic() -> None:
    h1 = load("h1_confound")
    rows = h1["rows"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(140 * MM, 58 * MM))
    bp = 100 * np.array([r["independent_steeper_bandpower_change"] for r in rows])
    a.hist(bp, bins=np.arange(-90, -40, 2.5), color=BLUE, ec="white", lw=0.5)
    a.axvline(-30, color=MUTED, lw=0.8, ls="--")
    a.text(
        -31.5, a.get_ylim()[1] * 0.92, "H1: |change| ≥ 30 %", fontsize=6, color=MUTED, ha="right"
    )
    a.set_xlim(-92, -25)
    a.set_xlabel("8-12 Hz band power change (%)")
    a.set_ylabel("Recordings")
    panel(a, "A")

    bins = np.arange(-0.3, 0.31, 0.02)
    ind = [r["independent_steeper_peak_change"] for r in rows]
    par = [r["paired_steeper_peak_change"] for r in rows]
    b.hist(ind, bins=bins, color=BLUE, ec="white", lw=0.5, label="independent noise (registered)")
    b.hist(
        par,
        bins=bins,
        color=ORANGE,
        ec="white",
        lw=0.5,
        alpha=0.85,
        label="paired noise (method bias)",
    )
    b.axvspan(-0.05, 0.05, color=GRID, alpha=0.5, lw=0, zorder=0)
    b.text(-0.29, b.get_ylim()[1] * 0.45, "shaded: ± 0.05\ntolerance (H1)", fontsize=6, color=MUTED)
    b.set_xlabel("Fitted alpha peak power change (log10)")
    b.set_ylabel("Recordings")
    b.legend(frameon=False, loc="upper right")
    panel(b, "B")
    fig.tight_layout(w_pad=3)
    save(fig, "fig4_aperiodic_confound")


def fig5_checker() -> None:
    chk, gem, oll = load("checker"), load("llm_eval_gemini"), load("llm_eval_ollama")
    ops = chk["operators"]
    names = sorted(ops, key=lambda k: (ops[k]["caught_by_registered_checker"] / ops[k]["live"], k))
    fig, (a, b) = plt.subplots(
        1, 2, figsize=(190 * MM, 72 * MM), gridspec_kw={"width_ratios": [1.6, 1]}
    )
    y = np.arange(len(names))
    reg = [ops[k]["caught_by_registered_checker"] / ops[k]["live"] for k in names]
    cur = [ops[k]["caught"] / ops[k]["live"] for k in names]
    a.barh(y + 0.2, reg, height=0.38, color=ORANGE, label="checker as first released")
    a.barh(y - 0.2, cur, height=0.38, color=BLUE, label="corrected checker")
    a.set_yticks(y, [n.replace("_", " ") for n in names])
    a.set_xlim(0, 1)
    a.set_xlabel("Live mutants rejected (fraction)")
    a.legend(frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2)
    panel(a, "A")

    keys = ("accepted_first_attempt", "accepted_after_repair")
    labels = ["first attempt", "after one repair"]
    vals = {
        "gemini-3.8-flash": [gem[k] / gem["n"] for k in keys],
        "qwen2.5:3b": [oll[k] / oll["n"] for k in keys],
    }
    x = np.arange(2)
    for j, (m, v) in enumerate(vals.items()):
        bars = b.bar(x + (j - 0.5) * 0.36, v, width=0.34, color=(BLUE, ORANGE)[j], label=m)
        for r, val in zip(bars, v, strict=True):
            b.text(
                r.get_x() + r.get_width() / 2,
                val + 0.02,
                f"{round(val * 30)}/30",
                ha="center",
                fontsize=6,
                color=INK,
            )
    b.axhline(0.8, color=MUTED, lw=0.8, ls="--")
    b.text(1.55, 0.82, "H7a: 24/30", fontsize=6, color=MUTED, ha="right")
    b.set_xticks(x, labels)
    b.set_ylim(0, 1.12)
    b.set_ylabel("Explanations accepted (fraction of 30)")
    b.legend(frameon=False, loc="upper left")
    panel(b, "B")
    fig.tight_layout(w_pad=3)
    save(fig, "fig5_checker_llm")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for f in (fig1_workflow, fig2_detector, fig3_wpli, fig4_aperiodic, fig5_checker):
        f()
    print(f"wrote {OUT}")
