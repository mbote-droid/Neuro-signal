"""One call from file to report: read -> analyse -> metrics -> explain -> check -> render."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neurosignal.core.config import PipelineConfig
from neurosignal.explain import template
from neurosignal.explain.checker import CheckResult, check
from neurosignal.io.readers import DEFAULT_MAX_BYTES, read
from neurosignal.pipeline import analyse, build_metrics
from neurosignal.report import render


@dataclass(frozen=True)
class ReportResult:
    outdir: Path
    metrics: dict[str, Any]
    explanation: str
    check: CheckResult
    source: str


def explain(
    metrics: dict[str, Any], explainer: str, model: str | None = None
) -> tuple[str, CheckResult, str]:
    """Returns (text, check result, source label). Falls back to the template
    when the backend is unavailable or its text fails the claim checker."""
    if explainer != "template":
        from neurosignal.explain.llm import BackendError, explain_llm, get_backend

        try:
            llm = explain_llm(metrics, get_backend(explainer, model))
        except BackendError as e:
            text = template.explain(metrics)
            return text, check(text, metrics), f"template ({explainer}: {e})"
        if llm.check.ok:
            return llm.text, llm.check, f"{llm.model}, accepted after {llm.attempts} attempt(s)"
        text = template.explain(metrics)
        return text, check(text, metrics), f"template ({llm.model} rejected by the claim checker)"
    text = template.explain(metrics)
    return text, check(text, metrics), "deterministic template"


def build_report(
    path: Path,
    outdir: Path,
    cfg: PipelineConfig | None = None,
    explainer: str = "template",
    max_bytes: int = DEFAULT_MAX_BYTES,
    model: str | None = None,
) -> ReportResult:
    t0 = time.perf_counter()
    rec = read(path, max_bytes=max_bytes)
    an = analyse(rec, cfg)
    metrics = build_metrics(an)
    t1 = time.perf_counter()
    outdir.mkdir(parents=True, exist_ok=True)
    render.write_metrics(metrics, outdir / "metrics.json")
    text, result, source = explain(metrics, explainer, model)
    (outdir / "explanation.md").write_text(text, encoding="utf-8")
    figs = render.make_figures(an, outdir)
    render.write_markdown(metrics, text, result, source, outdir / "report.md")
    render.write_html(metrics, text, result, source, figs, outdir / "report.html")
    run = {
        "analysis_s": round(t1 - t0, 3),
        "total_s": round(time.perf_counter() - t0, 3),
        "explanation_source": source,
        "claim_check_ok": result.ok,
    }
    (outdir / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return ReportResult(outdir, metrics, text, result, source)
