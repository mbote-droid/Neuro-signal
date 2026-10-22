"""F-14, F-15, F-16, V-08, S-03, S-04: explanations and the claim checker."""

from __future__ import annotations

import copy
import json
import random
from types import SimpleNamespace

import pytest

from neurosignal.explain import template
from neurosignal.explain.checker import check
from neurosignal.explain.llm import AnthropicBackend, explain_llm, metrics_for_model
from validation.mutants import BLIND_SPOTS, OPERATORS


def test_template_explanation_passes_the_checker(metrics):
    """F-14: every number written by the template is cited and correct."""
    text = template.explain(metrics)
    result = check(text, metrics)
    assert result.ok, result.findings
    assert result.n_citations >= 20
    assert result.n_numbers >= 15


@pytest.mark.parametrize("name", sorted(OPERATORS))
def test_every_mutation_operator_is_caught(metrics, name):
    """F-16, V-08: each realistic error is rejected (equivalent mutants excepted)."""
    text = template.explain(metrics)
    caught = applied = 0
    for seed in range(15):
        m = OPERATORS[name](text, metrics, random.Random(seed))
        if m is None or m.equivalent:
            continue
        applied += 1
        caught += not check(m.text, metrics).ok
    assert applied > 0
    assert caught == applied


def test_blind_spot_documented_not_hidden(metrics):
    """Numbers written as words are outside the contract: the checker passes them.
    This test pins the known limitation so a future fix is noticed."""
    text = template.explain(metrics)
    m = BLIND_SPOTS["number_as_words"](text, metrics, random.Random(0))
    assert m is not None and check(m.text, metrics).ok


def test_template_wording_edge_cases(metrics):
    """Singular counts, no bad channels, no events and a negative zero still read
    correctly and pass the checker."""
    m = copy.deepcopy(metrics)
    m["qc"].update(n_bad=0, bad_channels=[])
    m["events"].update(n_events=0, list=[], total_duration_s=0.0)
    m["connectivity"]["dwpli_mean"] = -0.0001
    text = template.explain(m)
    assert check(text, m).ok, check(text, m).findings
    assert "found no bad channels" in text
    assert "not evidence that none occurred" in text
    assert "-0.000" not in text

    m["qc"].update(n_bad=1, bad_channels=["Fz"])
    text = template.explain(m)
    assert check(text, m).ok, check(text, m).findings
    assert "1 [[qc.n_bad]] channel as bad" in text
    assert "it is excluded" in text


def test_specific_codes(metrics):
    base = template.explain(metrics)
    assert "UNKNOWN_KEY" in check(base + " 3 [[no.such.key]]", metrics).codes()
    assert "UNCITED_NUMBER" in check(base + " There were 12 spikes.", metrics).codes()
    assert "DIAGNOSTIC" in check(base + " This suggests epilepsy.", metrics).codes()
    assert "UNKNOWN_CHANNEL" in check(base + " Look at T9.", metrics).codes()
    assert "NO_DISCLAIMER" in check(base.replace("Research use only.", ""), metrics).codes()
    wrong = base.replace("[[recording.n_channels]]", "[[qc.n_bad]]", 1)
    assert "VALUE_MISMATCH" in check(wrong, metrics).codes()


def test_precision_rule():
    m = {"recording": {"channels": []}, "x": 1.234567}
    ok = "research use only. Value 1.23 [[x]], also 1.2 [[x]] and 1 [[x]]."
    tie = {"recording": {"channels": []}, "y": 0.5}
    assert not check("research use only. Half is 1 [[y]].", tie).ok
    assert check("research use only. Half is 0.5 [[y]].", tie).ok
    assert check(ok, m).ok
    assert "VALUE_MISMATCH" in check("research use only. Value 1.24 [[x]].", m).codes()
    assert "VALUE_MISMATCH" in check("research use only. Value 1.2345 [[x]].", m).codes()


def test_seizure_like_allowed_seizure_not():
    m = {"recording": {"channels": []}}
    assert check("research use only. Seizure-like events are candidates.", m).ok
    assert not check("research use only. A seizure occurred.", m).ok


# ---- LLM explainer with a fake client (no network, no key) -----------------


class FakeMessages:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.replies.pop(0)
        block = SimpleNamespace(type="text", text=text)
        return SimpleNamespace(content=[block], stop_reason="end_turn")


