from __future__ import annotations

from .memory import MemoryEntry
from .storage import MemoryStorage


class MemoryStore:
    def __init__(self, storage: MemoryStorage | None = None) -> None:
        self._storage = storage
        self._entries: dict[str, MemoryEntry] = {}
        if self._storage is not None:
            self._entries = {entry.id: entry for entry in self._storage.load()}

    def add(self, entry: MemoryEntry) -> None:
        self._entries[entry.id] = entry
        self._save()

    def get(self, memory_id: str) -> MemoryEntry | None:
        return self._entries.get(memory_id)

    def all(self) -> list[MemoryEntry]:
        return list(self._entries.values())

    def remove(self, memory_id: str) -> None:
        self._entries.pop(memory_id, None)
        self._save()

    def clear(self) -> None:
        self._entries.clear()
        self._save()

    def search(self, query: str) -> list[MemoryEntry]:
        normalized_query = query.casefold()
        if not normalized_query:
            return []
        return [
            entry
            for entry in self._entries.values()
            if normalized_query in entry.content.casefold()
        ]

    def _save(self) -> None:
        if self._storage is not None:
            self._storage.save(self.all())
