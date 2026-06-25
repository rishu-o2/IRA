from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import gemini_api_key, gemini_model

GEMINI_MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

SYSTEM_PROMPT = (
    "You are IRA, the user's intelligent responsive desktop assistant. "
    "Speak naturally, briefly, and helpfully. The app handles desktop actions "
    "like opening apps and websites separately, so do not claim you already "
    "performed a desktop action unless the backend says so.\n\n"
    "SELF-MODIFICATION CAPABILITY:\n"
    "You can modify, improve, or add features to your own codebase (backend and frontend) "
    "when requested by the user. To edit or create files, output special tags in your response:\n"
    "1. Use <write_file path=\"relative/path/from/project_root\">new file content</write_file> to create or overwrite a file completely.\n"
    "2. Use <patch_file path=\"relative/path/from/project_root\">\n<<<<\nexact original code to replace\n====\nnew replacement code\n>>>>\n</patch_file> to update specific lines in existing files.\n"
    "Paths must be relative to the project root (e.g. 'backend/ira/actions.py', 'frontend/src/main.tsx', 'backend/requirements.txt'). "
    "Explain what you are doing, then write the tags carefully. Ensure all your changes are valid code."
)


class ConversationError(RuntimeError):
    pass


class GeminiConversation:
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
        try:
            body = self._send_generate_content_request(clean_message, gemini_key, model)
        except HTTPError as exc:
            raise ConversationError(_api_error_message(exc)) from exc
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise ConversationError(_request_error_message(exc)) from exc

        try:
            reply_text = _parse_chat_reply(body)
        except ConversationError:
            raise
        except (TypeError, ValueError) as exc:
            raise ConversationError("Conversation API returned an unreadable reply.") from exc

        self._remember(clean_message, reply_text)
        return reply_text

    def _send_generate_content_request(self, message: str, api_key: str, model: str) -> dict[str, Any]:
        history_contents = [
            {"role": "model" if msg["role"] == "assistant" else "user", "parts": [{"text": msg["content"]}]}
            for msg in self.history
        ]
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                *history_contents,
                {"role": "user", "parts": [{"text": message}]},
            ],
            "generationConfig": {"temperature": 0.7},
        }
        endpoint = f"{GEMINI_MODELS_ENDPOINT}/{model}:generateContent"
        try:
            return _send_json_request(endpoint, payload, api_key)
        except HTTPError as exc:
            raise ConversationError(_api_error_message(exc, True)) from exc
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise ConversationError(_request_error_message(exc)) from exc

    def _remember(self, user_message: str, assistant_message: str) -> None:
        self.history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )
        if len(self.history) > self.max_history_messages:
            self.history = self.history[-self.max_history_messages :]


def _send_json_request(endpoint: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_chat_reply(body: dict[str, Any]) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

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


def _api_error_message(exc: HTTPError, is_gemini: bool = True) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return f"Conversation API returned HTTP {exc.code}."

    error = payload.get("error", {})
    message = str(error.get("message", "")).strip()

    if exc.code in {401, 403}:
        return "Conversation API rejected the Gemini API key. Check GEMINI_API_KEY in backend/.env."

    if message:
        return f"Conversation API error: {message}"

    return f"Conversation API returned HTTP {exc.code}."


def _request_error_message(exc: BaseException) -> str:
    detail = str(exc).strip()
    if detail:
        return f"Conversation API request failed: {detail}"
    return "Conversation API request failed."
