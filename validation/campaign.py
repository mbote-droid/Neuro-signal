"""Validation campaign: one experiment per subcommand, one result file each.

    python validation/campaign.py <experiment> [--quick]

Every result file carries provenance (R-04); `validation/report.py` turns
them into docs/VALIDATION_REPORT.md. Hypothesis thresholds are those
pre-registered in docs/PROBLEM_STATEMENT.md §4.
"""

from __future__ import annotations

import argparse
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neurosignal.core.config import PipelineConfig
from neurosignal.core.provenance import sha256_file
from neurosignal.core.recording import Recording
from neurosignal.core.seeds import rng
from neurosignal.core.stats import poisson_upper, rule_of_three, wilson
from neurosignal.detection.events import Interval, score_events
from neurosignal.explain import template
from neurosignal.explain.checker import check
from neurosignal.features.aperiodic import fit_spectrum
from neurosignal.features.connectivity import phase_coupling
from neurosignal.features.spectral import band_power, welch
from neurosignal.pipeline import analyse, preprocess
from neurosignal.synth.eeg import (
    ChannelSpectrum,
    SynthSpec,
    coupled_pair,
    make_recording,
    mixed_sources,
    random_spectrum,
    shaped_noise,
)
from validation.common import (
    EVAL_SEEDS,
    ROOT,
    SNR_LEVELS_DB,
    detection_spec,
    explanation_metrics,
    write_result,
)
from validation.mutants import BLIND_SPOTS, OPERATORS

CHBMIT = ROOT / "data" / "raw" / "chbmit"
WORKERS = 4


def _single(x: np.ndarray, fs: float = 256.0) -> Recording:
    return Recording(data=x[None, :], sfreq=fs, channels=("X",))


# --------------------------------------------------------------------- aperiodic


def _aperiodic_case(seed: int) -> dict[str, Any]:
    g = rng(seed, 77)
    cs = random_spectrum(g)
    x = shaped_noise(cs, 256 * 180, 256.0, g)
    sp = welch(_single(x))
    fit = fit_spectrum(sp.freqs, sp.psd[0])
    peak = fit.peak_in((7.0, 14.0))
    out: dict[str, Any] = {
        "seed": seed,
        "true_exponent": cs.exponent,
        "fit_exponent": fit.exponent,
        "true_alpha_freq": cs.peaks[0].freq,
        "fit_alpha_freq": peak.freq if peak else None,
        "true_alpha_height": cs.peaks[0].height,
        "fit_alpha_height": peak.height if peak else None,
    }
    try:
        import specparam

        sm = specparam.SpectralModel(
            peak_width_limits=(1.0, 8.0), max_n_peaks=4, aperiodic_mode="fixed", verbose=False
        )
        sm.fit(sp.freqs, sp.psd[0], [2, 40])
        out["specparam_exponent"] = float(sm.results.get_params("aperiodic", "exponent"))
    except ImportError:
        out["specparam_exponent"] = None
    return out


def exp_aperiodic(quick: bool) -> None:
    """V-01, V-02, V-03."""
    n = 40 if quick else 200
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_aperiodic_case, range(n)))
    exp_err = np.array([abs(r["fit_exponent"] - r["true_exponent"]) for r in rows])
    found = [r for r in rows if r["fit_alpha_freq"] is not None]
    f_err = np.array([abs(r["fit_alpha_freq"] - r["true_alpha_freq"]) for r in found])
    h_err = np.array([r["fit_alpha_height"] - r["true_alpha_height"] for r in found])
    sp_rows = [r for r in rows if r["specparam_exponent"] is not None]
    agree = sum(abs(r["fit_exponent"] - r["specparam_exponent"]) <= 0.1 for r in sp_rows)
    write_result(
        "aperiodic",
        {
            "n": n,
            "exponent_median_abs_error": float(np.median(exp_err)),
            "exponent_p95_abs_error": float(np.percentile(exp_err, 95)),
            "alpha_detected": len(found),
            "alpha_freq_median_abs_error_hz": float(np.median(f_err)),
            "alpha_height_median_error": float(np.median(h_err)),
            "specparam_n": len(sp_rows),
            "specparam_agree": int(agree),
            "specparam_agree_wilson": wilson(int(agree), len(sp_rows)),
            "V-01_pass": bool(np.median(exp_err) <= 0.1),
            "V-02_pass": bool(np.median(f_err) <= 0.5),
            "V-03_pass": bool(agree / max(len(sp_rows), 1) >= 0.9),
            "rows": rows,
        },
    )


