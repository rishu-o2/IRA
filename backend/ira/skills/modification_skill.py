"""
skills/modification_skill.py – Modification introspection skill.

Extracted from assistant.py _handle_internal (Phase 7.2):
  * what did you update
  * show updates
  * recent changes / recent modifications
  * what changed
"""
from __future__ import annotations

from ..brain.models import AssistantResponse
from .base import Skill


class ModificationSkill(Skill):
    """Reports on self-modifications applied during the current session."""

    def __init__(self, modification_history: list) -> None:
        self._history = modification_history

    @property
    def name(self) -> str:
        return "modification"

    @property
    def description(self) -> str:
        return "Reports on code modifications applied during the current session."

    _TRIGGERS: frozenset[str] = frozenset({
        "what did you update",
        "show updates",
        "recent changes",
        "what changed",
        "recent modifications",
    })

    def can_handle(self, command: str) -> bool:
        return command.lower() in self._TRIGGERS

    def execute(self, command: str) -> AssistantResponse:
        mods = self._history
        if not mods:
            return AssistantResponse(
                "I have not made any modifications to my codebase yet."
            )
        changes = "\n".join(f"- [{m['type']}] {m['path']}" for m in mods)
        return AssistantResponse(
            f"Here are the modifications I've applied to myself during this session:\n{changes}"
        )
