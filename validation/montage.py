"""Why does the detector raise more false alarms in a bipolar montage?
(BUILD_JOURNAL ISSUE-022, ROADMAP step 2b)

    python validation/montage.py diagnose   # one source at a time, tuning seeds
    python validation/montage.py power      # is the gap real? fresh seeds 5000-5199

Exploratory, on synthetic tuning seeds only: event-free recordings with one
source of realistic negatives at a time, each rendered in the referential
montage (as generated) and in CHB-MIT's bipolar montage, run through the
detector frozen for H6. The source whose false-alarm rate changes with the
montage is what a fix has to address; the fix itself is registered before it
is built (PROBLEM_STATEMENT §12).
"""

from __future__ import annotations

import dataclasses
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neurosignal.core.config import PipelineConfig
from neurosignal.core.stats import poisson_upper
from neurosignal.detection.seizure import detect
from neurosignal.pipeline import detector_params, preprocess
from neurosignal.synth.eeg import SynthSpec, bipolar_montage, make_recording
from validation.common import TUNING_SEEDS, detection_spec, write_result

QUIET = {
    "n_events": 0,
    "blinks_per_min": 0.0,
    "muscle_per_min": 0.0,
    "alpha_bursts_per_min": 0.0,
    "n_flat": 0,
    "n_noisy": 0,
    "line_noise_uv": 0.0,
}
SOURCES: dict[str, dict[str, Any]] = {
    "none": {},
    "blinks": {"blinks_per_min": 15.0},
    "muscle": {"muscle_per_min": 2.0},
    "alpha_bursts": {"alpha_bursts_per_min": 1.0},
    "bad_channels": {"n_flat": 1, "n_noisy": 1},
    "line_noise": {"line_noise_uv": 20.0},
}
MONTAGES = ("referential", "bipolar")
WORKERS = 4


def _spec(seed: int, source: str) -> SynthSpec:
    base = detection_spec(seed)
    if source == "benchmark":
        return dataclasses.replace(base, n_events=0)
    return dataclasses.replace(base, **{**QUIET, **SOURCES[source]})


def _case(args: tuple[str, int, str]) -> dict[str, Any]:
    source, seed, montage = args
    rec, _ = make_recording(seed, _spec(seed, source))
    if montage == "bipolar":
        rec = bipolar_montage(rec)
    clean = preprocess(rec, PipelineConfig())
    events = detect(clean, detector_params(PipelineConfig()))
    return {
        "source": source,
        "seed": seed,
        "montage": montage,
        "hours": rec.duration_s / 3600,
        "bad_channels": list(clean.bad_channels),
        "detections": [
            {
                "onset_s": e.onset_s,
                "duration_s": e.duration_s,
                "f_hz": e.dominant_freq_hz,
                "n_channels": len(e.channels),
                "channels": list(e.channels),
                "peak_z": e.peak_z,
            }
            for e in events
        ],
    }


def diagnose() -> None:
    seeds = list(TUNING_SEEDS)
    sources = [*SOURCES, "benchmark"]
    jobs = [(src, s, m) for src in sources for s in seeds for m in MONTAGES]
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_case, jobs))
    summary: dict[str, dict[str, Any]] = {}
    for src in sources:
        summary[src] = {}
        for m in MONTAGES:
            sub = [r for r in rows if r["source"] == src and r["montage"] == m]
            n = sum(len(r["detections"]) for r in sub)
            hours = sum(r["hours"] for r in sub)
            summary[src][m] = {
                "false_detections": n,
                "hours": hours,
                "false_per_hour": n / hours,
                "false_per_hour_upper95": poisson_upper(n, hours),
            }
    write_result(
        "montage_diagnosis",
        {
            "status": "exploratory, synthetic tuning seeds only (ISSUE-022)",
            "seeds": [seeds[0], seeds[-1]],
            "sources": SOURCES,
            "summary": summary,
            "rows": rows,
        },
    )
    for src, v in summary.items():
        print(
            f"{src:13s}",
            "  ".join(
                f"{m} {v[m]['false_per_hour']:.2f}/h ({v[m]['false_detections']})" for m in MONTAGES
            ),
        )


POWER_SEEDS = range(5000, 5200)  # exploratory only; disjoint from every other seed range


def _power_case(args: tuple[int, str, bool]) -> dict[str, Any]:
    """One benchmark recording, with or without its discharges. The discharges
    have their own random stream, so removing them leaves the background and
    every artifact byte-identical: a paired comparison."""
    seed, montage, with_events = args
    spec = detection_spec(seed)
    if not with_events:
        spec = dataclasses.replace(spec, n_events=0)
    rec, gt = make_recording(seed, spec)
    if montage == "bipolar":
        rec = bipolar_montage(rec)
    events = detect(preprocess(rec, PipelineConfig()), detector_params(PipelineConfig()))
    truth = [(e.onset_s, e.offset_s) for e in gt.events]
    false = [e for e in events if not any(e.onset_s < b and e.offset_s > a for a, b in truth)]
    return {"seed": seed, "montage": montage, "with_events": with_events,
            "hours": rec.duration_s / 3600, "false": len(false), "n_true": len(truth),
            "hits": sum(any(e.onset_s < b and e.offset_s > a for e in events) for a, b in truth)}  # fmt: skip


def power() -> None:
    seeds = list(POWER_SEEDS)
    jobs = [(s, m, w) for s in seeds for m in MONTAGES for w in (True, False)]
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_power_case, jobs))
    summary: dict[str, Any] = {}
    for w in (True, False):
        key = "with_discharges" if w else "same_recordings_without_discharges"
        summary[key] = {}
        for m in MONTAGES:
            sub = [r for r in rows if r["montage"] == m and r["with_events"] is w]
            n, hours = sum(r["false"] for r in sub), sum(r["hours"] for r in sub)
            hits, n_true = sum(r["hits"] for r in sub), sum(r["n_true"] for r in sub)
            summary[key][m] = {"false_detections": n, "hours": hours, "false_per_hour": n / hours,
                               "false_per_hour_upper95": poisson_upper(n, hours),
                               "hits": hits, "n_true": n_true}  # fmt: skip
        ref = {
            r["seed"]: r["false"]
            for r in rows
            if r["montage"] == "referential" and r["with_events"] is w
        }
        bip = {
            r["seed"]: r["false"]
            for r in rows
            if r["montage"] == "bipolar" and r["with_events"] is w
        }
        more, fewer = sum(bip[s] > ref[s] for s in seeds), sum(bip[s] < ref[s] for s in seeds)
        summary[key]["paired"] = {"bipolar_more": more, "bipolar_fewer": fewer,
                                  "sign_test_p_two_sided": _sign_test(more, fewer)}  # fmt: skip
    write_result(
        "montage_power",
        {
            "status": "exploratory, fresh seeds 5000-5199 (ISSUE-022)",
            "seeds": [seeds[0], seeds[-1]],
            "summary": summary,
            "rows": rows,
        },  # fmt: skip
    )
    for k, v in summary.items():
        print(
            k,
            {m: f"{v[m]['false_per_hour']:.2f}/h ({v[m]['false_detections']})" for m in MONTAGES},
            v["paired"],
        )


def _sign_test(more: int, fewer: int) -> float:
    """Exact two-sided sign test on recordings where the montages disagree."""
    from math import comb

    n, k = more + fewer, min(more, fewer)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


if __name__ == "__main__":
    {"diagnose": diagnose, "power": power}[sys.argv[1]]()