# --------------------------------------------------------------------- H1


def _h1_case(seed: int) -> dict[str, Any]:
    """Registered design: independent noise for each condition. Secondary
    (not registered): paired noise, which separates method bias from the
    sampling noise of two separate 3-minute recordings."""
    g = rng(seed, 101)
    base = random_spectrum(g, alpha=True)
    base = ChannelSpectrum(offset=base.offset, exponent=min(base.exponent, 1.7), peaks=base.peaks)
    conditions = {
        "base": base,
        "steeper": ChannelSpectrum(base.offset, base.exponent + 0.5, base.peaks),
        # sensitivity analysis: the same steepening pivoting at 20 Hz instead of 1 Hz
        "pivot20": ChannelSpectrum(
            base.offset + 0.5 * np.log10(20.0), base.exponent + 0.5, base.peaks
        ),
    }
    out: dict[str, Any] = {"seed": seed, "exponent": base.exponent}
    for design in ("independent", "paired"):
        vals = {}
        for k, (name, cs) in enumerate(conditions.items()):
            stream = rng(seed, 102, k if design == "independent" else 0)
            sp = welch(_single(shaped_noise(cs, 256 * 180, 256.0, stream)))
            pk = fit_spectrum(sp.freqs, sp.psd[0]).peak_in((7.0, 14.0))
            vals[name] = (float(band_power(sp, (8.0, 12.0))[0]), pk.height if pk else 0.0)
        for name in ("steeper", "pivot20"):
            out[f"{design}_{name}_bandpower_change"] = vals[name][0] / vals["base"][0] - 1
            out[f"{design}_{name}_peak_change"] = vals[name][1] - vals["base"][1]
    return out


def _h1_summary(rows: list[dict[str, Any]], prefix: str) -> dict[str, float]:
    bp = np.array([r[f"{prefix}_bandpower_change"] for r in rows])
    pk = np.array([r[f"{prefix}_peak_change"] for r in rows])
    return {
        "fraction_bandpower_change_ge_30pct": float(np.mean(np.abs(bp) >= 0.30)),
        "fraction_peak_change_le_0.05": float(np.mean(np.abs(pk) <= 0.05)),
        "median_bandpower_change": float(np.median(bp)),
        "median_peak_change": float(np.median(pk)),
        "median_abs_peak_change": float(np.median(np.abs(pk))),
        "p90_abs_peak_change": float(np.percentile(np.abs(pk), 90)),
    }


def exp_h1(quick: bool) -> None:
    """H1: band power moves with the exponent; parameterised peak power does not."""
    n = 40 if quick else 200
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_h1_case, range(n)))
    reg = _h1_summary(rows, "independent_steeper")
    write_result(
        "h1_confound",
        {
            "n": n,
            "registered": reg,
            "H1_accepted": bool(
                reg["fraction_bandpower_change_ge_30pct"] >= 0.95
                and reg["fraction_peak_change_le_0.05"] >= 0.90
            ),
            "secondary_paired": _h1_summary(rows, "paired_steeper"),
            "sensitivity_pivot_20hz_independent": _h1_summary(rows, "independent_pivot20"),
            "sensitivity_pivot_20hz_paired": _h1_summary(rows, "paired_pivot20"),
            "rows": rows,
        },
    )


# --------------------------------------------------------------------- QC


def _qc_case(seed: int) -> tuple[int, int, int]:
    g = rng(seed, 300)
    spec = SynthSpec(
        duration_s=120.0,
        n_flat=int(g.integers(0, 3)),
        n_noisy=int(g.integers(0, 3)),
        blinks_per_min=10.0,
        muscle_per_min=1.0,
    )
    rec, gt = make_recording(2000 + seed, spec)
    found = set(preprocess(rec, PipelineConfig()).bad_channels)
    truth = set(gt.bad_channels)
    return len(found & truth), len(found - truth), len(truth - found)


def exp_qc(quick: bool) -> None:
    """V-04."""
    n = 30 if quick else 100
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_qc_case, range(n)))
    tp, fp, fn = (sum(r[i] for r in rows) for i in range(3))
    recall, precision = tp / (tp + fn), tp / (tp + fp) if tp + fp else 1.0
    write_result(
        "qc",
        {
            "n_recordings": n,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "recall": recall,
            "precision": precision,
            "recall_wilson": wilson(tp, tp + fn),
            "precision_wilson": wilson(tp, tp + fp),
            "V-04_pass": bool(recall >= 0.95 and precision >= 0.95),
        },
    )


