"""
skills/virtual_world_skill.py – Virtual world interaction skill.

Extracted from assistant.py _handle_internal (Phase 7.1):
  * change mood to …
  * virtual world status / virtual status
  * add knowledge …
"""
from __future__ import annotations

from ..brain.models import AssistantResponse
from ..virtual_world import VirtualWorld
from .base import Skill


class VirtualWorldSkill(Skill):
    """Handles virtual world debug & interaction commands."""

    def __init__(self, virtual_world: VirtualWorld) -> None:
        self._vw = virtual_world

    @property
    def name(self) -> str:
        return "virtual_world"

    @property
    def description(self) -> str:
        return "Changes mood, adds knowledge, and reports virtual world status."

    def can_handle(self, command: str) -> bool:
        lowered = command.lower()
        if lowered.startswith("change mood to "):
            return True
        if lowered in {"virtual world status", "virtual status"}:
            return True
        if lowered.startswith("add knowledge "):
            return True
        return False

    def execute(self, command: str) -> AssistantResponse:
        lowered = command.lower()

        if lowered.startswith("change mood to "):
            new_mood = lowered[len("change mood to "):].strip()
            self._vw.state["mood"] = new_mood
            return AssistantResponse(f"Virtual world mood is now {new_mood}.")

        if lowered in {"virtual world status", "virtual status"}:
            status = "\n".join(
                f"{k}: {v}" for k, v in self._vw.state.items()
            )
            return AssistantResponse(f"Virtual world status:\n{status}")

        if lowered.startswith("add knowledge "):
            fact = command[len("add knowledge "):].strip()
            if fact:
                self._vw.state.setdefault("knowledge_base", []).append(fact)
                return AssistantResponse(f"Noted. I'll keep that in mind: {fact}")

        return AssistantResponse("Could not process virtual world command.", handled=False)
