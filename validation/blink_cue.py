"""Tune and evaluate the spatial blink cue (PROBLEM_STATEMENT §11).

    python validation/blink_cue.py tune       # synthetic tuning seeds 0-59 only
    python validation/blink_cue.py evaluate   # once, after tuning: D1-D6

Everything here follows the registration: the grid, the selection rule, the
stop rule and the criteria are copied from §11, not chosen after looking.
chb03 is never read. chb01 (D6) is a development set.

Every candidate event's fundamental and cue values are computed once per
recording; a grid setting only changes the thresholds applied to them. The
selected setting is then re-run through the real detector, and the counts
must match, so the shortcut cannot drift from `rhythm_gate`.
"""

from __future__ import annotations

import dataclasses
import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neurosignal.core.config import PipelineConfig
from neurosignal.core.recording import Recording
from neurosignal.core.stats import poisson_upper, wilson
from neurosignal.detection.events import Interval, score_events
from neurosignal.detection.seizure import (
    DetectorParams,
    background_spectra,
    band_limit,
    blink_cue,
    detect,
    dominant_frequency,
    events_from_z,
    line_length_z,
    robust_rms,
)
from neurosignal.pipeline import detector_params, preprocess
from neurosignal.synth.eeg import SynthSpec, bipolar_montage, make_recording
from validation.common import EVAL_SEEDS, ROOT, TUNING_SEEDS, detection_spec, write_result

# ---- registered in §11 -------------------------------------------------------
FLOOR_GRID = (1.0, 1.5)
FRONTALITY_GRID = (1.5, 2.0, 3.0, 4.0)
SYMMETRY_GRID = (0.5, 0.7)
MAX_FALSE_PER_HOUR = 2.0
MIN_SLOW_SENSITIVITY = 0.5  # stop rule
D1_MIN_SENSITIVITY = 0.847  # the H2 result
D2_MIN_SENSITIVITY, D2_MIN_LOWER = 0.70, 0.60
D4_MAX_EXTRA_PER_HOUR = 0.5
SLOW = {"event_f0_hz": (1.0, 1.8), "event_f1_min_hz": 1.0}
FRONTAL = {"event_centres": ("Fp1", "Fp2", "F7", "F8")}
ADVERSARIAL_SEEDS = range(2000, 2020)
ADVERSARIAL = {
    "baseline": {},
    "chewing": {"chewing_per_min": 0.3},
    "electrode_pops": {"electrode_pops_per_min": 0.3},
    "eye_flutter": {"eye_flutter_per_min": 0.3},
    "sweat": {"sweat_uv": 150.0},
}
MONTAGES = ("referential", "bipolar")
WORKERS = 4
# ------------------------------------------------------------------------------


def frozen() -> DetectorParams:
    """The detector frozen for H6; the cue's parameters are set per grid point."""
    return detector_params(PipelineConfig())


def _spec(seed: int, population: str) -> SynthSpec:
    base = detection_spec(seed)
    extra: dict[str, Any] = {
        "standard": {},
        "slow": SLOW,
        "frontal": FRONTAL,
        "frontal_slow": {**FRONTAL, **SLOW},
    }[population]
    return dataclasses.replace(base, **extra)


def _render(rec: Recording, montage: str) -> Recording:
    return rec if montage == "referential" else bipolar_montage(rec)