# --------------------------------------------------------------------- H2


def _detection_case(seed: int) -> dict[str, Any]:
    spec = detection_spec(seed)
    rec, gt = make_recording(seed, spec)
    an = analyse(rec)
    truth = [Interval(e.onset_s, e.offset_s) for e in gt.events]
    sc = score_events(truth, [e.interval() for e in an.events], rec.duration_s)
    return {
        "seed": seed,
        "snr_db": spec.snr_db,
        "hits": sc.hits,
        "n_true": sc.n_true,
        "false": sc.false_detections,
        "hours": sc.hours,
        "latencies_s": list(sc.onset_latencies_s),
    }


def exp_detection(quick: bool) -> None:
    """H2 on evaluation seeds (never used for tuning)."""
    seeds = list(EVAL_SEEDS)[: 40 if quick else None]
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_detection_case, seeds))
    hits = sum(r["hits"] for r in rows)
    n_true = sum(r["n_true"] for r in rows)
    false = sum(r["false"] for r in rows)
    hours = sum(r["hours"] for r in rows)
    lo, hi = wilson(hits, n_true)
    by_snr = {}
    for snr in SNR_LEVELS_DB:
        sub = [r for r in rows if r["snr_db"] == snr]
        h, n = sum(r["hits"] for r in sub), sum(r["n_true"] for r in sub)
        by_snr[f"{snr:g}"] = {"hits": h, "n": n, "sensitivity": h / n, "wilson": wilson(h, n)}
    lat = [x for r in rows for x in r["latencies_s"]]
    write_result(
        "detection_synthetic",
        {
            "seeds": [seeds[0], seeds[-1]],
            "n_recordings": len(rows),
            "hits": hits,
            "n_true": n_true,
            "sensitivity": hits / n_true,
            "sensitivity_wilson": [lo, hi],
            "false_detections": false,
            "hours": hours,
            "false_per_hour": false / hours,
            "false_per_hour_upper95": poisson_upper(false, hours),
            "onset_latency_median_s": float(np.median(lat)) if lat else None,
            "onset_latency_iqr_s": [float(np.percentile(lat, 25)), float(np.percentile(lat, 75))]
            if lat
            else None,
            "by_snr_db": by_snr,
            "H2_accepted": bool(hits / n_true >= 0.90 and lo >= 0.80 and false / hours <= 2.0),
            "rows": rows,
        },
    )


# --------------------------------------------------------------------- H3


def _conn_case(args: tuple[int, float]) -> dict[str, Any]:
    seed, dur = args
    c = phase_coupling(mixed_sources(seed, duration_s=dur))
    p = phase_coupling(coupled_pair(seed, duration_s=dur))
    return {
        "seed": seed,
        "duration_s": dur,
        "n_epochs": c.n_epochs,
        "plv_frac_gt_0.3": float(np.mean(c.upper("plv") > 0.3)),
        "wpli_p95": float(np.percentile(c.upper("wpli"), 95)),
        "dwpli_p95": float(np.percentile(c.upper("dwpli"), 95)),
        "pair_wpli": float(p.wpli[0, 1]),
        "pair_dwpli": float(p.dwpli[0, 1]),
    }


def exp_connectivity(quick: bool) -> None:
    """H3 at the minimum (120 s) and default (600 s) analysis lengths."""
    n = 10 if quick else 50
    payload: dict[str, Any] = {}
    for dur in (120.0, 600.0):
        with ProcessPoolExecutor(WORKERS) as ex:
            rows = list(ex.map(_conn_case, [(s, dur) for s in range(n)]))
        med = {
            k: float(np.median([r[k] for r in rows]))
            for k in rows[0]
            if k not in {"seed", "duration_s"}
        }
        ok_plv = med["plv_frac_gt_0.3"] >= 0.5
        payload[f"{dur:g}s"] = {
            "n": n,
            "median": med,
            "worst_wpli_p95": max(r["wpli_p95"] for r in rows),
            "worst_dwpli_p95": max(r["dwpli_p95"] for r in rows),
            "min_pair_wpli": min(r["pair_wpli"] for r in rows),
            "H3_as_registered_wpli": bool(
                ok_plv and med["wpli_p95"] <= 0.15 and min(r["pair_wpli"] for r in rows) > 0.5
            ),
            "H3_with_debiased_wpli": bool(
                ok_plv and med["dwpli_p95"] <= 0.15 and min(r["pair_dwpli"] for r in rows) > 0.5
            ),
            "rows": rows,
        }
    write_result("connectivity", payload)