class FakeClient:
    def __init__(self, replies):
        self.beta = SimpleNamespace(messages=FakeMessages(replies))


def test_llm_accepted_when_checker_passes(metrics):
    """F-15."""
    good = template.explain(metrics)
    client = FakeClient([good])
    out = explain_llm(metrics, AnthropicBackend(client=client))
    assert out.check.ok and out.attempts == 1


def test_llm_gets_one_repair_round(metrics):
    good = template.explain(metrics)
    client = FakeClient([good + " This is epilepsy.", good])
    out = explain_llm(metrics, AnthropicBackend(client=client))
    assert out.check.ok and out.attempts == 2
    repair = client.beta.messages.calls[1]["messages"][-1]["content"]
    assert "DIAGNOSTIC" in repair


def test_llm_rejected_twice_is_reported(metrics):
    bad = "research use only. 99 [[recording.n_channels]]"
    out = explain_llm(metrics, AnthropicBackend(client=FakeClient([bad, bad])))
    assert not out.check.ok


def test_model_sees_metrics_only(metrics, analysis):
    """S-03: no provenance, processing log, subject id or raw samples."""
    client = FakeClient([template.explain(metrics)])
    explain_llm(metrics, AnthropicBackend(client=client))
    sent = json.dumps(client.beta.messages.calls[0]["messages"], default=str)
    payload = metrics_for_model(metrics)
    assert "provenance" not in payload and "processing" not in payload
    assert metrics["recording"]["subject_id"] not in sent
    assert str(round(float(analysis.raw.data[0, 100]), 6)) not in sent


def test_api_key_never_written(tmp_path, monkeypatch, synth_pair):
    """S-04: with a key in the environment, no output file contains it."""
    from neurosignal.io.readers import write_npz
    from neurosignal.report import build

    secret = "sk-ant-test-SECRET-should-never-appear"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)

    def fake_llm(m, backend=None, max_attempts=2):
        return explain_llm(m, AnthropicBackend(client=FakeClient([template.explain(m)])))

    monkeypatch.setattr("neurosignal.explain.llm.explain_llm", fake_llm)
    rec, _ = synth_pair
    src = tmp_path / "in.npz"
    write_npz(rec, src)
    res = build.build_report(src, tmp_path / "out", explainer="llm")
    assert res.check.ok
    for f in (tmp_path / "out").rglob("*"):
        if f.is_file():
            assert secret.encode() not in f.read_bytes()


# ---- signs and number forms (BUILD_JOURNAL ISSUE-012, issue #21) --------------


SIGN_METRICS = {"recording": {"channels": []}, "x": {"pos": 0.30, "neg": -3, "a": 8, "b": 12,
                                                   "small": 0.0012}}  # fmt: skip


@pytest.mark.parametrize("dash", ["-", "−", "–", "‒", "﹣", "－"])
def test_a_sign_flip_is_caught_whatever_dash_writes_it(dash):
    text = f"research use only. The change was {dash}0.30 [[x.pos]]."
    assert check(text, SIGN_METRICS).codes() == {"VALUE_MISMATCH"}


@pytest.mark.parametrize("dash", ["-", "−", "–"])
def test_a_true_negative_value_passes_with_any_dash(dash):
    assert check(f"research use only. It was {dash}3 [[x.neg]].", SIGN_METRICS).ok


@pytest.mark.parametrize("sep", ["–", "-", " – ", " to "])
def test_a_range_dash_after_a_citation_is_not_a_sign(sep):
    text = f"research use only. The band was 8 [[x.a]]{sep}12 [[x.b]] Hz."
    assert check(text, SIGN_METRICS).ok


def test_scientific_notation_is_one_number():
    assert check("research use only. Ratio 1.2e-3 [[x.small]].", SIGN_METRICS).ok
    assert check("research use only. Ratio 1.2e−3 [[x.small]].", SIGN_METRICS).ok
    wrong = check("research use only. Ratio 1.3e-3 [[x.small]].", SIGN_METRICS)
    assert wrong.codes() == {"VALUE_MISMATCH"}


def test_no_unicode_normalisation_invents_numbers():
    """NFKC would turn the superscript in µV² into a digit; the checker must not."""
    assert check("research use only. Power in µV² was 0.30 [[x.pos]].", SIGN_METRICS).ok
