from __future__ import annotations

import re

from backend.ira.memory.long_term import MemoryEntry, MemoryType

from .rules import MemoryRules


class MemoryExtractor:
    def __init__(self, rules: MemoryRules | None = None) -> None:
        self.rules = rules or MemoryRules()

    def extract(self, text: str) -> list[MemoryEntry]:
        memories: list[MemoryEntry] = []
        for clause in self._clauses(text):
            if not self.rules.should_remember(clause):
                continue
            memory = self._extract_clause(clause)
            if memory is not None:
                memories.append(memory)
        return memories

    def _clauses(self, text: str) -> list[str]:
        clauses = re.split(r"[.;]|\s+and\s+|\s*,\s*", text)
        return [clause.strip() for clause in clauses if clause.strip()]

    def _extract_clause(self, clause: str) -> MemoryEntry | None:
        normalized = self.rules.normalize(clause)
        return (
            self._favorite(normalized)
            or self._preference(normalized)
            or self._goal(normalized)
            or self._personal_fact(normalized)
            or self._note(normalized)
        )

    def _favorite(self, normalized: str) -> MemoryEntry | None:
        match = re.match(r"my favorite ([a-z ]+) is (.+)", normalized)
        if match is None:
            return None
        subject = match.group(1).strip()
        value = self._title_value(match.group(2))
        return self._entry(
            MemoryType.PREFERENCE,
            f"Favorite {subject} = {value}",
            "preference",
            f"favorite_{subject.replace(' ', '_')}",
            value,
        )

    def _preference(self, normalized: str) -> MemoryEntry | None:
        match = re.match(r"i prefer (.+)", normalized)
        if match is not None:
            value = self._title_value(match.group(1))
            return self._entry(MemoryType.PREFERENCE, f"Prefers {value}", "preference", "preference", value)

        match = re.match(r"i use (.+)", normalized)
        if match is not None:
            value = self._title_value(match.group(1))
            key = self._usage_key(value)
            return self._entry(MemoryType.PREFERENCE, f"Uses {value}", "preference", key, value)

        match = re.match(r"i switched to (.+)", normalized)
        if match is not None:
            value = self._title_value(match.group(1))
            return self._entry(
                MemoryType.PREFERENCE,
                f"Favorite browser = {value}",
                "preference",
                "favorite_browser",
                value,
            )
        return None

    def _personal_fact(self, normalized: str) -> MemoryEntry | None:
        patterns = (
            (r"i am (a |an )?(.+)", "Personal fact"),
            (r"i'm (a |an )?(.+)", "Personal fact"),
            (r"i live in (.+)", "Lives in"),
            (r"i work as (.+)", "Works as"),
            (r"i work at (.+)", "Works at"),
        )
        for pattern, label in patterns:
            match = re.match(pattern, normalized)
            if match is None:
                continue
            value = self._title_value(match.group(match.lastindex or 1))
            key = label.casefold().replace(" ", "_")
            content = f"{label} = {value}" if label != "Personal fact" else f"Personal fact = {value}"
            return self._entry(MemoryType.FACT, content, "fact", key, value)
        return None

    def _goal(self, normalized: str) -> MemoryEntry | None:
        patterns = (
            r"i want to (.+)",
            r"i'm building (.+)",
            r"i am building (.+)",
            r"i'm preparing for (.+)",
            r"i am preparing for (.+)",
            r"my project is (.+)",
        )
        for pattern in patterns:
            match = re.match(pattern, normalized)
            if match is not None:
                value = self._title_value(match.group(1))
                return self._entry(MemoryType.GOAL, f"Goal = {value}", "goal", "goal", value)
        return None

    def _note(self, normalized: str) -> MemoryEntry | None:
        if normalized.startswith(("always ", "don't ", "do not ", "respond ")):
            value = self._sentence_value(normalized)
            return self._entry(MemoryType.NOTE, value, "note", self._note_key(value), value)
        return None

    def _entry(
        self,
        memory_type: MemoryType,
        content: str,
        category: str,
        key: str,
        value: str,
    ) -> MemoryEntry:
        return MemoryEntry(
            type=memory_type,
            content=content,
            metadata={"category": category, "key": key, "value": value},
        )

    def _usage_key(self, value: str) -> str:
        normalized = value.casefold()
        if normalized in {"chrome", "firefox", "edge", "brave"}:
            return "favorite_browser"
        if normalized in {"vs code", "visual studio code", "pycharm", "vim"}:
            return "favorite_editor"
        return f"uses_{normalized.replace(' ', '_')}"

    def _note_key(self, value: str) -> str:
        return f"note_{self.rules.normalize(value).replace(' ', '_')}"

    def _title_value(self, value: str) -> str:
        words = value.strip().rstrip(".").split()
        return " ".join(word.upper() if word in {"ira", "vs"} else word.capitalize() for word in words)

    def _sentence_value(self, value: str) -> str:
        stripped = value.strip().rstrip(".")
        return stripped[:1].upper() + stripped[1:]
