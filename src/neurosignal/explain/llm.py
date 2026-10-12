"""Optional LLM explainer (F-15, ADR-009).

The model receives only the metrics dictionary (S-03): no signal, no header
fields, no provenance. Its text is untrusted until `checker.check` accepts
it. If the first draft fails, the checker's findings are sent back once for
a repair; if that also fails, the caller falls back to the deterministic
explainer. The API key is resolved by the SDK from the environment and is
never read, logged or written here (S-04).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from neurosignal.explain.checker import CheckResult, check

MODEL = "claude-opus-5-5"
MAX_TOKENS = 8000

SYSTEM_PROMPT = """You write short, plain-language summaries of EEG analysis results for
researchers.

You receive a JSON object of metrics computed by a validated pipeline. Write a summary of
about 250-400 words in Markdown with the sections Summary, Recording, Quality, Spectrum,
Coupling and Events.

Rules, all checked mechanically; a summary that breaks any of them is rejected:
1. Every number you write must be followed immediately by a citation of the metric it comes
   from, as [[dotted.key]], for example "the mean exponent was 1.23 [[aperiodic.exponent.mean]]".
   Keys are dotted paths into the JSON; list items use their index, e.g.
   [[events.list.0.onset_s]]. Round as you like, but the rounded number must match the metric.
2. Do not write any number that is not in the metrics, including band limits, counts or
   ranges, unless you cite it. Write counts as digits with a citation, never as words.
3. Only name channels that appear in recording.channels.
4. This is research software. Include the exact phrase "research use only". Make no
   clinical or diagnostic statements: do not use words such as epilepsy, seizure (use
   "seizure-like event"), diagnosis, abnormal, normal EEG, pathology, disorder or disease.
5. Explain what the numbers mean: that band power mixes oscillations with the aperiodic
   background (peak power above the aperiodic fit is the oscillation measure), and that
   PLV is inflated by volume conduction while debiased wPLI is not.
"""


class MessagesClient(Protocol):
    """The slice of `anthropic.Anthropic` this module uses (for test doubles)."""

    @property
    def beta(self) -> Any: ...


@dataclass(frozen=True)
class LLMExplanation:
    text: str
    check: CheckResult
    attempts: int
    model: str


def metrics_for_model(metrics: dict[str, Any]) -> dict[str, Any]:
    """Only computed results go to the model: no provenance, processing log or ids."""
    out = {k: v for k, v in metrics.items() if k not in {"provenance", "processing"}}
    out["recording"] = {k: v for k, v in metrics["recording"].items() if k != "subject_id"}
    return out


def _text(response: Any) -> str:
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("the model declined to write a summary")
    return "".join(b.text for b in response.content if getattr(b, "type", "") == "text")


def explain_llm(
    metrics: dict[str, Any], client: MessagesClient | None = None, max_attempts: int = 2
) -> LLMExplanation:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    payload = json.dumps(metrics_for_model(metrics), sort_keys=True)
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"Metrics JSON:\n```json\n{payload}\n```"}
    ]
    result: CheckResult | None = None
    text = ""
    for attempt in range(1, max_attempts + 1):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        text = _text(response)
        result = check(text, metrics)
        if result.ok:
            return LLMExplanation(text, result, attempt, MODEL)
        problems = "\n".join(f"- {f.code}: {f.detail}" for f in result.findings[:30])
        messages += [
            # the full content (thinking blocks included) is echoed back unchanged
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": "The checker rejected the summary:\n"
                f"{problems}\nRewrite the whole summary so that it passes every rule.",
            },
        ]
    assert result is not None
    return LLMExplanation(text, result, max_attempts, MODEL)
