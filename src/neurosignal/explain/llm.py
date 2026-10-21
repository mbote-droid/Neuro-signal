"""Optional LLM explainer (F-15, ADR-009, ADR-013).

The model receives only the metrics dictionary (S-03): no signal, no header
fields, no provenance. Its text is untrusted until `checker.check` accepts
it. If the first draft fails, the checker's findings are sent back once for
a repair; if that also fails, the caller falls back to the deterministic
explainer.

Three backends share the same prompt, contract and repair loop: Anthropic
(SDK, optional extra `llm`), Google Gemini and a local Ollama server (both
over plain HTTPS/HTTP, no extra dependency). API keys are read from the
environment only, sent in request headers, and never logged or written
(S-04).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from neurosignal.explain.checker import CheckResult, check

MODEL = "claude-opus-5-5"
MAX_TOKENS = 8000
DEFAULT_MODELS = {"anthropic": MODEL, "gemini": "gemini-3.8-flash", "ollama": "qwen2.5:3b"}
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta"
OLLAMA_HOST = "http://localhost:11434"
RETRY_STATUS = {429, 500, 502, 503, 504}

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


class BackendError(RuntimeError):
    """A backend could not be used (no credentials, unreachable, refused)."""


@dataclass(frozen=True)
class Reply:
    text: str
    raw: Any  # what goes back into the conversation as the assistant turn
    model: str  # the model identifier the API reports


class ChatBackend(Protocol):
    provider: str
    model: str

    def chat(self, system: str, messages: list[dict[str, Any]]) -> Reply: ...


@dataclass(frozen=True)
class Attempt:
    text: str
    codes: tuple[str, ...]
    seconds: float


@dataclass(frozen=True)
class LLMExplanation:
    text: str
    check: CheckResult
    attempts: int
    model: str
    trace: tuple[Attempt, ...] = field(default=())


def metrics_for_model(metrics: dict[str, Any]) -> dict[str, Any]:
    """Only computed results go to the model: no provenance, processing log or ids."""
    out = {k: v for k, v in metrics.items() if k not in {"provenance", "processing"}}
    out["recording"] = {k: v for k, v in metrics["recording"].items() if k != "subject_id"}
    return out


# ---- backends -----------------------------------------------------------------


class AnthropicBackend:
    provider = "anthropic"

    def __init__(self, model: str | None = None, client: Any = None) -> None:
        if client is None and not (
            os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        ):
            raise BackendError("no API credentials found")
        self.model = model or MODEL
        self._client = client

    def chat(self, system: str, messages: list[dict[str, Any]]) -> Reply:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        response = self._client.beta.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if getattr(response, "stop_reason", None) == "refusal":
            raise BackendError("the model declined to write a summary")
        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        # the full content (thinking blocks included) is echoed back unchanged
        return Reply(text, response.content, str(getattr(response, "model", self.model)))


def _post_json(
    url: str, body: dict[str, Any], headers: dict[str, str], timeout: float, retries: int = 4
) -> dict[str, Any]:
    """POST JSON with retries on rate limits and transient errors. Keys travel in
    headers, never in the URL, and error messages never include headers, so a key
    cannot leak into a log."""
    data = json.dumps(body).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST"
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result: dict[str, Any] = json.loads(response.read())
                return result
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_STATUS or attempt == retries:
                detail = e.read().decode(errors="replace")[:300]
                raise BackendError(f"HTTP {e.code} from {url}: {detail}") from None
            wait = float(e.headers.get("Retry-After") or 0) or 2.0 * 2**attempt
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries:
                raise BackendError(f"cannot reach {url}: {e}") from None
            wait = 2.0 * 2**attempt
        time.sleep(min(wait, 60.0))
    raise AssertionError("unreachable")


class GeminiBackend:
    provider = "gemini"

    def __init__(self, model: str | None = None, base_url: str = GEMINI_URL) -> None:
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise BackendError("no API key found (set GEMINI_API_KEY)")
        self._key = key
        self.model = model or DEFAULT_MODELS["gemini"]
        self._base = base_url.rstrip("/")

    def chat(self, system: str, messages: list[dict[str, Any]]) -> Reply:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]}
                for m in messages
            ],
            "generationConfig": {"temperature": 0, "maxOutputTokens": MAX_TOKENS},
        }  # fmt: skip
        out = _post_json(
            f"{self._base}/models/{self.model}:generateContent",
            body,
            {"x-goog-api-key": self._key},
            timeout=180,
        )
        if out.get("promptFeedback", {}).get("blockReason"):
            raise BackendError(f"prompt blocked: {out['promptFeedback']['blockReason']}")
        candidates = out.get("candidates") or []
        if not candidates:
            raise BackendError("no candidates in the response")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text:
            reason = candidates[0].get("finishReason")
            raise BackendError(f"empty response (finish reason {reason})")
        return Reply(text, text, str(out.get("modelVersion", self.model)))


class OllamaBackend:
    provider = "ollama"

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        host = host or os.environ.get("OLLAMA_HOST") or OLLAMA_HOST
        if "://" not in host:
            host = "http://" + host
        self.model = model or DEFAULT_MODELS["ollama"]
        self.host = host.rstrip("/")

    def chat(self, system: str, messages: list[dict[str, Any]]) -> Reply:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "stream": False,
            # the metrics and prompt need ~2k tokens; a repair round doubles it
            "options": {"temperature": 0, "seed": 0, "num_ctx": 8192},
        }
        out = _post_json(f"{self.host}/api/chat", body, {}, timeout=900)
        text = str(out.get("message", {}).get("content", ""))
        if not text:
            raise BackendError("empty response from Ollama")
        return Reply(text, text, str(out.get("model", self.model)))


BACKENDS: dict[str, type[AnthropicBackend] | type[GeminiBackend] | type[OllamaBackend]] = {
    "anthropic": AnthropicBackend,
    "llm": AnthropicBackend,  # the original name of the Anthropic explainer
    "gemini": GeminiBackend,
    "ollama": OllamaBackend,
}


def get_backend(name: str, model: str | None = None) -> ChatBackend:
    try:
        return BACKENDS[name](model)
    except KeyError:
        raise BackendError(f"unknown explainer backend {name!r}") from None


# ---- the explain-check-repair loop ------------------------------------------------


def explain_llm(
    metrics: dict[str, Any], backend: ChatBackend | None = None, max_attempts: int = 2
) -> LLMExplanation:
    if backend is None:
        backend = AnthropicBackend()
    payload = json.dumps(metrics_for_model(metrics), sort_keys=True)
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"Metrics JSON:\n```json\n{payload}\n```"}
    ]
    trace: list[Attempt] = []
    result: CheckResult | None = None
    text, model = "", backend.model
    for attempt in range(1, max_attempts + 1):
        start = time.perf_counter()
        reply = backend.chat(SYSTEM_PROMPT, messages)
        text, model = reply.text, reply.model
        result = check(text, metrics)
        codes = tuple(f.code for f in result.findings)
        trace.append(Attempt(text, codes, round(time.perf_counter() - start, 2)))
        if result.ok:
            return LLMExplanation(text, result, attempt, model, tuple(trace))
        problems = "\n".join(f"- {f.code}: {f.detail}" for f in result.findings[:30])
        messages += [
            {"role": "assistant", "content": reply.raw},
            {
                "role": "user",
                "content": "The checker rejected the summary:\n"
                f"{problems}\nRewrite the whole summary so that it passes every rule.",
            },
        ]
    assert result is not None
    return LLMExplanation(text, result, max_attempts, model, tuple(trace))
