from __future__ import annotations

from dataclasses import dataclass

from .actions import ActionError, open_app, open_path, open_website, play_youtube_search


@dataclass(frozen=True)
class AssistantResponse:
    text: str
    handled: bool = True


class IRAAssistant:
    def handle(self, message: str) -> AssistantResponse:
        command = message.strip()
        lowered = command.lower()

        if not command:
            return AssistantResponse("I'm here. Tell me what you want to do.", handled=False)

        try:
            if lowered in {"hi", "hello", "hey"}:
                return AssistantResponse("Hello. IRA is online.")

            if lowered in {"help", "commands", "what can you do"}:
                return AssistantResponse(self._help_text())

            if lowered.startswith("open folder "):
                target = command[len("open folder ") :].strip()
                return AssistantResponse(open_path(target))

            if lowered.startswith("open file "):
                target = command[len("open file ") :].strip()
                return AssistantResponse(open_path(target))

            if lowered.startswith("open website "):
                target = command[len("open website ") :].strip()
                return AssistantResponse(open_website(target))

            if lowered.startswith("open "):
                app_name = command[len("open ") :].strip()
                return AssistantResponse(open_app(app_name))

            if lowered.startswith("play "):
                query = command[len("play ") :].strip()
                return AssistantResponse(play_youtube_search(query))

        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        return AssistantResponse(
            "I do not know how to do that yet, but this is exactly where my skills will grow.",
            handled=False,
        )

    def _help_text(self) -> str:
        return "\n".join(
            [
                "You can try:",
                "- open notepad",
                "- open calculator",
                "- open website youtube.com",
                "- open folder C:\\Users\\hp\\Downloads",
                "- open file C:\\path\\to\\file.txt",
                "- play relaxing music",
                "- exit",
            ]
        )

