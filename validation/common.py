"""Shared helpers for the validation campaign: result files with provenance,
and the synthetic dataset definitions (tuning and evaluation seeds disjoint)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neurosignal.core import provenance
from neurosignal.core.seeds import rng
from neurosignal.synth.eeg import SynthSpec, make_recording

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "validation"

TUNING_SEEDS = range(0, 60)  # detector thresholds are chosen here only (V-10)
EVAL_SEEDS = range(1000, 1200)  # H2 is measured here
SNR_LEVELS_DB = (0.0, 3.0, 6.0, 10.0)


def detection_spec(seed: int) -> SynthSpec:
    """Ten minutes; two discharges (none in one recording of five); blinks,
    muscle and normal alpha/spindle bursts; SNR cycles over levels."""
    g = rng(seed, 900)
    return SynthSpec(
        duration_s=600.0,
        n_events=0 if seed % 5 == 4 else 2,  # one recording in five has no events
        snr_db=SNR_LEVELS_DB[seed % len(SNR_LEVELS_DB)],
        n_flat=int(g.integers(0, 2)),
        n_noisy=int(g.integers(0, 2)),
        line_noise_uv=float(g.uniform(0.0, 20.0)),
        blinks_per_min=15.0,
        muscle_per_min=2.0,
        alpha_bursts_per_min=1.0,
    )


def explanation_metrics(seed: int) -> dict[str, Any]:
    """Metrics of a varied synthetic recording, for explanation experiments
    (H4: seeds 0-59; H7: seeds 100-129)."""
    from neurosignal.pipeline import analyse, build_metrics

    g = rng(seed, 400)
    spec = SynthSpec(
        duration_s=float(g.choice([120.0, 300.0])),
        n_events=int(g.integers(0, 3)),
        snr_db=float(g.choice([3.0, 10.0])),
        n_flat=int(g.integers(0, 2)),
        n_noisy=int(g.integers(0, 2)),
        blinks_per_min=10.0,
        alpha=bool(g.random() < 0.85),
    )
    try:
        rec, _ = make_recording(3000 + seed, spec)
    except ValueError:  # too short for the events requested
        rec, _ = make_recording(3000 + seed, SynthSpec(duration_s=300.0))
    return build_metrics(analyse(rec))


def write_result(name: str, payload: dict[str, Any], **prov: Any) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{name}.json"
    record = {"experiment": name, "provenance": provenance.collect(**prov), **payload}
    # LF on every platform, so files written on Windows match their committed form
    text = json.dumps(record, indent=2, sort_keys=True, default=float) + "\n"
    path.write_text(text, newline="\n")
    return path