def prepare(rec: Recording, truth: list[Interval]) -> dict[str, Any]:
    """Candidates with their fundamental and cue, for one recording."""
    p = frozen()
    clean = preprocess(rec, PipelineConfig())
    chans = clean.analysed_channels
    x = band_limit(clean.data[clean.index(list(chans))], clean.sfreq, p.band_hz)
    z = line_length_z(x, clean.sfreq, p.window_s, p.step_s)
    bg = background_spectra(x, clean.sfreq)
    rms = robust_rms(x, clean.sfreq, p.window_s)
    nper = int(2 * clean.sfreq)
    cands = []
    for e in events_from_z(z, chans, p):
        idx = [chans.index(c) for c in e.channels] or list(range(len(chans)))
        seg = x[idx, int(e.onset_s * clean.sfreq) : int(e.offset_s * clean.sfreq)]
        ref = bg[idx].mean(axis=0) if seg.shape[-1] >= nper else None
        f = dominant_frequency(seg, clean.sfreq, p.band_hz, ref)
        cue = blink_cue(x, chans, clean.sfreq, e.onset_s, e.offset_s, rms)
        cands.append(
            {
                "onset_s": e.onset_s,
                "offset_s": e.offset_s,
                "f_hz": f,
                "frontality": None if cue is None else cue.frontality,
                "symmetry": None if cue is None else cue.symmetry,
            }
        )
    return {
        "truth": [[t.onset_s, t.offset_s] for t in truth],
        "duration_s": rec.duration_s,
        "candidates": cands,
    }


def kept(c: dict[str, Any], floor: float, frontality: float, symmetry: float) -> bool:
    """`rhythm_gate`'s decision for one candidate (verified against it)."""
    lo, hi = frozen().rhythm_hz
    if lo <= c["f_hz"] <= hi:
        return True
    if not floor <= c["f_hz"] < lo or c["frontality"] is None:
        return False
    return not (c["frontality"] >= frontality and c["symmetry"] >= symmetry)


def score(cases: list[dict[str, Any]], setting: tuple[float, float, float]) -> dict[str, Any]:
    hits = n_true = false = 0
    hours = 0.0
    for case in cases:
        truth = [Interval(a, b) for a, b in case["truth"]]
        det = [
            Interval(c["onset_s"], c["offset_s"]) for c in case["candidates"] if kept(c, *setting)
        ]
        sc = score_events(truth, det, case["duration_s"])
        hits, n_true = hits + sc.hits, n_true + sc.n_true
        false, hours = false + sc.false_detections, hours + sc.hours
    lo, hi = wilson(hits, n_true) if n_true else (0.0, 1.0)
    return {
        "hits": hits,
        "n_true": n_true,
        "sensitivity": hits / n_true if n_true else None,
        "sensitivity_wilson": [lo, hi],
        "false_detections": false,
        "hours": hours,
        "false_per_hour": false / hours if hours else 0.0,
        "false_per_hour_upper95": poisson_upper(false, hours),
    }


def _job(args: tuple[str, int, str, dict[str, Any] | None]) -> dict[str, Any]:
    population, seed, montage, artifacts = args
    if artifacts is None:
        spec = _spec(seed, population)
    else:
        spec = dataclasses.replace(detection_spec(seed), n_events=0, **artifacts)
    rec, gt = make_recording(seed, spec)
    truth = [Interval(e.onset_s, e.offset_s) for e in gt.events]
    out = prepare(_render(rec, montage), truth)
    return {"population": population, "seed": seed, "montage": montage, **out}


def _run(jobs: list[tuple[str, int, str, dict[str, Any] | None]]) -> list[dict[str, Any]]:
    with ProcessPoolExecutor(WORKERS) as ex:
        return list(ex.map(_job, jobs))


def _pick(cases: list[dict[str, Any]], **where: str) -> list[dict[str, Any]]:
    return [c for c in cases if all(c[k] == v for k, v in where.items())]


OFF = (2.0, 99.0, 99.0)  # floor at the gate's edge: the slow band is empty


def _verify(seed_specs: list[tuple[int, SynthSpec, str]], setting: tuple[float, ...]) -> int:
    """Detections from the real detector, summed over a few recordings."""
    p = dataclasses.replace(
        frozen(), slow_floor_hz=setting[0], blink_frontality=setting[1], blink_symmetry=setting[2]
    )
    total = 0
    for seed, spec, montage in seed_specs:
        rec, _ = make_recording(seed, spec)
        total += len(detect(preprocess(_render(rec, montage), PipelineConfig()), p))
    return total


