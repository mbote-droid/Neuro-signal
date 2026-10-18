"""H7 harness: resume without repeating calls, summary, blinded audit (fake model)."""

from __future__ import annotations

import csv
import json
from argparse import Namespace

import pytest

from neurosignal.explain import template
from neurosignal.explain.llm import BackendError, Reply
from validation import common, llm_eval


class ScriptedBackend:
    """Good text for most seeds, one rejected-then-repaired seed, one outage."""

    provider, model = "fake", "fake-1"

    def __init__(self, metrics_of, outage_seed=None):
        self.metrics_of, self.outage_seed, self.calls = metrics_of, outage_seed, []

    def chat(self, system, messages):
        seed = self.current_seed
        self.calls.append(seed)
        if seed == self.outage_seed:
            raise BackendError("HTTP 429 (quota)")
        good = template.explain(self.metrics_of(seed))
        first_call = len(messages) == 1
        text = good + " There were 12 spikes." if seed == 101 and first_call else good
        return Reply(text, text, "fake-1.0")


@pytest.fixture
def harness(tmp_path, monkeypatch):
    metrics = {s: common.explanation_metrics(s) for s in (100, 101, 102)}
    monkeypatch.setattr(llm_eval, "H7_SEEDS", range(100, 103))
    monkeypatch.setattr(llm_eval, "DIR", tmp_path / "llm_eval")
    monkeypatch.setattr(llm_eval, "RESULTS", tmp_path)
    monkeypatch.setattr(common, "RESULTS", tmp_path)
    monkeypatch.setattr(llm_eval, "explanation_metrics", metrics.__getitem__)
    monkeypatch.setattr(llm_eval, "PACE_S", {"gemini": 0.0, "ollama": 0.0})
    backend = ScriptedBackend(metrics.__getitem__, outage_seed=102)
    monkeypatch.setattr(llm_eval, "get_backend", lambda name, model: backend)
    real_init = llm_eval.RecordingBackend.__init__

    def init(self, inner, cache, seed, pace_s):
        real_init(self, inner, cache, seed, pace_s)
        inner.current_seed = seed

    monkeypatch.setattr(llm_eval.RecordingBackend, "__init__", init)
    return tmp_path, backend


def test_run_resumes_without_repeating_calls(harness):
    tmp, backend = harness
    args = Namespace(backend="gemini", model="fake-1", pace=None)
    assert llm_eval.cmd_run(args) == 1  # seed 102 hit an outage: incomplete
    assert not (tmp / "llm_eval_gemini.json").exists()
    backend.outage_seed = None
    backend.calls.clear()
    assert llm_eval.cmd_run(args) == 0
    assert backend.calls == [102]  # only the failed call was made again
    out = json.loads((tmp / "llm_eval_gemini.json").read_text())
    assert out["n"] == 3 and out["accepted_after_repair"] == 3
    assert out["accepted_first_attempt"] == 2
    assert out["finding_codes_first_attempt"] == {"UNCITED_NUMBER": 1}
    assert out["H7a_accepted"] is False  # 3 recordings, not the registered 30
    assert out["models_reported"] == ["fake-1.0"]


def test_audit_is_blinded_and_scored(harness, monkeypatch):
    tmp, backend = harness
    backend.outage_seed = None
    for name in ("gemini", "ollama"):
        assert llm_eval.cmd_run(Namespace(backend=name, model="fake-1", pace=None)) == 0
        assert (tmp / "llm_eval" / f"{name}_calls.jsonl").exists()
    assert llm_eval.cmd_audit_sheet(Namespace()) == 0
    items = (tmp / "llm_eval" / "audit_items.md").read_text()
    assert "gemini" not in items and "ollama" not in items  # model hidden
    assert "| `recording.n_channels` |" in items
    path = tmp / "llm_eval" / "audit.csv"
    rows = list(csv.DictReader(path.open()))
    assert len(rows) == 6
    assert llm_eval.cmd_audit_score(Namespace()) == 1  # not filled in yet
    for r in rows:
        r["fails"] = "0"
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # as Excel saves it
        w = csv.DictWriter(f, fieldnames=["id", "fails", "notes"])
        w.writeheader()
        w.writerows(rows)
    assert llm_eval.cmd_audit_score(Namespace()) == 0
    score = json.loads((tmp / "llm_audit.json").read_text())
    assert score["gemini"]["audited"] == 3 and score["H7c_accepted"] is True
