"""Generate docs/VALIDATION_REPORT.md from result files; never hand-written.

Every number below is read from results/validation/*.json, each of which
carries provenance; the manifest lists their SHA-256 (R-04).

    python validation/report.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation.common import RESULTS, ROOT

OUT = ROOT / "docs" / "VALIDATION_REPORT.md"


def _load(name: str) -> dict[str, Any] | None:
    p = RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _f(x: float | None, d: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{d}f}"


def _ci(pair: list[float] | tuple[float, float]) -> str:
    return f"[{pair[0]:.3f}, {pair[1]:.3f}]"


def _verdict(ok: bool) -> str:
    return "**accepted**" if ok else "**rejected**"


def _link(name: str) -> str:
    return f"[`{name}.json`](../results/validation/{name}.json)"


def section_hypotheses(r: dict[str, Any]) -> list[str]:
    lines = [
        "## Hypotheses",
        "",
        "| hypothesis | pre-registered threshold | measured | verdict | evidence |",
        "|---|---|---|---|---|",
    ]
    if h1 := r.get("h1_confound"):
        reg = h1["registered"]
        lines.append(
            f"| H1 aperiodic confound | band power change >= 30 % in >= 95 %; peak change <= 0.05 log10 in >= 90 % "
            f"| {reg['fraction_bandpower_change_ge_30pct']:.1%} ; {reg['fraction_peak_change_le_0.05']:.1%} "
            f"| {_verdict(h1['H1_accepted'])} | {_link('h1_confound')} |"
        )
    if d := r.get("detection_synthetic"):
        lines.append(
            f"| H2 detection (synthetic) | sensitivity >= 0.90, Wilson lower >= 0.80, <= 2 false/h "
            f"| {d['sensitivity']:.3f} {_ci(d['sensitivity_wilson'])}; {d['false_per_hour']:.2f}/h "
            f"| {_verdict(d['H2_accepted'])} | {_link('detection_synthetic')} |"
        )
    if c := r.get("connectivity"):
        a, b = c["120s"], c["600s"]
        lines.append(
            "| H3 volume conduction (wPLI, as registered) | PLV > 0.3 in >= 50 % of pairs; wPLI p95 <= 0.15; lagged pair wPLI > 0.5 "
            f"| 120 s: wPLI p95 {a['median']['wpli_p95']:.3f}; 600 s: {b['median']['wpli_p95']:.3f} "
            f"| 120 s {_verdict(a['H3_as_registered_wpli'])}, 600 s {_verdict(b['H3_as_registered_wpli'])} | {_link('connectivity')} |"
        )
        lines.append(
            "| H3 with debiased wPLI (post hoc, see FINDINGS) | same thresholds | "
            f"120 s: dwPLI p95 {a['median']['dwpli_p95']:.3f}; 600 s: {b['median']['dwpli_p95']:.3f} "
            f"| 120 s {_verdict(a['H3_with_debiased_wpli'])}, 600 s {_verdict(b['H3_with_debiased_wpli'])} | {_link('connectivity')} |"
        )
    if k := r.get("checker"):
        lines.append(
            f"| H4 claim checker | all live mutants (>= 300, >= 6 operators) rejected; all faithful accepted "
            f"| {k['caught']}/{k['live_mutants']} caught; {k['faithful_accepted']}/{k['n_explanations']} faithful accepted "
            f"| {_verdict(k['H4_accepted'])} | {_link('checker')} |"
        )
    if m := r.get("chbmit_h5_registered"):
        lines.append(
            f"| H5 transfer to CHB-MIT chb01 (exploratory, detector v1) | >= 5 of 7 seizures at <= 2 false/h "
            f"| {m['hits']}/{m['seizures']} at {m['false_per_hour']:.2f}/h "
            f"| {_verdict(m['H5_accepted'])} | {_link('chbmit_h5_registered')} |"
        )
    if m := r.get("chbmit_heldout"):
        lines.append(
            f"| H6 held-out subject chb03 (frozen detector, one run) | >= 60 % of seizures at <= 2 false/h "
            f"| {m['hits']}/{m['seizures']} ({m['sensitivity']:.0%}, Wilson {_ci(m['sensitivity_wilson'])}) at {m['false_per_hour']:.2f}/h "
            f"| {_verdict(m['H6_accepted'])} | {_link('chbmit_heldout')} |"
        )
    if g := r.get("llm_eval_gemini"):
        lines.append(
            f"| H7a LLM explainer, cloud model ({', '.join(g['models_reported'])}) "
            f"| >= 24 of 30 accepted after at most one repair "
            f"| {g['accepted_after_repair']}/{g['n']} ({g['accepted_first_attempt']} first attempt) "
            f"| {_verdict(g['H7a_accepted'])} | {_link('llm_eval_gemini')} |"
        )
    if au := r.get("llm_audit"):
        g = au["gemini"]
        lines.append(
            f"| H7c blinded audit of accepted text, cloud model | <= 2 of 20 fail "
            f"| {g['failed']}/{g['audited']} fail (auditor not independent) "
            f"| {_verdict(au['H7c_accepted'])} | {_link('llm_audit')} |"
        )
    if "llm_eval_gemini" not in r:
        lines.append(
            "| H7 LLM explainer (Gemini, local Ollama model) | see PROBLEM_STATEMENT §10 "
            "| not yet run | pending | |"
        )
    return [*lines, ""]


def section_llm(r: dict[str, Any]) -> list[str]:
    runs = [r[n] for n in ("llm_eval_gemini", "llm_eval_ollama") if n in r]
    if not runs:
        return []
    lines = [
        "## LLM explainer under the citation contract (H7)",
        "",
        "30 synthetic recordings (seeds 100-129), temperature 0, at most one repair round with "
        "the checker's findings; text that fails twice is replaced by the template.",
        "",
        "| backend | model reported | accepted first attempt | accepted after repair "
        "| median s/call | most frequent first-attempt findings |",
        "|---|---|---|---|---|---|",
    ]
    for m in runs:
        top = sorted(m["finding_codes_first_attempt"].items(), key=lambda kv: -kv[1])[:3]
        lines.append(
            f"| {m['backend']} | {', '.join(m['models_reported'])} "
            f"| {m['accepted_first_attempt']}/{m['n']} {_ci(m['accepted_first_wilson'])} "
            f"| {m['accepted_after_repair']}/{m['n']} {_ci(m['accepted_after_repair_wilson'])} "
            f"| {m['seconds_per_call_median']:.1f} "
            f"| {', '.join(f'{k} ({v})' for k, v in top) or 'none'} |"
        )
    if rc := r.get("llm_recheck"):
        lines += [
            "",
            "Secondary analysis: the saved replies under the corrected checker "
            "(ISSUE-012; primary verdicts above use the registered checker):",
            "",
        ]
        for b in ("gemini", "ollama"):
            if x := rc.get(b):
                lines.append(
                    f"* {b}: {x['calls_with_typographic_sign']} of {x['calls']} replies wrote a "
                    f"typographic minus before a digit; {len(x['verdict_changes'])} verdicts "
                    f"change; {x['accepted_texts_now_rejected']} accepted texts would be rejected"
                )
    if au := r.get("llm_audit"):
        lines += [
            "",
            "Blinded audit of accepted explanations (H7c; the auditor built the tool):",
            "",
        ]
        for b in ("gemini", "ollama"):
            a = au[b]
            if a["audited"]:
                lines.append(f"* {b}: {a['failed']} of {a['audited']} failed "
                             f"(Wilson {_ci(a['failed_wilson'])})")  # fmt: skip
    return [*lines, ""]


def section_requirements(r: dict[str, Any]) -> list[str]:
    lines = [
        "## Validity and performance requirements",
        "",
        "| requirement | measured | pass | evidence |",
        "|---|---|---|---|",
    ]
    if a := r.get("aperiodic"):
        lines += [
            f"| V-01 exponent MAE <= 0.1 | median {a['exponent_median_abs_error']:.4f} (p95 {a['exponent_p95_abs_error']:.4f}), n = {a['n']} | {a['V-01_pass']} | {_link('aperiodic')} |",
            f"| V-02 alpha frequency MAE <= 0.5 Hz | median {a['alpha_freq_median_abs_error_hz']:.3f} Hz ({a['alpha_detected']}/{a['n']} peaks found) | {a['V-02_pass']} | {_link('aperiodic')} |",
            f"| V-03 agreement with specparam | {a['specparam_agree']}/{a['specparam_n']} within 0.1, Wilson {_ci(a['specparam_agree_wilson'])} | {a['V-03_pass']} | {_link('aperiodic')} |",
        ]
    if q := r.get("qc"):
        lines.append(
            f"| V-04 bad channels recall, precision >= 0.95 | recall {q['recall']:.3f} {_ci(q['recall_wilson'])}, precision {q['precision']:.3f} {_ci(q['precision_wilson'])}, {q['n_recordings']} recordings | {q['V-04_pass']} | {_link('qc')} |"
        )
    if p := r.get("resources"):
        lines.append(
            f"| P-01 1 h, 32 ch, 256 Hz: <= 300 s, <= 2048 MB | {p['runtime_s']:.1f} s, {p['peak_rss_mb']:.0f} MB peak RSS, 1 thread ({p['cpu']}) | {p['P-01_pass']} | {_link('resources')} |"
        )
    return [*lines, ""]


def section_detection(r: dict[str, Any]) -> list[str]:
    d = r.get("detection_synthetic")
    if not d:
        return []
    lines = [
        "## Event detection on synthetic evaluation seeds",
        "",
        f"{d['n_recordings']} recordings of 10 minutes (seeds {d['seeds'][0]}-{d['seeds'][1]}, disjoint from the tuning seeds), "
        f"{d['n_true']} injected spike-wave discharges (one recording in five has none), blinks at 15/min, "
        "muscle bursts at 2/min, and normal alpha/spindle bursts at 1/min. "
        f"Overall sensitivity {d['sensitivity']:.3f} (Wilson 95 % {_ci(d['sensitivity_wilson'])}); "
        f"{d['false_detections']} false detections in {d['hours']:.1f} h = {d['false_per_hour']:.2f}/h "
        f"(95 % upper bound {d['false_per_hour_upper95']:.2f}/h); median onset latency {_f(d['onset_latency_median_s'], 1)} s.",
        "",
        "| SNR (dB) | detected | sensitivity | Wilson 95 % |",
        "|---|---|---|---|",
    ]
    for snr, v in d["by_snr_db"].items():
        lines.append(
            f"| {snr} | {v['hits']}/{v['n']} | {v['sensitivity']:.3f} | {_ci(v['wilson'])} |"
        )
    return [*lines, ""]


def _chb_table(m: dict[str, Any], title: str, note: str, name: str) -> list[str]:
    lines = [
        f"## {title}",
        "",
        f"{m['dataset']}. {m['files']} files, {m['hours']:.1f} h, {m['seizures']} expert-marked seizures. {note}",
        "",
        "| file | seizures (s) | detections (onset-offset s, fundamental Hz) | hits | false |",
        "|---|---|---|---|---|",
    ]
    for row in m["rows"]:
        sz = "; ".join(f"{a:.0f}-{b:.0f}" for a, b in row["seizures"]) or "none"
        det = "; ".join(f"{d[0]:.0f}-{d[1]:.0f} ({d[2]:.1f})" for d in row["detections"]) or "none"
        lines.append(f"| {row['file']} | {sz} | {det} | {row['hits']} | {row['false']} |")
    lines += [
        "",
        f"Sensitivity {m['hits']}/{m['seizures']} (Wilson {_ci(m['sensitivity_wilson'])}); "
        f"{m['false_detections']} false detections = {m['false_per_hour']:.2f}/h "
        f"(95 % upper bound {m['false_per_hour_upper95']:.2f}/h); median onset latency "
        f"{_f(m['onset_latency_median_s'], 1)} s. Evidence: {_link(name)}.",
        "",
    ]
    return lines


def section_chbmit(r: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if m := r.get("chbmit_heldout"):
        out += _chb_table(
            m,
            "Real data, held out: CHB-MIT chb03 (H6)",
            "Detector frozen and committed before these files were downloaded; run once.",
            "chbmit_heldout",
        )
    if m := r.get("chbmit"):
        out += _chb_table(
            m,
            "Real data, development: CHB-MIT chb01 (post hoc)",
            "chb01 was H5's test set; after ISSUE-008 it was used for development, so these "
            "numbers are optimistic and not a test.",
            "chbmit",
        )
    if m := r.get("chbmit_h5_registered"):
        out += _chb_table(
            m,
            "Real data, H5 as registered: CHB-MIT chb01 with detector v1",
            "The first and only confirmatory run on chb01 (raw-spectrum rhythm gate).",
            "chbmit_h5_registered",
        )
    return out


def section_checker(r: dict[str, Any]) -> list[str]:
    k = r.get("checker")
    if not k:
        return []
    lines = [
        "## Claim checker mutation testing (H4)",
        "",
        f"{k['n_explanations']} explanations from varied synthetic recordings; four mutants per operator per explanation. "
        f"Equivalent mutants (still true at the written precision, decided from metric values, not by the checker): {k['equivalent_mutants']}. "
        f"Miss-rate 95 % upper bound {k['miss_rate_upper95']:.4f}; false-reject 95 % upper bound {k['false_reject_upper95']:.3f}.",
        "",
        "| operator | mutants | equivalent | live | caught |",
        "|---|---|---|---|---|",
    ]
    for name, v in k["operators"].items():
        lines.append(
            f"| `{name}` | {v['mutants']} | {v['equivalent']} | {v['live']} | {v['caught']} |"
        )
    for name, v in k["blind_spots"].items():
        lines.append(
            f"| `{name}` (known blind spot, out of contract) | {v['applied']} | n/a | {v['applied']} | {v['caught']} |"
        )
    return [*lines, ""]


def section_mutation(r: dict[str, Any]) -> list[str]:
    m = r.get("mutation")
    if not m:
        return []
    lines = [
        "## Test-suite mutation testing",
        "",
        f"{m['killed']}/{m['mutants']} code mutants killed by the tests. Survived: {', '.join(m['survived']) or 'none'}. "
        f"Not applied: {', '.join(m['not_applied']) or 'none'}.",
        "",
        "| mutant | file | status |",
        "|---|---|---|",
    ]
    lines += [f"| `{x['id']}` | `{x.get('file', '')}` | {x['status']} |" for x in m["rows"]]
    return [*lines, ""]


def section_tuning(r: dict[str, Any]) -> list[str]:
    t = r.get("detector_tuning")
    if not t:
        return []
    s = t["selected"]
    extra = (
        f", rhythm gate {s['rhythm_hz'][0]:g}-{s['rhythm_hz'][1]:g} Hz, merge gap {s['merge_gap_s']:g} s"
        if "rhythm_hz" in s
        else ""
    )
    return [
        "## Detector tuning (synthetic seeds only)",
        "",
        f"Seeds {t['seeds'][0]}-{t['seeds'][1]}; {len(t['grid'])} settings. Selected z = {s['z_threshold']}, "
        f"channel fraction = {s['channel_fraction']}, minimum duration = {s['min_duration_s']} s{extra}: "
        f"sensitivity {s['sensitivity']:.3f}, {s['false_per_hour']:.2f} false/h on the tuning set. {_link('detector_tuning')}",
        "",
    ]


def manifest() -> list[str]:
    lines = []
    for p in sorted(RESULTS.glob("*.json")):
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
    (RESULTS / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", newline="\n")
    return [
        "## Manifest",
        "",
        "SHA-256 of every result file (`results/validation/MANIFEST.sha256`):",
        "",
        "```",
        *lines,
        "```",
        "",
    ]


def main() -> None:
    names = ["aperiodic", "h1_confound", "qc", "detection_synthetic", "connectivity", "checker",
             "chbmit_h5_registered", "chbmit", "chbmit_heldout", "resources",
             "detector_tuning", "mutation", "llm_eval_gemini", "llm_eval_ollama",
             "llm_audit", "llm_recheck"]  # fmt: skip
    r = {n: d for n in names if (d := _load(n)) is not None}
    commits = sorted({str(d["provenance"]["git"]["commit"])[:10] for d in r.values()})
    dirty = any(d["provenance"]["git"]["dirty"] for d in r.values())
    out = [
        "# Validation report",
        "",
        "Generated by `validation/report.py` from the result files in `results/validation/`; "
        "do not edit by hand. Hypotheses and thresholds: [PROBLEM_STATEMENT.md](PROBLEM_STATEMENT.md) §4. "
        "What these results changed: [FINDINGS.md](FINDINGS.md).",
        "",
        f"Result files produced at commit(s) {', '.join(commits)}{' (working tree dirty)' if dirty else ''}.",
        "",
        *section_hypotheses(r),
        *section_requirements(r),
        *section_detection(r),
        *section_chbmit(r),
        *section_checker(r),
        *section_llm(r),
        *section_tuning(r),
        *section_mutation(r),
        *manifest(),
    ]
    OUT.write_text("\n".join(out), newline="\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
