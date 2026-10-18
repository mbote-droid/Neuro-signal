"""H7: how real language models behave under the citation contract.

Pre-registered in PROBLEM_STATEMENT §10. Runs on the author's machine (the
models need a Gemini API key or a local Ollama server):

    $env:GEMINI_API_KEY = "..."                       # PowerShell; never committed
    uv run python validation/llm_eval.py run --backend gemini --model <free-tier model>
    uv run python validation/llm_eval.py run --backend ollama --model <3-4B model>
    uv run python validation/llm_eval.py audit-sheet  # blinded sheet for H7c
    #   ... fill results/validation/llm_eval/audit.csv ...
    uv run python validation/llm_eval.py audit-score

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
from neurosignal.explain.checker import CITATION
from neurosignal.explain.llm import BackendError, ChatBackend, Reply, explain_llm, get_backend
from validation.common import RESULTS, explanation_metrics, write_result

H7_SEEDS = range(100, 130)
AUDIT_SAMPLE = 20
AUDIT_SEED = 7
DIR = RESULTS / "llm_eval"
PACE_S = {"gemini": 5.0, "ollama": 0.0}  # stay inside the free tier's requests per minute


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
        with self.cache.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return reply


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
    inner = get_backend(a.backend, a.model)
    pace = PACE_S[a.backend] if a.pace is None else a.pace
    cases, failed = [], []
    for seed in H7_SEEDS:
        metrics = explanation_metrics(seed)
        backend = RecordingBackend(inner, cache, seed, pace)
        try:
            out = explain_llm(metrics, backend)
        except BackendError as e:
            failed.append(seed)
            print(f"seed {seed}: {e} (will be retried on the next run)")
            continue
        cases.append({
            "seed": seed, "model": out.model, "attempts": out.attempts,
            "accepted_first": not out.trace[0].codes, "accepted": out.check.ok,
            "codes": [list(t.codes) for t in out.trace],
        })  # fmt: skip
        print(f"seed {seed}: {'accepted' if out.check.ok else 'REJECTED'} "
              f"after {out.attempts} attempt(s)")  # fmt: skip
    if failed:
        print(f"{len(failed)} recording(s) incomplete; run the same command again to resume.")
        return 1
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
        "calls_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
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
        cited = sorted({m.group(1) for m in CITATION.finditer(text)})
        rows = [f"| `{k}` | {json.dumps(_lookup(metrics, k))} |" for k in cited]
        md += [f"## {item_id}", "", text.strip(), "", "| cited key | value |", "|---|---|",
               *rows, ""]  # fmt: skip
    (DIR / "audit_items.md").write_text("\n".join(md), encoding="utf-8")
    (DIR / "audit_key.json").write_text(json.dumps(key, indent=2) + "\n")
    with (DIR / "audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "fails", "notes"])
        w.writerows([[k, "", ""] for k in key])
    print(f"{len(items)} items: read {DIR / 'audit_items.md'}, fill {DIR / 'audit.csv'}")
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
    sub.add_parser("audit-score", help="score the filled audit.csv").set_defaults(
        func=cmd_audit_score)  # fmt: skip
    a = p.parse_args()
    return int(a.func(a))


if __name__ == "__main__":
    raise SystemExit(main())
