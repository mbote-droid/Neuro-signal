"""H7: how real language models behave under the citation contract.

Pre-registered in PROBLEM_STATEMENT §10. Runs on the author's machine (the
models need a Gemini API key or a local Ollama server):

    $env:GEMINI_API_KEY = "..."                       # PowerShell; never committed
    uv run python validation/llm_eval.py run --backend gemini --model <free-tier model>
    uv run python validation/llm_eval.py run --backend ollama --model <3-4B model>
    uv run python validation/llm_eval.py audit-sheet  # blinded sheet for H7c
    #   ... fill results/validation/llm_eval/audit.csv ...
    uv run python validation/llm_eval.py audit-score
    uv run python validation/llm_eval.py recheck      # corrected checker, secondary

Every model reply is cached in results/validation/llm_eval/<backend>_calls.jsonl
before it is checked, so an interrupted run resumes without repeating a call:
only calls that failed for infrastructure reasons (rate limits, network) are
ever made again.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import statistics
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neurosignal.core.stats import wilson
from neurosignal.explain import llm
from neurosignal.explain.checker import CITATION, check
from neurosignal.explain.llm import BackendError, ChatBackend, Reply, explain_llm, get_backend
from validation import h7_registered_checker as registered
from validation.common import RESULTS, explanation_metrics, write_result

H7_SEEDS = range(100, 130)
AUDIT_SAMPLE = 20
AUDIT_SEED = 7
DIR = RESULTS / "llm_eval"
PACE_S = {"gemini": 13.0, "ollama": 0.0}  # the free tier allows 5 requests per minute


class RecordingBackend:
    """Wraps a backend: replays cached replies, caches new ones before use."""

    def __init__(self, inner: ChatBackend, cache: Path, seed: int, pace_s: float) -> None:
        self.inner, self.cache, self.seed, self.pace_s = inner, cache, seed, pace_s
        self.provider, self.model = inner.provider, inner.model
        self.calls = 0
        self.done = {
            (r["seed"], r["call"]): r
            for r in map(
                json.loads, cache.read_text("utf-8").splitlines() if cache.exists() else []
            )
        }

    def chat(self, system: str, messages: list[dict[str, Any]]) -> Reply:
        key = (self.seed, self.calls)
        self.calls += 1
        if key in self.done:
            r = self.done[key]
            return Reply(r["text"], r["text"], r["model"])
        time.sleep(self.pace_s)
        start = time.perf_counter()
        reply = self.inner.chat(system, messages)
        row = {"seed": key[0], "call": key[1], "model": reply.model, "text": reply.text,
               "seconds": round(time.perf_counter() - start, 2)}  # fmt: skip
        with self.cache.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row) + "\n")
        return reply


def lf_sha256(path: Path) -> str:
    """SHA-256 of a text file with LF line endings, so the checksum is the same
    on Windows (CRLF) and after Git stores the file with LF (.gitattributes)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _ollama_digest(model: str) -> str | None:
    """The local model's content digest, so the exact weights are on record."""
    try:
        host = llm.OllamaBackend(model).host
        with urllib.request.urlopen(f"{host}/api/tags", timeout=10) as r:
            tags = json.loads(r.read())
        return next((m.get("digest") for m in tags.get("models", []) if m.get("name") == model),
                    None)  # fmt: skip
    except (OSError, ValueError):
        return None


