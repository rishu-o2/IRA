from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import gemini_api_key, gemini_model, openai_api_key, openai_model

OPENAI_CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
GEMINI_CHAT_ENDPOINTS = [
    "https://gemini.googleapis.com/v1/models",
    "https://gemini.googleapis.com/v1beta2/models",
]

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

        openai_key = openai_api_key()
        gemini_key = gemini_api_key()

        if gemini_key:
            model = gemini_model()
            payload = {
                "messages": [
                    {"author": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
                    *[
                        {"author": msg["role"], "content": [{"type": "text", "text": msg["content"]}]}
                        for msg in self.history
                    ],
                    {"author": "user", "content": [{"type": "text", "text": clean_message}]},
                ],
                "temperature": 0.7,
            }
            headers = {
                "Authorization": f"Bearer {gemini_key}",
                "Content-Type": "application/json",
            }
            request_errors: list[str] = []
            response_body = None
            for base_url in GEMINI_CHAT_ENDPOINTS:
                endpoint = f"{base_url}/{model}:generateMessage"
                request = Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
                try:
                    with urlopen(request, timeout=25) as response:
                        response_body = json.loads(response.read().decode("utf-8"))
                    break
                except HTTPError as exc:
                    request_errors.append(
                        f"{endpoint} returned {exc.code}: {exc.read().decode('utf-8', errors='replace')}"
                    )
                    if exc.code != 404:
                        raise ConversationError(_api_error_message(exc, True)) from exc
                except (OSError, URLError, json.JSONDecodeError) as exc:
                    raise ConversationError("Conversation API request failed.") from exc

            if response_body is None:
                raise ConversationError(
                    "Gemini endpoint failed. Tried: " + "; ".join(request_errors)
                )
        else:
            api_key = openai_key
            if not api_key:
                raise ConversationError("Conversation API is not configured. Add OPENAI_API_KEY or GEMINI_API_KEY to backend/.env.")

            payload = {
                "model": openai_model(),
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *self.history,
                    {"role": "user", "content": clean_message},
                ],
                "temperature": 0.7,
            }
            request = Request(
                OPENAI_CHAT_ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

        if not gemini_key:
            try:
                with urlopen(request, timeout=25) as response:
                    body = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                raise ConversationError(_api_error_message(exc, False)) from exc
            except (OSError, URLError, json.JSONDecodeError) as exc:
                raise ConversationError("Conversation API request failed.") from exc

        reply_text = _parse_chat_reply(body, gemini_key is not None)
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
    if is_gemini:
        candidates = body.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ConversationError("Conversation API returned no reply.")

        first = candidates[0]
        content = first.get("content") if isinstance(first, dict) else None
        if isinstance(content, list) and content:
            first_piece = content[0]
            text = first_piece.get("text") if isinstance(first_piece, dict) else None
            if isinstance(text, str) and text.strip():
                return text.strip()
        raise ConversationError("Conversation API returned an empty reply.")

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ConversationError("Conversation API returned no reply.")

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str) and content.strip():
        return content.strip()

    raise ConversationError("Conversation API returned an empty reply.")


def _api_error_message(exc: HTTPError, is_gemini: bool) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return f"Conversation API returned HTTP {exc.code}."

    error = payload.get("error", {})
    message = str(error.get("message", "")).strip()

    if exc.code in {401, 403}:
        if is_gemini:
            return "Conversation API rejected the Gemini key. Check GEMINI_API_KEY in backend/.env."
        return "Conversation API rejected the OpenAI key. Check OPENAI_API_KEY in backend/.env."

    if message:
        return f"Conversation API error: {message}"

    return f"Conversation API returned HTTP {exc.code}."
