from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass

from .actions import ActionError, open_app, open_known_folder, open_path, open_website, play_youtube_search, search_web


@dataclass(frozen=True)
class AssistantResponse:
    text: str
    handled: bool = True


class IRAAssistant:
    def handle(self, message: str) -> AssistantResponse:
        command = self._normalize_command(message)
        lowered = command.lower()

        if not command:
            return AssistantResponse("I'm here. Tell me what you want to do.", handled=False)

        try:
            if lowered in {"hi", "hello", "hey"}:
                return AssistantResponse("Hello. IRA is online and ready.")

            if lowered in {"help", "commands", "what can you do", "what can you do for me"}:
                return AssistantResponse(self._help_text())

            if lowered in {"time", "what time is it", "tell me the time", "current time"}:
                return AssistantResponse(f"It is {datetime.now().strftime('%I:%M %p').lstrip('0')}.")

            if lowered in {"date", "what date is it", "what is today's date", "today's date"}:
                return AssistantResponse(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}.")

            if lowered.startswith(("launch ", "start ")):
                app_name = command.split(" ", 1)[1].strip()
                return AssistantResponse(open_app(app_name))

            if lowered.startswith("go to "):
                target = command[len("go to ") :].strip()
                return AssistantResponse(open_website(target))

            if lowered.startswith("visit "):
                target = command[len("visit ") :].strip()
                return AssistantResponse(open_website(target))

            if lowered.startswith("open folder "):
                target = command[len("open folder ") :].strip()
                if self._is_known_folder(target):
                    return AssistantResponse(open_known_folder(target))
                return AssistantResponse(open_path(target))

            if lowered.startswith("open file "):
                target = command[len("open file ") :].strip()
                return AssistantResponse(open_path(target))

            if lowered.startswith("open website "):
                target = command[len("open website ") :].strip()
                return AssistantResponse(open_website(target))

            if lowered.startswith("open youtube"):
                return AssistantResponse(open_website("youtube.com"))

            if lowered.startswith("open google"):
                return AssistantResponse(open_website("google.com"))

            if lowered.startswith("open downloads"):
                return AssistantResponse(open_known_folder("downloads"))

            if lowered.startswith("open documents"):
                return AssistantResponse(open_known_folder("documents"))

            if lowered.startswith("open desktop"):
                return AssistantResponse(open_known_folder("desktop"))

            if lowered.startswith("open pictures") or lowered.startswith("open photos"):
                return AssistantResponse(open_known_folder("pictures"))

            if lowered.startswith("search google for "):
                query = command[len("search google for ") :].strip()
                return AssistantResponse(search_web(query))

            if lowered.startswith("search for "):
                query = command[len("search for ") :].strip()
                return AssistantResponse(search_web(query))

            if lowered.startswith("google "):
                query = command[len("google ") :].strip()
                return AssistantResponse(search_web(query))

            if lowered.startswith("find "):
                query = command[len("find ") :].strip()
                return AssistantResponse(search_web(query))

            if lowered.startswith("open "):
                target = command[len("open ") :].strip()
                if self._looks_like_website(target):
                    return AssistantResponse(open_website(target))
                if self._is_known_folder(target):
                    return AssistantResponse(open_known_folder(target))
                return AssistantResponse(open_app(target))

            if lowered.startswith("play "):
                query = command[len("play ") :].strip()
                if query.lower().endswith(" on youtube"):
                    query = query[: -len(" on youtube")].strip()
                return AssistantResponse(play_youtube_search(query))

        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        return AssistantResponse(
            "I can open apps, folders, websites, search Google, play YouTube results, and tell the time. Try saying open notepad, search for AI news, or play relaxing music.",
            handled=False,
        )

    def _normalize_command(self, message: str) -> str:
        command = " ".join(message.strip().split())
        lowered = command.lower()

        for prefix in (
            "ira ",
            "ira, ",
            "ira: ",
            "hey ira ",
            "hey ira, ",
            "hello ira ",
            "hello ira, ",
            "hi ira ",
            "hi ira, ",
            "please ",
            "can you ",
            "could you ",
            "would you ",
        ):
            if lowered.startswith(prefix):
                return command[len(prefix) :].strip()

        return command

    def _looks_like_website(self, target: str) -> bool:
        lowered = target.lower()
        return lowered.startswith(("http://", "https://")) or "." in lowered

    def _is_known_folder(self, target: str) -> bool:
        return target.lower().strip() in {
            "desktop",
            "downloads",
            "download",
            "documents",
            "document",
            "pictures",
            "photos",
            "music",
            "videos",
        }

    def _help_text(self) -> str:
        return "\n".join(
            [
                "You can try:",
                "- open notepad",
                "- open calculator",
                "- open downloads",
                "- open website youtube.com",
                "- search for Python tutorials",
                "- open folder C:\\Users\\hp\\Downloads",
                "- open file C:\\path\\to\\file.txt",
                "- play relaxing music",
                "- what time is it",
            ]
        )