def cmd_run(a: argparse.Namespace) -> int:
    DIR.mkdir(parents=True, exist_ok=True)
    cache = DIR / f"{a.backend}_calls.jsonl"
    # a resumed run must use the model the saved replies came from; otherwise
    # replayed and new replies would mix two models in one result
    rows = cache.read_text("utf-8").splitlines() if cache.exists() else []
    saved = {json.loads(x)["model"] for x in rows}
    if other := sorted(m for m in saved if not m.startswith(a.model)):
        print(f"refused: the saved {a.backend} replies come from {', '.join(other)}, "
              f"not {a.model}. Run again with --model {other[0]}.")  # fmt: skip
        return 2
    inner = get_backend(a.backend, a.model)
    pace = PACE_S[a.backend] if a.pace is None else a.pace
    cases = []
    for seed in H7_SEEDS:
        metrics = explanation_metrics(seed)
        backend = RecordingBackend(inner, cache, seed, pace)
        try:
            # primary verdicts use the checker as registered (ISSUE-012)
            out = explain_llm(metrics, backend, checker=registered.check)
        except BackendError as e:
            # quota and outages persist: stop instead of failing every remaining seed
            done = len(cases)
            print(f"seed {seed}: {e}")
            print(f"stopped after {done} of {len(H7_SEEDS)} recordings; every reply so far is "
                  "saved. Run the same command again later (for a daily quota, tomorrow) "
                  "to continue.")  # fmt: skip
            return 1
        cases.append({
            "seed": seed, "model": out.model, "attempts": out.attempts,
            "accepted_first": not out.trace[0].codes, "accepted": out.check.ok,
            "codes": [list(t.codes) for t in out.trace],
        })  # fmt: skip
        print(f"seed {seed}: {'accepted' if out.check.ok else 'REJECTED'} "
              f"after {out.attempts} attempt(s)")  # fmt: skip
    _summarise(a.backend, cases, cache)
    return 0


def _summarise(backend: str, cases: list[dict[str, Any]], cache: Path) -> None:
    calls = [json.loads(x) for x in cache.read_text().splitlines()]
    n = len(cases)
    first = sum(c["accepted_first"] for c in cases)
    final = sum(c["accepted"] for c in cases)
    codes = [Counter(code for c in cases if len(c["codes"]) > i for code in c["codes"][i])
             for i in range(2)]  # fmt: skip
    models = sorted({c["model"] for c in cases})
    payload: dict[str, Any] = {
        "backend": backend,
        "models_reported": models,
        "ollama_digest": _ollama_digest(models[0]) if backend == "ollama" else None,
        "prompt_sha256": hashlib.sha256(llm.SYSTEM_PROMPT.encode()).hexdigest(),
        "seeds": [H7_SEEDS.start, H7_SEEDS.stop - 1],
        "n": n,
        "accepted_first_attempt": first,
        "accepted_first_wilson": wilson(first, n),
        "accepted_after_repair": final,
        "accepted_after_repair_wilson": wilson(final, n),
        "fell_back_to_template": n - final,
        "finding_codes_first_attempt": dict(codes[0]),
        "finding_codes_repair_attempt": dict(codes[1]),
        "seconds_per_call_median": statistics.median(c["seconds"] for c in calls),
        "calls": len(calls),
        "calls_sha256": lf_sha256(cache),
        "cases": cases,
    }
    if backend == "gemini":
        payload["H7a_accepted"] = bool(n == len(H7_SEEDS) and final >= 24)
    path = write_result(f"llm_eval_{backend}", payload)
    print(f"{final}/{n} accepted after at most one repair ({first} on the first attempt); "
          f"wrote {path}")  # fmt: skip


def _final_texts(backend: str) -> dict[int, str]:
    """The accepted text of each seed (the last call made for it)."""
    rows = [json.loads(x) for x in (DIR / f"{backend}_calls.jsonl").read_text().splitlines()]
    last: dict[int, dict[str, Any]] = {}
    for r in rows:
        if r["seed"] not in last or r["call"] > last[r["seed"]]["call"]:
            last[r["seed"]] = r
    return {s: r["text"] for s, r in last.items()}


def _lookup(metrics: Any, key: str) -> Any:
    for part in key.split("."):
        metrics = metrics[int(part)] if isinstance(metrics, list) else metrics[part]
    return metrics


