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


def test_resume_with_another_model_is_refused(harness):
    _tmp, backend = harness
    backend.outage_seed = 101
    args = Namespace(backend="ollama", model="fake-1", pace=None)
    assert llm_eval.cmd_run(args) == 1  # seed 100 saved, then an outage
    backend.calls.clear()
    wrong = Namespace(backend="ollama", model="gemini-3.8-flash", pace=None)
    assert llm_eval.cmd_run(wrong) == 2
    assert backend.calls == []  # refused before any replay or call


def test_run_stops_at_the_first_outage(harness):
    _tmp, backend = harness
    backend.outage_seed = 100
    assert llm_eval.cmd_run(Namespace(backend="gemini", model="fake-1", pace=None)) == 1
    assert backend.calls == [100]  # no attempt on the later recordings


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
    assert llm_eval.cmd_audit_guide(Namespace()) == 0
    guide = (tmp / "llm_eval" / "audit_guide.md").read_text("utf-8")
    assert "see docs/ICD.md" not in guide  # every cited metric has a note
    assert "`recording.n_channels` = " in guide
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


def test_registered_checker_is_a_frozen_copy():
    """H7's primary verdicts use the checker as registered (ISSUE-012)."""
    import hashlib
    from pathlib import Path

    from validation import h7_registered_checker as registered

    lines = Path(registered.__file__).read_text("utf-8").splitlines(keepends=True)
    body = "".join(lines[next(i for i, x in enumerate(lines) if not x.startswith("#")) :])
    assert hashlib.sha256(body.encode()).hexdigest() == (
        "cedae866bf1e06eec8ab9459d4526598aef17d7c4afe073c025de6df15f189b4"
    )
    flip = "research use only. 0.30 [[x.p]] then −0.30 [[x.p]]"
    metrics = {"recording": {"channels": []}, "x": {"p": 0.30}}
    assert registered.check(flip, metrics).ok  # the registered bug, kept on record


def test_run_uses_registered_checker_and_recheck_flags_the_difference(harness, monkeypatch):
    tmp, backend = harness
    backend.outage_seed = None
    real_chat = backend.chat

    def chat(system, messages):
        reply = real_chat(system, messages)
        if backend.current_seed == 100:  # a sign flip with a typographic minus
            text = reply.text.replace("lasts ", "lasts −", 1)
            return Reply(text, text, reply.model)
        return reply

    monkeypatch.setattr(backend, "chat", chat)
    assert llm_eval.cmd_run(Namespace(backend="gemini", model="fake-1", pace=None)) == 0
    out = json.loads((tmp / "llm_eval_gemini.json").read_text())
    assert out["accepted_first_attempt"] == 2  # 100 accepted as registered; 101 needs repair
    assert llm_eval.cmd_recheck(Namespace()) == 0
    re_ = json.loads((tmp / "llm_recheck.json").read_text())["gemini"]
    assert re_["calls_with_typographic_sign"] == 1
    assert re_["accepted_texts_now_rejected"] == 1
    assert re_["verdict_changes"][0]["corrected_codes"] == ["VALUE_MISMATCH"]


def test_calls_checksum_ignores_windows_line_endings(tmp_path):
    lf, crlf = tmp_path / "lf.jsonl", tmp_path / "crlf.jsonl"
    lf.write_bytes(b'{"a": 1}\n{"b": 2}\n')
    crlf.write_bytes(b'{"a": 1}\r\n{"b": 2}\r\n')
    assert llm_eval.lf_sha256(lf) == llm_eval.lf_sha256(crlf)