def tune() -> None:
    seeds = list(TUNING_SEEDS)
    jobs = [(pop, s, m, None) for pop in ("standard", "slow") for s in seeds for m in MONTAGES]
    cases = _run(jobs)
    slow = _pick(cases, population="slow")
    rows = []
    for floor, fr, sy in itertools.product(FLOOR_GRID, FRONTALITY_GRID, SYMMETRY_GRID):
        everything, on_slow = score(cases, (floor, fr, sy)), score(slow, (floor, fr, sy))
        rows.append(
            {
                "slow_floor_hz": floor,
                "blink_frontality": fr,
                "blink_symmetry": sy,
                "false_per_hour": everything["false_per_hour"],
                "false_detections": everything["false_detections"],
                "hours": everything["hours"],
                "slow_sensitivity": on_slow["sensitivity"],
                "slow_hits": on_slow["hits"],
                "slow_n_true": on_slow["n_true"],
            }
        )
    baseline = {"all": score(cases, OFF), "slow": score(slow, OFF)}
    feasible = [r for r in rows if r["false_per_hour"] <= MAX_FALSE_PER_HOUR]
    # ties towards the setting that admits less: higher floor, lower F*, lower S*
    best = (
        max(
            feasible,
            key=lambda r: (
                r["slow_sensitivity"],
                r["slow_floor_hz"],
                -r["blink_frontality"],
                -r["blink_symmetry"],
            ),
        )
        if feasible
        else None
    )
    stop = best is None or best["slow_sensitivity"] < MIN_SLOW_SENSITIVITY
    verification = None
    if best is not None:
        setting = (best["slow_floor_hz"], best["blink_frontality"], best["blink_symmetry"])
        sample = [
            (s, _spec(s, pop), m)
            for s in seeds[:6]
            for pop in ("standard", "slow")
            for m in MONTAGES
        ]
        expected = sum(
            sum(kept(c, *setting) for c in case["candidates"])
            for case in cases
            if (case["seed"], case["montage"]) in {(s, m) for s, _, m in sample}
            and case["population"] in ("standard", "slow")
        )
        verification = {
            "recordings": len(sample),
            "shortcut": expected,
            "detector": _verify(sample, setting),
        }
    write_result(
        "blink_cue_tuning",
        {
            "seeds": [seeds[0], seeds[-1]],
            "registration": "PROBLEM_STATEMENT §11 (commits 62207a8, 4f4049e)",
            "grid": rows,
            "baseline_cue_off": baseline,
            "selected": best,
            "stop_rule_triggered": stop,
            "verification": verification,
            "cases": cases,
        },
    )
    print("selected:", best, "| stop rule:", stop, "| verification:", verification)


def _chb01(setting: tuple[float, float, float]) -> dict[str, Any]:
    """D6, development only: chb01's files chosen by the H5 file rule. Never
    chb03, which is spent (§11)."""
    import importlib.util

    from neurosignal.io.readers import read
    from validation.campaign import CHBMIT, parse_summary

    spec = importlib.util.spec_from_file_location("fetch", ROOT / "scripts" / "fetch_chbmit.py")
    assert spec and spec.loader
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    summary_path = CHBMIT / "chb01-summary.txt"
    files = fetch.select_files(summary_path.read_text())
    seizures = parse_summary(summary_path)
    assert all(f.startswith("chb01_") for f in files), "only chb01 is read here"
    cleaned = [(f, preprocess(read(CHBMIT / f), PipelineConfig())) for f in files]
    out = {}
    for name, s in (("cue_off", OFF), ("cue_on", setting)):
        p = dataclasses.replace(
            frozen(), slow_floor_hz=s[0], blink_frontality=s[1], blink_symmetry=s[2]
        )
        hits = n_true = false = 0
        hours = 0.0
        for f, clean in cleaned:
            det = [e.interval() for e in detect(clean, p)]
            truth = [Interval(a, b) for a, b in seizures.get(f, [])]
            sc = score_events(truth, det, clean.duration_s)
            hits, n_true = hits + sc.hits, n_true + sc.n_true
            false, hours = false + sc.false_detections, hours + sc.hours
        out[name] = {"hits": hits, "seizures": n_true, "false_detections": false,
                     "hours": hours, "false_per_hour": false / hours}  # fmt: skip
    return out


