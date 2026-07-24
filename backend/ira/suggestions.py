from __future__ import annotations

from .memory.long_term import MemoryEntry, MemoryType


class ProactiveSuggestionEngine:
    """Deterministic follow-up suggestions for newly learned personal memories."""

    def suggest(self, memories: list[MemoryEntry]) -> str | None:
        for memory in memories:
            suggestion = self._suggest_for(memory)
            if suggestion is not None:
                return suggestion
        return None

    def _suggest_for(self, memory: MemoryEntry) -> str | None:
        category = str(memory.metadata.get("category", "")).casefold()
        key = str(memory.metadata.get("key", "")).casefold()
        content = memory.content.casefold()
        value = str(memory.metadata.get("value", ""))

        if category == "exam" or "exam" in key or "exam" in content:
            return "Would you like me to remind you before it?"

        if memory.type == MemoryType.GOAL:
            if key == "project" or "project" in content or self._looks_like_project(value):
                return "Would you like me to keep this project in your active goals?"
            return "Would you like me to keep track of your progress?"

        if memory.type == MemoryType.PREFERENCE:
            if key == "favorite_editor":
                editor = value or "that editor"
                return f"I'll use {editor} whenever you ask me to open your editor."
            return "I'll remember that preference for future conversations."

        if memory.type == MemoryType.NOTE:
            return "I'll remember that preference for future conversations."

        return None

    def _looks_like_project(self, value: str) -> bool:
        normalized = value.casefold()
        return any(term in normalized for term in {"assistant", "app", "website", "project", "system"})
