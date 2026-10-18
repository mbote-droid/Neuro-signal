"""ADR-013, S-04, H7: LLM backends (Gemini, Ollama) without network or keys."""

from __future__ import annotations

import hashlib
import io
import json
import urllib.error

import pytest

from neurosignal.explain import llm, template
from neurosignal.explain.llm import (
    BackendError,
    GeminiBackend,
    OllamaBackend,
    Reply,
    explain_llm,
    get_backend,
)
from neurosignal.report import build

# H7 (PROBLEM_STATEMENT §10) fixes the prompt; changing it invalidates the registration.
REGISTERED_PROMPT_SHA256 = "c96529342eab6d832c9cec49859d7c8bfcfa4625ce24ced15b22fe95554a5c4b"


def test_system_prompt_is_the_registered_one():
    assert hashlib.sha256(llm.SYSTEM_PROMPT.encode()).hexdigest() == REGISTERED_PROMPT_SHA256


class FakeBackend:
    provider = "fake"
    model = "fake-1"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, system, messages):
        self.calls.append([dict(m) for m in messages])
        text = self.replies.pop(0)
        return Reply(text, text, "fake-1.2")


def test_loop_records_every_attempt(metrics):
    good = template.explain(metrics)
    backend = FakeBackend([good + " There were 12 spikes.", good])
    out = explain_llm(metrics, backend)
    assert out.check.ok and out.attempts == 2 and out.model == "fake-1.2"
    assert [a.codes for a in out.trace] == [("UNCITED_NUMBER",), ()]
    assert backend.calls[1][-2] == {"role": "assistant", "content": good + " There were 12 spikes."}


class FakeHTTP:
    """Stands in for urllib.request.urlopen: records requests, replays responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return io.BytesIO(json.dumps(r).encode())


def _http_error(code, body="busy"):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body.encode()))


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


def gemini_reply(text, version="gemini-test-001"):
    parts = [{"text": "thinking...", "thought": True}, {"text": text}]
    return {"candidates": [{"content": {"parts": parts}}], "modelVersion": version}


def test_gemini_request_and_reply(metrics, monkeypatch):
    secret = "AIza-test-SECRET"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    fake = FakeHTTP([gemini_reply(template.explain(metrics))])
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    out = explain_llm(metrics, GeminiBackend("gemini-test"))
    assert out.check.ok and out.model == "gemini-test-001"
    req = fake.requests[0]
    assert req.full_url.endswith("/models/gemini-test:generateContent")
    assert secret not in req.full_url  # the key travels in a header, not the URL
    assert req.get_header("X-goog-api-key") == secret
    body = json.loads(req.data)
    assert body["generationConfig"]["temperature"] == 0
    assert body["systemInstruction"]["parts"][0]["text"] == llm.SYSTEM_PROMPT
    assert [c["role"] for c in body["contents"]] == ["user"]


def test_gemini_repair_uses_model_role(metrics, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    good = template.explain(metrics)
    fake = FakeHTTP([gemini_reply(good + " This is epilepsy."), gemini_reply(good)])
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    out = explain_llm(metrics, GeminiBackend("g"))
    assert out.attempts == 2 and out.check.ok
    roles = [c["role"] for c in json.loads(fake.requests[1].data)["contents"]]
    assert roles == ["user", "model", "user"]


def test_gemini_without_key_is_refused(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(BackendError, match="GEMINI_API_KEY"):
        GeminiBackend()


def test_rate_limit_is_retried(metrics, monkeypatch, no_sleep):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    fake = FakeHTTP([_http_error(429), _http_error(503), gemini_reply(template.explain(metrics))])
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    assert explain_llm(metrics, GeminiBackend("g")).check.ok
    assert len(fake.requests) == 3


def test_http_error_message_never_contains_the_key(monkeypatch, no_sleep):
    secret = "AIza-test-SECRET"
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    monkeypatch.setattr(llm.urllib.request, "urlopen", FakeHTTP([_http_error(400, "bad request")]))
    with pytest.raises(BackendError) as e:
        GeminiBackend("g").chat("s", [{"role": "user", "content": "x"}])
    assert "400" in str(e.value) and secret not in str(e.value)


def test_ollama_request_and_reply(metrics, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11434")
    reply = {"model": "qwen-test:3b", "message": {"content": template.explain(metrics)}}
    fake = FakeHTTP([reply])
    monkeypatch.setattr(llm.urllib.request, "urlopen", fake)
    out = explain_llm(metrics, OllamaBackend("qwen-test:3b"))
    assert out.check.ok and out.model == "qwen-test:3b"
    req = fake.requests[0]
    assert req.full_url == "http://127.0.0.1:11434/api/chat"
    body = json.loads(req.data)
    assert body["stream"] is False and body["options"]["temperature"] == 0
    assert body["messages"][0] == {"role": "system", "content": llm.SYSTEM_PROMPT}


def test_unreachable_backend_falls_back_to_template(metrics, monkeypatch, no_sleep):
    down = urllib.error.URLError("connection refused")
    monkeypatch.setattr(llm.urllib.request, "urlopen", FakeHTTP([down] * 5))
    text, result, source = build.explain(metrics, "ollama", "m")
    assert result.ok and text == template.explain(metrics)
    assert source.startswith("template (ollama: cannot reach")


def test_rejected_text_is_never_shown(metrics, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    bad = gemini_reply("research use only. 99 [[recording.n_channels]]")
    monkeypatch.setattr(llm.urllib.request, "urlopen", FakeHTTP([bad, bad]))
    text, result, source = build.explain(metrics, "gemini")
    assert result.ok and text == template.explain(metrics)
    assert "rejected by the claim checker" in source


def test_unknown_backend():
    with pytest.raises(BackendError):
        get_backend("nope")


def test_ollama_over_a_real_socket(metrics):
    """The urllib path end to end, against a local server that speaks Ollama's API."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    good = template.explain(metrics)
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(
                (self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            )
            body = json.dumps({"model": "local-test", "message": {"content": good}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        host = f"127.0.0.1:{server.server_address[1]}"
        out = explain_llm(metrics, OllamaBackend("local-test", host=host))
    finally:
        server.shutdown()
    assert out.check.ok and out.model == "local-test"
    assert seen[0][0] == "/api/chat" and seen[0][1]["model"] == "local-test"