def evaluate() -> None:
    import json

    tuning = json.loads((ROOT / "results" / "validation" / "blink_cue_tuning.json").read_text())
    best = tuning["selected"]
    if tuning["stop_rule_triggered"] or best is None:
        raise SystemExit(
            "stop rule triggered at tuning: the cue is not adopted, nothing to evaluate"
        )
    setting = (best["slow_floor_hz"], best["blink_frontality"], best["blink_symmetry"])
    seeds = list(EVAL_SEEDS)
    jobs = [
        (pop, s, m, None)
        for pop in ("standard", "slow", "frontal", "frontal_slow")
        for s in seeds
        for m in MONTAGES
    ]
    jobs += [
        (kind, s, "referential", art)
        for kind, art in ADVERSARIAL.items()
        for s in ADVERSARIAL_SEEDS
    ]
    cases = _run(jobs)

    def both(sel: list[dict[str, Any]]) -> dict[str, Any]:
        return {"cue_on": score(sel, setting), "cue_off": score(sel, OFF)}

    d1 = both(_pick(cases, population="standard", montage="referential"))
    d2 = both(_pick(cases, population="slow"))
    d3 = both(_pick(cases, population="standard", montage="bipolar"))
    d4 = {k: both(_pick(cases, population=k)) for k in ADVERSARIAL}
    d5 = {
        pop: {m: both(_pick(cases, population=pop, montage=m)) for m in MONTAGES}
        for pop in ("frontal", "frontal_slow")
    }
    verdict = {
        "D1": d1["cue_on"]["sensitivity"] >= D1_MIN_SENSITIVITY
        and d1["cue_on"]["false_per_hour"] <= MAX_FALSE_PER_HOUR,
        "D2": d2["cue_on"]["sensitivity"] >= D2_MIN_SENSITIVITY
        and d2["cue_on"]["sensitivity_wilson"][0] >= D2_MIN_LOWER,
        "D3": d3["cue_on"]["false_per_hour"] <= MAX_FALSE_PER_HOUR,
        "D4": all(
            v["cue_on"]["false_per_hour"] <= v["cue_off"]["false_per_hour"] + D4_MAX_EXTRA_PER_HOUR
            for v in d4.values()
        ),
        "D5_normal_frequency_unchanged": all(
            d5["frontal"][m]["cue_on"]["hits"] == d5["frontal"][m]["cue_off"]["hits"]
            for m in MONTAGES
        ),
    }
    adopted = all(verdict[k] for k in ("D1", "D2", "D3", "D4"))
    chb01 = _chb01(setting)
    write_result(
        "blink_cue_evaluation",
        {
            "seeds": [seeds[0], seeds[-1]],
            "registration": "PROBLEM_STATEMENT §11 (commits 62207a8, 4f4049e)",
            "selected": dict(
                zip(("slow_floor_hz", "blink_frontality", "blink_symmetry"), setting, strict=True)
            ),
            "D1_standard_referential": d1,
            "D2_slow_both_montages": d2,
            "D3_standard_bipolar": d3,
            "D4_adversarial": d4,
            "D5_frontal_cost": d5,
            "D6_chb01_development": chb01,
            "verdict": verdict,
            "adopted": adopted,
        },
    )
    print("verdict:", verdict, "| adopted:", adopted, "| chb01:", chb01)


if __name__ == "__main__":
    {"tune": tune, "evaluate": evaluate}[sys.argv[1]]()
