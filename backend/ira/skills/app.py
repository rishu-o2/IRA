import re
from .base import Skill
from ..assistant import AssistantResponse
from ..actions import ActionError
from ..tools import desktop_tools

# Verbs that prefix commands but carry no semantic meaning for routing
_VERBS = {"open", "launch", "start", "run"}

# Folder names handled via open_known_folder
_KNOWN_FOLDERS = {"downloads", "documents", "desktop", "pictures", "videos", "music"}

# Alias normalization map: user-facing alias → canonical target passed to open_app
_ALIASES: dict[str, str] = {
    "google chrome": "chrome",
    "chrome": "chrome",
    "firefox": "firefox",
    "edge": "edge",
    "microsoft edge": "edge",
    "brave": "brave",
    "opera": "opera",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "visual studio": "visual studio",
    "notepad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "paint": "paint",
    "word": "word",
    "excel": "excel",
    "powerpoint": "powerpoint",
    "explorer": "explorer",
    "file explorer": "explorer",
    "spotify": "spotify",
    "slack": "slack",
    "discord": "discord",
    "vlc": "vlc",
    "teams": "teams",
    "skype": "skype",
    "zoom": "zoom",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
}


def open_app(app_name: str) -> str:
    return desktop_tools.open_app(app_name)


def open_known_folder(folder_name: str) -> str:
    return desktop_tools.open_known_folder(folder_name)


def _strip_verb(command: str) -> str:
    """Remove a leading launch verb from the command, if present."""
    parts = command.split(maxsplit=1)
    if parts and parts[0].lower() in _VERBS:
        return parts[1] if len(parts) > 1 else ""
    return command


def _normalize_target(raw: str) -> str:
    """Normalize an alias to its canonical form, or return the raw value."""
    return _ALIASES.get(raw.lower(), raw)


class AppSkill(Skill):
    """Skill responsible for launching applications and opening common Windows folders."""

    @property
    def name(self) -> str:
        return "app"

    @property
    def description(self) -> str:
        return "Launches desktop applications and opens common Windows folders."

    def can_handle(self, command: str) -> bool:
        """Return True if the command is an application launch or folder open."""
        parts = command.lower().split(maxsplit=1)
        if not parts or parts[0] not in _VERBS:
            return False

        target = parts[1].strip() if len(parts) > 1 else ""
        if not target:
            return False

        # Recognized alias or known folder
        if target in _ALIASES or target in _KNOWN_FOLDERS:
            return True

        # Single-word, non-system targets are treated as potential app names.
        # Exclude multi-word phrases not matching any alias (e.g. "search python").
        # A target with exactly one word that is not a system/contextual keyword
        # is assumed to be an app name the user wants to open.
        excluded_singles = {
            "weather", "news", "time", "date", "hello", "hi",
        }
        words = target.split()
        if len(words) == 1 and words[0] not in excluded_singles:
            return True

        return False

    def execute(self, command: str) -> AssistantResponse:
        """Strip the leading verb, normalize the target, and delegate to the action layer."""
        raw_target = _strip_verb(command).strip()
        target = _normalize_target(raw_target)

        try:
            if target.lower() in _KNOWN_FOLDERS:
                result = open_known_folder(target.lower())
            else:
                result = open_app(target)
                if target != raw_target and result == f"Opening {target}":
                    result = f"Opening {raw_target}"
        except ActionError:
            raise  # propagate exactly — no swallowing

        return AssistantResponse(result)
