"""
skills/preference.py – Memory-aware preference routing skill.

Extracted from assistant.py:
  * _PREFERENCE_TARGETS (routing config)
  * _handle_preference_aware_skill
  * _preferred_target

A PreferenceSkill matches commands like "open my editor" and resolves
the actual target (e.g. "VS Code") from long-term memory before
delegating to the appropriate capability skill.
"""
from __future__ import annotations

from ..brain.models import AssistantResponse
from ..memory.retrieval import ContextRetriever
from .base import Skill
from .registry import SkillRegistry

# ---------------------------------------------------------------------------
# Routing configuration
# ---------------------------------------------------------------------------
_PREFERENCE_TARGETS: dict[str, dict[str, object]] = {
    "editor": {
        "keys": ("favorite_editor",),
        "commands": {
            "open my editor", "open editor",
            "launch my editor", "launch editor",
            "start my editor", "start editor",
        },
        "skill": "app",
        "template": "open {target}",
        "aliases": {
            "vs code": "code",
            "vscode": "code",
            "visual studio code": "code",
        },
    },
    "browser": {
        "keys": ("favorite_browser",),
        "commands": {
            "open my browser", "open browser",
            "launch my browser", "launch browser",
            "start my browser", "start browser",
        },
        "skill": "app",
        "template": "open {target}",
        "aliases": {
            "chrome": "chrome",
            "google chrome": "chrome",
            "firefox": "firefox",
            "edge": "edge",
            "microsoft edge": "edge",
        },
    },
    "terminal": {
        "keys": ("favorite_terminal",),
        "commands": {
            "open my terminal", "open terminal",
            "launch my terminal", "launch terminal",
            "start my terminal", "start terminal",
        },
        "skill": "app",
        "template": "open {target}",
    },
    "music_player": {
        "keys": ("favorite_music_player",),
        "commands": {"play music", "play my music", "resume music"},
        "skill": "media",
        "template": "play music",
        "open_template": "open {target}",
        "aliases": {
            "spotify": "spotify",
        },
    },
}

# Flat set of all preference commands for fast can_handle lookup.
_ALL_PREFERENCE_COMMANDS: frozenset[str] = frozenset(
    cmd
    for config in _PREFERENCE_TARGETS.values()
    for cmd in config["commands"]  # type: ignore[union-attr]
)


class PreferenceSkill(Skill):
    """Routes commands to capability skills based on stored user preferences."""

    def __init__(
        self,
        registry: SkillRegistry,
        context_retriever: ContextRetriever,
    ) -> None:
        self._registry = registry
        self._context_retriever = context_retriever

    @property
    def name(self) -> str:
        return "preference"

    @property
    def description(self) -> str:
        return "Routes generic capability commands using stored user preferences."

    def can_handle(self, command: str) -> bool:
        return command.lower() in _ALL_PREFERENCE_COMMANDS

    def execute(self, command: str) -> AssistantResponse:
        lowered = command.lower()
        for config in _PREFERENCE_TARGETS.values():
            commands = config["commands"]
            if not isinstance(commands, set) or lowered not in commands:
                continue

            target = self._preferred_target(command, config["keys"])
            if target is None:
                # No preference stored; delegate to the underlying skill
                # with the original command so that AppSkill can handle
                # "open editor" generically.
                skill_name = str(config["skill"])
                underlying = self._registry.get(skill_name)
                if underlying is not None:
                    return underlying.execute(command)
                return AssistantResponse("", handled=False)

            aliases = config.get("aliases", {})
            if isinstance(aliases, dict):
                target = str(aliases.get(target.casefold(), target))

            skill_name = str(config["skill"])
            skill = self._registry.get(skill_name)
            if skill is None:
                return AssistantResponse("", handled=False)

            if skill_name == "media":
                return self._execute_media_preference(config, target, skill)

            routed_command = str(config["template"]).format(target=target)
            return skill.execute(routed_command)

        # Unreachable if can_handle is implemented correctly.
        return AssistantResponse("", handled=False)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _preferred_target(self, query: str, keys: object) -> str | None:
        if not isinstance(keys, tuple):
            return None
        context = self._context_retriever.retrieve(query)
        for memory in context.memories:
            key = str(memory.metadata.get("key", "")).casefold()
            if key in keys:
                value = str(memory.metadata.get("value", "")).strip()
                if value:
                    return value
        return None

    def _execute_media_preference(
        self,
        config: dict,
        target: str,
        media_skill: Skill,
    ) -> AssistantResponse:
        app_skill = self._registry.get("app")
        open_template = str(config.get("open_template", "open {target}"))
        open_command = open_template.format(target=target)
        media_command = str(config["template"])

        if app_skill is None:
            return media_skill.execute(media_command)

        open_result = app_skill.execute(open_command)
        if not open_result.handled:
            return open_result
        media_result = media_skill.execute(media_command)
        if not media_result.handled:
            return media_result
        return AssistantResponse(f"{open_result.text}\n{media_result.text}")