# --------------------------------------------------------------------- H4


def _checker_case(seed: int) -> dict[str, Any]:
    metrics = explanation_metrics(seed)
    text = template.explain(metrics)
    faithful_ok = check(text, metrics).ok
    out: dict[str, Any] = {"seed": seed, "faithful_ok": faithful_ok, "ops": {}, "blind": {}}
    r = random.Random(seed)
    for name, op in OPERATORS.items():
        res = []
        for _ in range(4):
            m = op(text, metrics, r)
            if m is None:
                continue
            res.append({"equivalent": m.equivalent, "caught": not check(m.text, metrics).ok})
        out["ops"][name] = res
    for name, op in BLIND_SPOTS.items():
        m = op(text, metrics, r)
        out["blind"][name] = None if m is None else (not check(m.text, metrics).ok)
    return out


def exp_checker(quick: bool) -> None:
    """H4."""
    n = 15 if quick else 60
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_checker_case, range(n)))
    per_op = {}
    total = caught = equivalent = 0
    for name in OPERATORS:
        res = [x for r in rows for x in r["ops"][name]]
        eq = sum(x["equivalent"] for x in res)
        live = [x for x in res if not x["equivalent"]]
        c = sum(x["caught"] for x in live)
        per_op[name] = {"mutants": len(res), "equivalent": eq, "live": len(live), "caught": c}
        total += len(live)
        caught += c
        equivalent += eq
    faithful = sum(r["faithful_ok"] for r in rows)
    blind = {
        name: {"applied": sum(r["blind"][name] is not None for r in rows),
               "caught": sum(bool(r["blind"][name]) for r in rows)}
        for name in BLIND_SPOTS
    }  # fmt: skip
    write_result(
        "checker",
        {
            "n_explanations": n,
            "faithful_accepted": faithful,
            "live_mutants": total,
            "caught": caught,
            "equivalent_mutants": equivalent,
            "operators": per_op,
            "miss_rate_upper95": rule_of_three(total)
            if caught == total
            else wilson(total - caught, total)[1],
            "false_reject_upper95": rule_of_three(n)
            if faithful == n
            else wilson(n - faithful, n)[1],
            "blind_spots": blind,
            "H4_accepted": bool(
                caught == total and total >= 300 and len(per_op) >= 6 and faithful == n
            ),
        },
    )


# --------------------------------------------------------------------- H5 CHB-MIT


def parse_summary(path: Path) -> dict[str, list[tuple[float, float]]]:
    """File name -> list of (start, end) seizure times from chbNN-summary.txt."""
    out: dict[str, list[tuple[float, float]]] = {}
    current = None
    starts: list[float] = []
    for line in path.read_text().splitlines():
        if line.startswith("File Name:"):
            current = line.split(":", 1)[1].strip()
            out[current] = []
        elif current and re.match(r"Seizure( \d+)? Start Time", line):
            starts.append(float(re.findall(r"(\d+) seconds", line)[0]))
        elif current and re.match(r"Seizure( \d+)? End Time", line):
            out[current].append((starts.pop(), float(re.findall(r"(\d+) seconds", line)[0])))
    return out


def _chb_case(name: str) -> dict[str, Any]:
    from neurosignal.io.readers import read

    path = CHBMIT / name
    subject = name.split("_", maxsplit=1)[0]
    t0 = time.perf_counter()
    rec = read(path)
    an = analyse(rec)
    seizures = parse_summary(CHBMIT / f"{subject}-summary.txt").get(name, [])
    truth = [Interval(a, b) for a, b in seizures]
    sc = score_events(truth, [e.interval() for e in an.events], rec.duration_s)
    return {
        "file": name,
        "sha256": sha256_file(path),
        "hours": sc.hours,
        "seizures": seizures,
        "detections": [
            [e.onset_s, e.offset_s, e.dominant_freq_hz, len(e.channels)] for e in an.events
        ],
        "hits": sc.hits,
        "false": sc.false_detections,
        "latencies_s": list(sc.onset_latencies_s),
        "bad_channels": list(an.clean.bad_channels),
        "runtime_s": time.perf_counter() - t0,
    }


