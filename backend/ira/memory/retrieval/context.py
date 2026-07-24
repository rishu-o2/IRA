from __future__ import annotations

from dataclasses import dataclass

from ..long_term import MemoryEntry, MemoryType


@dataclass(frozen=True)
class Context:
    memories: tuple[MemoryEntry, ...]

    def all(self) -> list[MemoryEntry]:
        return list(self.memories)

    def preferences(self) -> list[MemoryEntry]:
        return self._of_type(MemoryType.PREFERENCE)

    def facts(self) -> list[MemoryEntry]:
        return self._of_type(MemoryType.FACT)

    def goals(self) -> list[MemoryEntry]:
        return self._of_type(MemoryType.GOAL)

    def notes(self) -> list[MemoryEntry]:
        return self._of_type(MemoryType.NOTE)

    def empty(self) -> bool:
        return not self.memories

    def _of_type(self, memory_type: MemoryType) -> list[MemoryEntry]:
        return [memory for memory in self.memories if memory.type == memory_type]
