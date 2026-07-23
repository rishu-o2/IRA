from __future__ import annotations

import re

from backend.ira.memory.long_term import MemoryEntry, MemoryType


class ConsolidationRules:
    _EQUIVALENT_VALUES = {
        "vscode": "VS Code",
        "vs code": "VS Code",
        "visual studio code": "VS Code",
    }
    _EQUIVALENT_KEYS = {
        "uses_vs_code": "favorite_editor",
        "uses_vscode": "favorite_editor",
        "uses_visual_studio_code": "favorite_editor",
        "preferred_editor": "favorite_editor",
    }

    def consolidation_key(self, memory: MemoryEntry) -> str:
        metadata_key = str(memory.metadata.get("key", "")).strip()
        if metadata_key:
            return self._canonical_key(metadata_key)
        return f"{memory.type.name}:{self._subject_from_content(memory.content)}"

    def canonical_value(self, memory: MemoryEntry) -> str:
        value = str(memory.metadata.get("value", "")).strip()
        if not value:
            value = self._value_from_content(memory.content)
        return self._canonical_value(value)

    def canonical_content(self, memory: MemoryEntry) -> str:
        key = self.consolidation_key(memory)
        value = self.canonical_value(memory)
        if key == "favorite_editor":
            return f"Preferred editor = {value}"
        if key == "favorite_browser":
            return f"Favorite browser = {value}"
        if key == "preferred_language":
            return f"Preferred language = {value}"
        if key == "project":
            return f"Project = {value}"
        if " = " in memory.content:
            subject = memory.content.split(" = ", 1)[0].strip()
            return f"{subject} = {value}"
        return memory.content

    def equivalent(self, first: MemoryEntry, second: MemoryEntry) -> bool:
        return (
            first.type == second.type
            and self.consolidation_key(first) == self.consolidation_key(second)
            and self.canonical_value(first).casefold() == self.canonical_value(second).casefold()
        )

    def conflicts(self, first: MemoryEntry, second: MemoryEntry) -> bool:
        return (
            first.type == second.type
            and self.consolidation_key(first) == self.consolidation_key(second)
            and self.canonical_value(first).casefold() != self.canonical_value(second).casefold()
        )

    def normalized_metadata(self, memory: MemoryEntry) -> dict[str, object]:
        metadata = dict(memory.metadata)
        metadata["key"] = self.consolidation_key(memory)
        if "value" in metadata:
            metadata["value"] = self.canonical_value(memory)
        return metadata

    def _canonical_key(self, key: str) -> str:
        normalized = self._normalize_key(key)
        return self._EQUIVALENT_KEYS.get(normalized, normalized)

    def _canonical_value(self, value: str) -> str:
        normalized = self._normalize_text(value)
        if normalized in self._EQUIVALENT_VALUES:
            return self._EQUIVALENT_VALUES[normalized]
        return value.strip()

    def _subject_from_content(self, content: str) -> str:
        if " = " in content:
            return self._normalize_key(content.split(" = ", 1)[0])
        return self._normalize_key(content)

    def _value_from_content(self, content: str) -> str:
        if " = " in content:
            return content.split(" = ", 1)[1].strip()
        return content.strip()

    def _normalize_key(self, text: str) -> str:
        return "_".join(re.findall(r"[a-z0-9]+", text.casefold()))

    def _normalize_text(self, text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))