def _chbmit(subject: str, result: str, role: str, hypothesis: str) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("fetch", ROOT / "scripts" / "fetch_chbmit.py")
    assert spec and spec.loader
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    summary = CHBMIT / f"{subject}-summary.txt"
    if not summary.exists():
        raise SystemExit(f"no {subject} data; run `make data` first")
    files = fetch.select_files(summary.read_text())
    with ProcessPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(_chb_case, files))
    hits = sum(r["hits"] for r in rows)
    n_true = sum(len(r["seizures"]) for r in rows)
    false = sum(r["false"] for r in rows)
    hours = sum(r["hours"] for r in rows)
    lat = [x for r in rows for x in r["latencies_s"]]
    sens = hits / n_true if n_true else None
    payload: dict[str, Any] = {
        "dataset": f"CHB-MIT Scalp EEG Database v1.0.0 (PhysioNet), subject {subject}",
        "role": role,
        "files": len(rows),
        "hours": hours,
        "seizures": n_true,
        "hits": hits,
        "sensitivity": sens,
        "sensitivity_wilson": wilson(hits, n_true),
        "false_detections": false,
        "false_per_hour": false / hours,
        "false_per_hour_upper95": poisson_upper(false, hours),
        "onset_latency_median_s": float(np.median(lat)) if lat else None,
        "rows": rows,
    }
    if hypothesis == "H6":
        payload["H6_accepted"] = bool(sens is not None and sens >= 0.6 and false / hours <= 2.0)
    write_result(result, payload)


def exp_chbmit(quick: bool) -> None:
    """chb01: H5's test set, a development set after ISSUE-008 (post hoc)."""
    _chbmit("chb01", "chbmit", "development (post hoc after ISSUE-008)", "none")


def exp_chbmit_heldout(quick: bool) -> None:
    """H6: held-out subject chb03, detector frozen before download."""
    _chbmit("chb03", "chbmit_heldout", "held-out test of the frozen detector (H6)", "H6")


# --------------------------------------------------------------------- P-01


_RESOURCE_CHILD = """
import resource, sys, time, json
import numpy as np
from neurosignal.core.recording import Recording
from neurosignal.core.seeds import rng
from neurosignal.pipeline import analyse, build_metrics
from neurosignal.synth.eeg import ChannelSpectrum, Peak, shaped_noise
fs, n_ch, dur = 256.0, 32, 3600.0
n = int(fs * dur)
cs = ChannelSpectrum(1.5, 1.4, (Peak(10.0, 0.6, 1.2),))
data = np.empty((n_ch, n))
for i in range(n_ch):
    data[i] = shaped_noise(cs, n, fs, rng(0, i))
rec = Recording(data=data, sfreq=fs, channels=tuple(f"E{i+1}" for i in range(n_ch)))
del data
t0 = time.perf_counter()
build_metrics(analyse(rec))
elapsed = time.perf_counter() - t0
peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(json.dumps({"runtime_s": elapsed, "peak_rss_mb": peak_mb}))
"""


def exp_resources(quick: bool) -> None:
    """P-01: 1 hour, 32 channels, 256 Hz on one core."""
    import json
    import os

    env = {
        **os.environ,
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }
    out = subprocess.run(
        [sys.executable, "-c", _RESOURCE_CHILD], capture_output=True, text=True, env=env, check=True
    )
    m = json.loads(out.stdout.strip().splitlines()[-1])
    write_result(
        "resources",
        {
            "recording": "synthetic, 32 channels, 3600 s, 256 Hz (29.5 M samples, 236 MB float64)",
            "threads": 1,
            **m,
            "P-01_pass": bool(m["runtime_s"] <= 300 and m["peak_rss_mb"] <= 2048),
            "cpu": _cpu(),
        },
    )


def _cpu() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    import platform

    return platform.processor() or "unknown"


EXPERIMENTS = {
    "aperiodic": exp_aperiodic,
    "h1": exp_h1,
    "qc": exp_qc,
    "detection": exp_detection,
    "connectivity": exp_connectivity,
    "checker": exp_checker,
    "chbmit": exp_chbmit,
    "chbmit_heldout": exp_chbmit_heldout,
    "resources": exp_resources,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("experiment", choices=[*EXPERIMENTS, "all"])
    ap.add_argument("--quick", action="store_true", help="fewer cases, for smoke runs")
    a = ap.parse_args()
    names = list(EXPERIMENTS) if a.experiment == "all" else [a.experiment]
    for name in names:
        t0 = time.perf_counter()
        EXPERIMENTS[name](a.quick)
        print(f"{name}: {time.perf_counter() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
