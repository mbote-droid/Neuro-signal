"""Shared helpers for the validation campaign: result files with provenance,
and the synthetic dataset definitions (tuning and evaluation seeds disjoint)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neurosignal.core import provenance
from neurosignal.core.seeds import rng
from neurosignal.synth.eeg import SynthSpec

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "validation"

TUNING_SEEDS = range(0, 60)  # detector thresholds are chosen here only (V-10)
EVAL_SEEDS = range(1000, 1200)  # H2 is measured here
SNR_LEVELS_DB = (0.0, 3.0, 6.0, 10.0)


def detection_spec(seed: int) -> SynthSpec:
    """Ten minutes, two discharges, realistic artifacts; SNR cycles over levels."""
    g = rng(seed, 900)
    return SynthSpec(
        duration_s=600.0,
        n_events=2,
        snr_db=SNR_LEVELS_DB[seed % len(SNR_LEVELS_DB)],
        n_flat=int(g.integers(0, 2)),
        n_noisy=int(g.integers(0, 2)),
        line_noise_uv=float(g.uniform(0.0, 20.0)),
        blinks_per_min=15.0,
        muscle_per_min=2.0,
    )


def write_result(name: str, payload: dict[str, Any], **prov: Any) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{name}.json"
    record = {"experiment": name, "provenance": provenance.collect(**prov), **payload}
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=float) + "\n")
    return path
