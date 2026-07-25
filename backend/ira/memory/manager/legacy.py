from __future__ import annotations

from datetime import datetime, timezone

from ..long_term import MemoryEntry, MemoryStore

from .extractor import MemoryExtractor
from .rules import MemoryRules


class LegacyMemoryManager:
    def __init__(
        self,
        store: MemoryStore,
        extractor: MemoryExtractor | None = None,
        rules: MemoryRules | None = None,
    ) -> None:
        self.store = store
        self.rules = rules or MemoryRules()
        self.extractor = extractor or MemoryExtractor(self.rules)

    def remember(self, text: str) -> list[MemoryEntry]:
        remembered: list[MemoryEntry] = []
        for candidate in self.extract(text):
            existing = self._find_existing(candidate)
            if existing is None:
                self.store.add(candidate)
                remembered.append(candidate)
            elif self._changed(existing, candidate):
                existing.content = candidate.content
                existing.type = candidate.type
                existing.metadata = candidate.metadata
                existing.updated_at = datetime.now(timezone.utc)
                self.store.add(existing)
                remembered.append(existing)
        return remembered

    def forget(self, query: str) -> list[MemoryEntry]:
        if not query.strip():
            return []

        removed: list[MemoryEntry] = []
        normalized_query = self.rules.normalize(query)
        for entry in list(self.store.all()):
            haystack = " ".join(
                [
                    entry.content,
                    str(entry.metadata.get("category", "")),
                    str(entry.metadata.get("key", "")),
                    str(entry.metadata.get("value", "")),
                ]
            ).casefold()
            natural_haystack = self.rules.normalize(haystack.replace("_", " "))
            if normalized_query in haystack or normalized_query in natural_haystack:
                self.store.remove(entry.id)
                removed.append(entry)
        return removed

    def should_remember(self, text: str) -> bool:
        return self.rules.should_remember(text)

    def extract(self, text: str) -> list[MemoryEntry]:
        return self.extractor.extract(text)

    def _find_existing(self, candidate: MemoryEntry) -> MemoryEntry | None:
        candidate_key = candidate.metadata.get("key")
        for entry in self.store.all():
            if entry.metadata.get("key") == candidate_key:
                return entry
            if entry.content.casefold() == candidate.content.casefold():
                return entry
        return None

    def _changed(self, existing: MemoryEntry, candidate: MemoryEntry) -> bool:
        return (
            existing.content != candidate.content
            or existing.type != candidate.type
            or existing.metadata != candidate.metadata
        )
