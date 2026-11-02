"""Why does the detector raise more false alarms in a bipolar montage?
(BUILD_JOURNAL ISSUE-022, ROADMAP step 2b)

    python validation/montage.py diagnose   # one source at a time, tuning seeds
    python validation/montage.py power      # is the gap real? fresh seeds 5000-5199
    python validation/montage.py tune       # §12: re-tune with the quiet baseline, seeds 0-59
    python validation/montage.py evaluate   # §12: once, E1-E5, seeds 1000-1199

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
        },
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


# ---------------------------------------------------------------- §12 tuning


def _quiet(**kw: Any) -> Any:
    """The frozen detector with the quiet baseline on and `kw` overridden."""
    return dataclasses.replace(detector_params(PipelineConfig()), quiet_baseline=True, **kw)


def _tune_case(args: tuple[int, str]) -> dict[str, Any]:
    """Every grid setting on one recording; returns per-setting counts."""
    import itertools

    from neurosignal.detection.events import Interval, score_events
    from neurosignal.detection.seizure import (
        background_spectra,
        band_limit,
        events_from_z,
        log_line_length,
        quiet_baseline_z,
        rhythm_gate,
    )
    from validation.tune_detector import (
        FRACTION_GRID,
        MERGE_GAP_GRID,
        MIN_DURATION_GRID,
        RHYTHM_GRID,
        Z_GRID,
    )

    seed, montage = args
    rec, gt = make_recording(seed, detection_spec(seed))
    if montage == "bipolar":
        rec = bipolar_montage(rec)
    clean = preprocess(rec, PipelineConfig())
    chans = clean.analysed_channels
    p0 = _quiet()
    x = band_limit(clean.data[clean.index(list(chans))], clean.sfreq, p0.band_hz)
    ll = log_line_length(x, clean.sfreq, p0.window_s, p0.step_s)
    bg = background_spectra(x, clean.sfreq)
    truth = [Interval(e.onset_s, e.offset_s) for e in gt.events]
    out = []
    for zt, frac in itertools.product(Z_GRID, FRACTION_GRID):
        z = quiet_baseline_z(ll, zt, frac)
        for mind, rhythm, gap in itertools.product(MIN_DURATION_GRID, RHYTHM_GRID, MERGE_GAP_GRID):
            p = _quiet(z_threshold=zt, channel_fraction=frac, min_duration_s=mind,
                       rhythm_hz=rhythm, merge_gap_s=gap)  # fmt: skip
            det = [
                e.interval()
                for e in rhythm_gate(events_from_z(z, chans, p), x, chans, clean.sfreq, p, bg)
            ]
            sc = score_events(truth, det, rec.duration_s)
            out.append(
                [
                    zt,
                    frac,
                    mind,
                    list(rhythm),
                    gap,
                    sc.hits,
                    sc.n_true,
                    sc.false_detections,
                    sc.hours,
                ]
            )
    return {"seed": seed, "montage": montage, "event_free": not gt.events, "settings": out}


def tune() -> None:
    seeds = list(TUNING_SEEDS)
    with ProcessPoolExecutor(WORKERS) as ex:
        cases = list(ex.map(_tune_case, [(s, m) for s in seeds for m in MONTAGES]))
    keys = [
        tuple(map(lambda v: tuple(v) if isinstance(v, list) else v, row[:5]))
        for row in cases[0]["settings"]
    ]
    rows = []
    for i, key in enumerate(keys):
        tot = {m: [0, 0, 0, 0.0] for m in (*MONTAGES, "event_free")}
        for c in cases:
            h, n, f, hrs = c["settings"][i][5:]
            for k in (c["montage"], *(["event_free"] if c["event_free"] else [])):
                tot[k][0] += h
                tot[k][1] += n
                tot[k][2] += f
                tot[k][3] += hrs
        hits = sum(tot[m][0] for m in MONTAGES)
        n_true = sum(tot[m][1] for m in MONTAGES)
        false = sum(tot[m][2] for m in MONTAGES)
        hours = sum(tot[m][3] for m in MONTAGES)
        zt, frac, mind, rhythm, gap = key
        rows.append({
            "z_threshold": zt, "channel_fraction": frac, "min_duration_s": mind,
            "rhythm_hz": list(rhythm), "merge_gap_s": gap,
            "sensitivity": hits / n_true, "false_per_hour": false / hours,
            "hits": hits, "n_true": n_true, "false_detections": false, "hours": hours,
            "by_montage": {m: {"sensitivity": tot[m][0] / tot[m][1],
                               "false_per_hour": tot[m][2] / tot[m][3]} for m in MONTAGES},
            "event_free_false_per_hour": tot["event_free"][2] / tot["event_free"][3],
        })  # fmt: skip
    feasible = [r for r in rows if r["false_per_hour"] <= 2.0]
    # the H2 rule (validation/tune_detector.py): ties towards the conservative setting
    best = max(
        feasible,
        key=lambda r: (r["sensitivity"], r["z_threshold"], r["min_duration_s"],
                       -r["rhythm_hz"][1], -r["merge_gap_s"], -r["channel_fraction"]),
    ) if feasible else None  # fmt: skip
    frozen = detector_params(PipelineConfig())
    frozen_key = (frozen.z_threshold, frozen.channel_fraction, frozen.min_duration_s,
                  list(frozen.rhythm_hz), frozen.merge_gap_s)  # fmt: skip
    at_frozen = next(r for r in rows if (r["z_threshold"], r["channel_fraction"], r["min_duration_s"],
                                         r["rhythm_hz"], r["merge_gap_s"]) == frozen_key)  # fmt: skip
    write_result(
        "montage_tuning",
        {
            "registration": "PROBLEM_STATEMENT §12 (commit 59abd62)",
            "seeds": [seeds[0], seeds[-1]],
            "quiet_baseline_at_frozen_thresholds": at_frozen,
            "grid": rows,
            "selected": best,
            "stop_rule_triggered": best is None,
        },
    )
    print(
        "at frozen thresholds:",
        {
            k: at_frozen[k]
            for k in ("sensitivity", "false_per_hour", "event_free_false_per_hour", "by_montage")
        },
    )
    print("selected:", best)


# ------------------------------------------------------------ §12 evaluation


def _eval_case(args: tuple[int, str, dict[str, Any]]) -> dict[str, Any]:
    import numpy as np

    from neurosignal.detection.events import Interval, score_events
    from neurosignal.detection.seizure import band_limit, log_line_length, quiet_baseline_z

    seed, montage, sel = args
    spec = detection_spec(seed)
    rec, gt = make_recording(seed, spec)
    bare, _ = make_recording(seed, dataclasses.replace(spec, n_events=0))
    if montage == "bipolar":
        rec, bare = bipolar_montage(rec), bipolar_montage(bare)
    truth = [Interval(e.onset_s, e.offset_s) for e in gt.events]
    new, old = _quiet(**sel), detector_params(PipelineConfig())
    clean = preprocess(rec, PipelineConfig())
    out: dict[str, Any] = {"seed": seed, "montage": montage, "event_free": not gt.events,
                           "hours": rec.duration_s / 3600}  # fmt: skip
    for name, p in (("new", new), ("frozen", old)):
        sc = score_events(truth, [e.interval() for e in detect(clean, p)], rec.duration_s)
        out[name] = {"hits": sc.hits, "n_true": sc.n_true, "false": sc.false_detections}
    if gt.events:  # E4: the spread with and without this recording's discharges

        def spread(r: Any) -> Any:
            c = preprocess(r, PipelineConfig())
            ch = c.analysed_channels
            x = band_limit(c.data[c.index(list(ch))], c.sfreq, new.band_hz)
            ll = log_line_length(x, c.sfreq, new.window_s, new.step_s)
            z = quiet_baseline_z(ll, new.z_threshold, new.channel_fraction)
            return dict(zip(ch, np.std(ll, axis=-1) / np.std(z, axis=-1), strict=True))

        a, b = spread(rec), spread(bare)
        out["spread_ratio"] = float(np.median([a[c] / b[c] for c in a if c in b]))
    return out


def evaluate() -> None:
    import json

    import numpy as np

    from neurosignal.core.stats import wilson
    from validation.common import EVAL_SEEDS, ROOT

    tuning = json.loads((ROOT / "results" / "validation" / "montage_tuning.json").read_text())
    if tuning["stop_rule_triggered"]:
        raise SystemExit("stop rule triggered at tuning: nothing to evaluate")
    b = tuning["selected"]
    sel = {"z_threshold": b["z_threshold"], "channel_fraction": b["channel_fraction"],
           "min_duration_s": b["min_duration_s"], "rhythm_hz": tuple(b["rhythm_hz"]),
           "merge_gap_s": b["merge_gap_s"]}  # fmt: skip
    seeds = list(EVAL_SEEDS)
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_eval_case, [(s, m, sel) for s in seeds for m in MONTAGES]))

    def rates(sub: list[dict[str, Any]], which: str) -> dict[str, Any]:
        hits = sum(r[which]["hits"] for r in sub)
        n_true = sum(r[which]["n_true"] for r in sub)
        false, hours = sum(r[which]["false"] for r in sub), sum(r["hours"] for r in sub)
        return {"hits": hits, "n_true": n_true, "sensitivity": hits / n_true if n_true else None,
                "sensitivity_wilson": list(wilson(hits, n_true)) if n_true else None,
                "false_detections": false, "hours": hours, "false_per_hour": false / hours,
                "false_per_hour_upper95": poisson_upper(false, hours)}  # fmt: skip

    res: dict[str, Any] = {}
    for m in MONTAGES:
        sub = [r for r in rows if r["montage"] == m]
        ef = [r for r in sub if r["event_free"]]
        res[m] = {w: {"all": rates(sub, w), "event_free": rates(ef, w)} for w in ("new", "frozen")}
        res[m]["spread_ratio_median"] = float(
            np.median([r["spread_ratio"] for r in sub if "spread_ratio" in r])
        )
    verdict = {
        "E1": all(
            res[m]["new"][k]["false_per_hour"] <= 2.0
            for m in MONTAGES
            for k in ("all", "event_free")
        ),
        "E2": res["bipolar"]["new"]["all"]["false_per_hour"]
        <= res["referential"]["new"]["all"]["false_per_hour"] + 0.5,
        "E3": all(res[m]["new"]["all"]["sensitivity"] >= 0.80 for m in MONTAGES),
        "E4": all(0.95 <= res[m]["spread_ratio_median"] <= 1.05 for m in MONTAGES),
    }
    adopted = all(verdict.values())
    chb01 = _chb01(sel)
    write_result(
        "montage_evaluation",
        {
            "registration": "PROBLEM_STATEMENT §12 (commit 59abd62)",
            "seeds": [seeds[0], seeds[-1]],
            "selected": {**sel, "rhythm_hz": list(sel["rhythm_hz"])},
            "results": res,
            "E5_chb01_development": chb01,
            "verdict": verdict,
            "adopted": adopted,
            "rows": rows,
        },
    )
    for m in MONTAGES:
        print(m, {w: (round(res[m][w]["all"]["sensitivity"], 3), round(res[m][w]["all"]["false_per_hour"], 2),
                      round(res[m][w]["event_free"]["false_per_hour"], 2)) for w in ("new", "frozen")},
              "spread ratio", round(res[m]["spread_ratio_median"], 3))  # fmt: skip
    print("verdict:", verdict, "adopted:", adopted, "chb01:", chb01)


def _chb01(sel: dict[str, Any]) -> dict[str, Any]:
    """E5, development only: chb01 by the H5 file rule. chb03 is never read."""
    import importlib.util

    from neurosignal.detection.events import Interval, score_events
    from neurosignal.io.readers import read
    from validation.campaign import CHBMIT, parse_summary
    from validation.common import ROOT

    spec = importlib.util.spec_from_file_location("fetch", ROOT / "scripts" / "fetch_chbmit.py")
    assert spec and spec.loader
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    summary = CHBMIT / "chb01-summary.txt"
    files = fetch.select_files(summary.read_text())
    assert all(f.startswith("chb01_") for f in files), "only chb01 is read here"
    seizures = parse_summary(summary)
    cleaned = [(f, preprocess(read(CHBMIT / f), PipelineConfig())) for f in files]
    out = {}
    for name, p in (("frozen", detector_params(PipelineConfig())), ("new", _quiet(**sel))):
        hits = n_true = false = 0
        hours = 0.0
        for f, clean in cleaned:
            truth = [Interval(a, b) for a, b in seizures.get(f, [])]
            sc = score_events(truth, [e.interval() for e in detect(clean, p)], clean.duration_s)
            hits, n_true = hits + sc.hits, n_true + sc.n_true
            false, hours = false + sc.false_detections, hours + sc.hours
        out[name] = {"hits": hits, "seizures": n_true, "false_detections": false,
                     "hours": hours, "false_per_hour": false / hours}  # fmt: skip
    return out


if __name__ == "__main__":
    {"diagnose": diagnose, "power": power, "tune": tune, "evaluate": evaluate}[sys.argv[1]]()
