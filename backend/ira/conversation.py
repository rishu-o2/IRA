from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import gemini_api_key, gemini_model

GEMINI_CHAT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

SYSTEM_PROMPT = (
    "You are IRA, the user's intelligent responsive desktop assistant. "
    "Speak naturally, briefly, and helpfully. The app handles desktop actions "
    "like opening apps and websites separately, so do not claim you already "
    "performed a desktop action unless the backend says so."
)


class ConversationError(RuntimeError):
    pass


class OpenAIConversation:
    def __init__(self, max_history_messages: int = 10) -> None:
        self.max_history_messages = max_history_messages
        self.history: list[dict[str, str]] = []

    def reply(self, message: str) -> str:
        clean_message = message.strip()
        if not clean_message:
            raise ConversationError("Tell me what you want to talk about.")

        gemini_key = gemini_api_key()
        if not gemini_key:
            raise ConversationError("Conversation API is not configured. Add GEMINI_API_KEY to backend/.env.")

        model = gemini_model()
        # Convert history roles: OpenAI uses "assistant", Gemini uses "model"
        history_contents = [
            {"role": "model" if msg["role"] == "assistant" else "user", "parts": [{"text": msg["content"]}]}
            for msg in self.history
        ]
        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                *history_contents,
                {"role": "user", "parts": [{"text": clean_message}]},
            ],
            "generationConfig": {
                "temperature": 0.7,
            },
        }
        headers = {
            "x-goog-api-key": gemini_key,
            "Content-Type": "application/json",
        }
        endpoint = f"{GEMINI_CHAT_ENDPOINT}/{model}:generateContent"
        request = Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urlopen(request, timeout=25) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ConversationError(_api_error_message(exc, True)) from exc
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise ConversationError("Conversation API request failed.") from exc

        reply_text = _parse_chat_reply(body, True)
        self._remember(clean_message, reply_text)
        return reply_text

    def _remember(self, user_message: str, assistant_message: str) -> None:
        self.history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )
        if len(self.history) > self.max_history_messages:
            self.history = self.history[-self.max_history_messages :]


def _parse_chat_reply(body: dict[str, Any], is_gemini: bool) -> str:
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ConversationError("Conversation API returned no reply.")

    first = candidates[0]
    content = first.get("content") if isinstance(first, dict) else None
    if isinstance(content, dict):
        parts = content.get("parts") if isinstance(content, dict) else None
        if isinstance(parts, list) and parts:
            first_part = parts[0]
            text = first_part.get("text") if isinstance(first_part, dict) else None
            if isinstance(text, str) and text.strip():
                return text.strip()
    raise ConversationError("Conversation API returned an empty reply.")


def _api_error_message(exc: HTTPError, is_gemini: bool) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return f"Conversation API returned HTTP {exc.code}."

    error = payload.get("error", {})
    message = str(error.get("message", "")).strip()

    if exc.code in {401, 403}:
        return "Conversation API rejected the Gemini key. Check GEMINI_API_KEY in backend/.env."

    if message:
        return f"Conversation API error: {message}"

    return f"Conversation API returned HTTP {exc.code}."
