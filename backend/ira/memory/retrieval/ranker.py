from __future__ import annotations

import re
from datetime import datetime, timezone

from backend.ira.memory.long_term import MemoryEntry, MemoryType


class MemoryRanker:
    _TYPE_KEYWORDS = {
        MemoryType.PREFERENCE: {"preference", "preferences", "prefer", "preferred"},
        MemoryType.FACT: {"fact", "facts", "personal"},
        MemoryType.GOAL: {"goal", "goals"},
        MemoryType.NOTE: {"note", "notes", "instruction", "instructions"},
    }

    def rank(self, query: str, memories: list[MemoryEntry]) -> list[MemoryEntry]:
        query_tokens = self._tokens(query)
        if not query_tokens:
            return []

        scored = [
            (self._score(query, query_tokens, memory), index, memory)
            for index, memory in enumerate(memories)
        ]
        matched = [(score, index, memory) for score, index, memory in scored if score > 0]
        matched.sort(key=lambda item: (-item[0], item[1]))
        return [memory for _, _, memory in matched]

    def _score(self, query: str, query_tokens: set[str], memory: MemoryEntry) -> float:
        content = self._normalize(memory.content)
        metadata_text = self._metadata_text(memory.metadata)
        metadata = self._normalize(metadata_text)
        score = 0.0

        for token in query_tokens:
            if self._whole_word(token, content):
                score += 10
            elif token in content:
                score += 3

            if self._whole_word(token, metadata):
                score += 8
            elif token in metadata:
                score += 2

        content_tokens = self._tokens(memory.content)
        metadata_tokens = self._tokens(metadata_text)
        if query_tokens & self._TYPE_KEYWORDS.get(memory.type, set()):
            score += 4
        if query_tokens & metadata_tokens:
            score += 6
        if query_tokens & content_tokens:
            score += 2

        if score > 0:
            score += self._recency_bonus(memory)
        return score

    def _metadata_text(self, metadata: dict[str, object]) -> str:
        return " ".join(str(value) for value in metadata.values())

    def _tokens(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", self._normalize(text))
            if len(token) > 1
        }

    def _whole_word(self, token: str, text: str) -> bool:
        return re.search(rf"\b{re.escape(token)}\b", text) is not None

    def _normalize(self, text: object) -> str:
        return " ".join(str(text).casefold().split())

    def _recency_bonus(self, memory: MemoryEntry) -> float:
        timestamp = memory.updated_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
        if age.days <= 1:
            return 1.0
        if age.days <= 30:
            return 0.5
        return 0.1
