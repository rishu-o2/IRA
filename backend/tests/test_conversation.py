from __future__ import annotations

import json

from ira import conversation
from ira.conversation import GeminiConversation


class DummyResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_conversation_uses_google_ai_studio_generate_content(monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    def fake_urlopen(request: object, timeout: int) -> DummyResponse:
        captured.append(
            {
                "url": request.full_url,
                "headers": request.headers,
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        return DummyResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "Hello from Gemini."},
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    monkeypatch.setattr(conversation, "urlopen", fake_urlopen)

    assistant = GeminiConversation()
    reply = assistant.reply("hello")

    assert reply == "Hello from Gemini."
    assert captured[0]["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"
    )
    assert captured[0]["timeout"] == 25
    assert captured[0]["headers"]["X-goog-api-key"] == "test-key"
    assert captured[0]["body"]["contents"][0]["parts"][0]["text"] == "hello"
    assert captured[0]["body"]["systemInstruction"]


def test_conversation_sends_history_to_generate_content(monkeypatch) -> None:
    bodies: list[dict[str, object]] = []

    def fake_urlopen(request: object, timeout: int) -> DummyResponse:
        bodies.append(json.loads(request.data.decode("utf-8")))
        return DummyResponse(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": f"ok {len(bodies)}"},
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(conversation, "urlopen", fake_urlopen)

    assistant = GeminiConversation()
    assistant.reply("first")
    assistant.reply("second")

    assert bodies[0]["contents"] == [{"role": "user", "parts": [{"text": "first"}]}]
    assert bodies[1]["contents"] == [
        {"role": "user", "parts": [{"text": "first"}]},
        {"role": "model", "parts": [{"text": "ok 1"}]},
        {"role": "user", "parts": [{"text": "second"}]},
    ]