def cmd_audit_sheet(a: argparse.Namespace) -> int:
    rng = random.Random(AUDIT_SEED)
    items = []
    for backend in ("gemini", "ollama"):
        result = json.loads((RESULTS / f"llm_eval_{backend}.json").read_text())
        accepted = sorted(c["seed"] for c in result["cases"] if c["accepted"])
        texts = _final_texts(backend)
        sample = rng.sample(accepted, min(AUDIT_SAMPLE, len(accepted)))
        items += [(backend, seed, texts[seed]) for seed in sample]
    rng.shuffle(items)
    key, md = {}, ["# H7c audit sheet", "",
                   "For each item, read the explanation against the cited values. Mark it as "
                   "failing (1) if it contains at least one statement that is false or misleading "
                   "given the metrics: a citation of the wrong metric for the sentence, a wrong "
                   "interpretation, or an invented qualitative claim. Otherwise 0. Record the "
                   "verdict in audit.csv. Do not open audit_key.json until audit.csv is complete.",
                   ""]  # fmt: skip
    for i, (backend, seed, text) in enumerate(items, 1):
        item_id = f"A{i:02d}"
        key[item_id] = {"backend": backend, "seed": seed}
        metrics = explanation_metrics(seed)
        cited = sorted({m.group(1).strip() for m in CITATION.finditer(text)})
        rows = [f"| `{k}` | {json.dumps(_lookup(metrics, k))} |" for k in cited]
        # the explanation as a quote, so its own headings stay inside the item
        quoted = [f"> {line}" if line else ">" for line in text.strip().splitlines()]
        md += [f"## {item_id}", "", *quoted, "", f"Cited values for {item_id}:", "",
               "| cited key | value |", "|---|---|", *rows, ""]  # fmt: skip
    (DIR / "audit_items.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    (DIR / "audit_key.json").write_text(json.dumps(key, indent=2) + "\n", newline="\n")
    with (DIR / "audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "fails", "notes"])
        w.writerows([[k, "", ""] for k in key])
    print(f"{len(items)} items: read {DIR / 'audit_items.md'}, fill {DIR / 'audit.csv'}")
    return 0


# Plain-words notes for the audit reading guide: what each metric measures and
# what it cannot tell. The same note for every item; no item is judged here.
GLOSSARY: list[tuple[str, str]] = [
    (r"recording\.n_channels", "number of EEG channels in the file."),
    (r"recording\.duration_s", "length of the recording in seconds."),
    (r"recording\.sfreq_hz", "sampling rate: samples per second (Hz)."),
    (
        r"recording\.montage",
        "'referential' = each channel against a reference; "
        "'bipolar' = each channel is the difference of two neighbours.",
    ),
    (r"recording\.channels", "the channel names in the file."),
    (
        r"qc\.n_bad",
        "channels rejected by quality control (flat, noisy or too quiet); "
        "they are left out of everything else.",
    ),
    (r"qc\.n_good", "channels kept after quality control."),
    (r"qc\.bad_channels", "names of the rejected channels."),
    (
        r"qc\.line_noise_reference_band_hz",
        "edges (Hz) of the 1-45 Hz band the line-noise ratio divides by.",
    ),
    (r"config\.line_freq_hz", "mains frequency the notch filter removes (50 Hz in Kenya)."),
    (r"config\.alpha_band_hz", "edges (Hz) of the canonical alpha band used for band power."),
    (r"aperiodic\.poor_fit_channels", "names of the channels with an unreliable fit."),
    (
        r"qc\.flat\.",
        "this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.",
    ),
    (
        r"qc\.noisy\.",
        "this channel's amplitude spread divided by the median channel's; "
        "above 5 marks it noisy (bad). It is a ratio, not microvolts.",
    ),
    (
        r"qc\.line_noise_ratio_before",
        "50 Hz mains power divided by total 1-45 Hz power, "
        "median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.",
    ),
    (r"qc\.line_noise_ratio_after", "the same ratio AFTER the 50 Hz notch filter."),
    (
        r"spectral\.n_segments",
        "number of 2-second windows averaged for the spectrum "
        "(windows inside detected events are left out).",
    ),
    (
        r"spectral\.alpha_band_power",
        "raw power in 8-12 Hz (µV²). It MIXES the alpha "
        "rhythm with the 1/f background, so it is NOT a clean oscillation measure.",
    ),
    (
        r"spectral\.relative_alpha_power",
        "8-12 Hz power as a fraction of all 1-45 Hz power "
        "(0 to 1). Also mixes rhythm and background.",
    ),
    (
        r"aperiodic\.exponent",
        "steepness of the 1/f background slope (typical 1-2). Not an oscillation.",
    ),
    (r"aperiodic\.offset", "overall height (log10 power) of the 1/f background."),
    (
        r"aperiodic\.r_squared",
        "how well the background-plus-peaks model fits the spectrum "
        "(1 = perfect; below 0.8 the channel counts as a poor fit).",
    ),
    (r"aperiodic\.n_poor_fits", "channels whose model fit was unreliable and left out."),
    (
        r"aperiodic\.n_channels_with_alpha",
        "channels where an alpha peak (7-14 Hz) rises above the 1/f background.",
    ),
    (r"aperiodic\.alpha_peak_freq_hz", "frequency (Hz) of the alpha peak."),
    (
        r"aperiodic\.alpha_peak_power",
        "height of the alpha peak ABOVE the 1/f background, "
        "in log10 units: the CLEAN measure of the alpha oscillation.",
    ),
    (
        r"connectivity\.n_epochs",
        "number of 2-second pieces used to estimate coupling; more epochs = more reliable.",
    ),
    (
        r"connectivity\.plv_mean",
        "phase-locking value averaged over channel pairs. "
        "INFLATED by volume conduction: cannot show true connectivity on its own.",
    ),
    (
        r"connectivity\.wpli_mean",
        "plain wPLI averaged over pairs. Ignores zero-lag sync but "
        "is biased UPWARD with few epochs (about 0.15 even with no coupling at 60 epochs).",
    ),
    (
        r"connectivity\.dwpli_mean",
        "debiased wPLI averaged over pairs: the trustworthy "
        "coupling measure. Near 0 (it can be slightly negative) = no real coupling.",
    ),
    (
        r"connectivity\.top_pairs\.\d+\.dwpli",
        "debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.",
    ),
    (r"connectivity\.top_pairs\.\d+\.plv", "PLV of this pair (inflated by volume conduction)."),
    (r"connectivity\.top_pairs\.\d+\.[ab]", "a channel of this pair."),
    (
        r"events\.n_events",
        "number of seizure-like event CANDIDATES the detector found. "
        "Zero means none were found, not that none happened; candidates are not diagnoses.",
    ),
    (r"events\.rate_per_hour", "candidates per hour of recording."),
    (r"events\.total_duration_s", "total seconds covered by candidates."),
    (r"events\.list\.\d+\.onset_s", "when this candidate starts (seconds from the start)."),
    (r"events\.list\.\d+\.offset_s", "when this candidate ends (seconds)."),
    (r"events\.list\.\d+\.duration_s", "how long this candidate lasts (seconds)."),
    (
        r"events\.list\.\d+\.dominant_freq_hz",
        "main rhythm of the candidate (Hz), read "
        "against the background; the detector only keeps 2-7.5 Hz.",
    ),
    (r"events\.list\.\d+\.n_channels", "channels where the candidate was seen."),
    (r"events\.list\.\d+\.channels", "names of those channels."),
    (
        r"events\.list\.\d+\.peak_z",
        "how far line length rose above the channel's usual "
        "level (robust z-score); higher = more pronounced, not more dangerous.",
    ),
]


def _note(key: str) -> str:
    stem = re.sub(r"\.(mean|min|max)$", "", key)
    for pattern, note in GLOSSARY:
        if re.match(pattern, stem):
            suffix = {"mean": " (average over channels)", "min": " (lowest channel)",
                      "max": " (highest channel)"}.get(key.rsplit(".", 1)[-1], "")  # fmt: skip
            return note + suffix
    return "see docs/ICD.md for this metric."


def cmd_audit_guide(a: argparse.Namespace) -> int:
    """A reading copy of the audit sheet: every sentence with a cited number is
    followed by what each cited metric measures. Explains; judges nothing."""
    key = json.loads((DIR / "audit_key.json").read_text())
    texts = {b: _final_texts(b) for b in {v["backend"] for v in key.values()}}
    md = ["# H7c audit: reading guide", "",
          "The same items as audit_items.md, in the same order. Under each sentence that "
          "cites a number: the cited value and what that metric measures. The notes are "
          "identical for every item and say nothing about whether a sentence is right; the "
          "verdicts (0 or 1 in audit.csv) are yours.", ""]  # fmt: skip
    for item_id, v in key.items():
        metrics = explanation_metrics(v["seed"])
        md += [f"## {item_id}", ""]
        for line in texts[v["backend"]][v["seed"]].strip().splitlines():
            if not line.strip():
                continue
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z#*])", line):
                md.append(f"> {sentence}")
                cited = list(dict.fromkeys(m.group(1).strip() for m in CITATION.finditer(sentence)))
                for k in cited:
                    try:
                        value = json.dumps(_lookup(metrics, k))
                    except (KeyError, IndexError, ValueError):
                        value = "(not in the metrics)"
                    md.append(f"- `{k}` = {value}: {_note(k)}")
                md.append("")
    (DIR / "audit_guide.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"wrote {DIR / 'audit_guide.md'}")
    return 0


def cmd_audit_score(a: argparse.Namespace) -> int:
    key = json.loads((DIR / "audit_key.json").read_text())
    # utf-8-sig: Excel adds a byte-order mark when it saves a CSV
    with (DIR / "audit.csv").open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if any(r["fails"].strip() not in {"0", "1"} for r in rows) or len(rows) != len(key):
        print("audit.csv is incomplete: every item needs fails = 0 or 1")
        return 1
    payload: dict[str, Any] = {"sample_seed": AUDIT_SEED, "auditor_independent": False}
    for backend in ("gemini", "ollama"):
        mine = [r for r in rows if key[r["id"]]["backend"] == backend]
        fails = sum(r["fails"].strip() == "1" for r in mine)
        payload[backend] = {
            "audited": len(mine), "failed": fails,
            "failed_wilson": wilson(fails, len(mine)) if mine else None,
            "notes": {r["id"]: r["notes"] for r in mine if r["notes"].strip()},
        }  # fmt: skip
    g = payload["gemini"]
    payload["H7c_accepted"] = bool(g["audited"] > 0 and g["failed"] <= 2 * g["audited"] / 20)
    path = write_result("llm_audit", payload)
    print(f"wrote {path}")
    return 0


TYPOGRAPHIC_SIGN = re.compile("[\u2010\u2011\u2012\u2013\u2212\ufe63\uff0d](?=\\d)")


def cmd_recheck(a: argparse.Namespace) -> int:
    """Secondary analysis (ISSUE-012): every saved reply, judged by the registered
    checker and by the corrected one. No model is called."""
    payload: dict[str, Any] = {"registered_checker": "validation/h7_registered_checker.py"}
    for backend in ("gemini", "ollama"):
        cache = DIR / f"{backend}_calls.jsonl"
        if not cache.exists():
            continue
        rows = [json.loads(x) for x in cache.read_text("utf-8").splitlines()]
        final = _final_texts(backend)
        changes = []
        for r in rows:
            metrics = explanation_metrics(r["seed"])
            before, after = registered.check(r["text"], metrics), check(r["text"], metrics)
            if before.ok != after.ok:
                changes.append({"seed": r["seed"], "call": r["call"], "registered_ok": before.ok,
                                "corrected_ok": after.ok,
                                "corrected_codes": sorted(after.codes())})  # fmt: skip
        payload[backend] = {
            "calls": len(rows),
            "calls_with_typographic_sign": sum(bool(TYPOGRAPHIC_SIGN.search(r["text"])) for r in rows),
            "verdict_changes": changes,
            "accepted_texts_now_rejected": sum(
                1 for c in changes
                if c["registered_ok"] and final.get(c["seed"]) is not None
                and c["call"] == max(r["call"] for r in rows if r["seed"] == c["seed"])
            ),
        }  # fmt: skip
    path = write_result("llm_recheck", payload)
    print(f"wrote {path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="explain the 30 H7 recordings with one model")
    r.add_argument("--backend", choices=["gemini", "ollama"], required=True)
    r.add_argument("--model", required=True, help="exact model name, recorded in the results")
    r.add_argument("--pace", type=float, help="seconds between calls (default per backend)")
    r.set_defaults(func=cmd_run)
    sub.add_parser("audit-sheet", help="blinded sheet of accepted texts").set_defaults(
        func=cmd_audit_sheet)  # fmt: skip
    sub.add_parser("audit-guide", help="reading guide for the audit sheet").set_defaults(
        func=cmd_audit_guide)  # fmt: skip
    sub.add_parser("audit-score", help="score the filled audit.csv").set_defaults(
        func=cmd_audit_score)  # fmt: skip
    sub.add_parser("recheck", help="saved replies under the corrected checker").set_defaults(
        func=cmd_recheck)  # fmt: skip
    a = p.parse_args()
    return int(a.func(a))


if __name__ == "__main__":
    raise SystemExit(main())
