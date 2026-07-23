from __future__ import annotations

from backend.ira.memory.long_term import MemoryEntry, MemoryStore

from .report import ConsolidationReport
from .rules import ConsolidationRules


class MemoryConsolidator:
    def __init__(self, rules: ConsolidationRules | None = None) -> None:
        self.rules = rules or ConsolidationRules()

    def consolidate(self, store: MemoryStore) -> ConsolidationReport:
        groups: dict[str, list[MemoryEntry]] = {}
        for memory in store.all():
            groups.setdefault(self.rules.consolidation_key(memory), []).append(memory)

        duplicates_removed = 0
        memories_updated = 0
        changes: list[str] = []
        kept: list[MemoryEntry] = []
        removed_ids: set[str] = set()

        for key, memories in groups.items():
            newest = max(memories, key=lambda memory: memory.updated_at)
            canonical_content = self.rules.canonical_content(newest)
            canonical_metadata = self.rules.normalized_metadata(newest)

            for memory in memories:
                if memory.id == newest.id:
                    continue
                removed_ids.add(memory.id)
                if self._has_newer_equivalent(memory, memories):
                    duplicates_removed += 1
                    changes.append(f"Removed duplicate memory {memory.id} for {key}.")
                elif self.rules.conflicts(newest, memory):
                    memories_updated += 1
                    changes.append(f"Removed outdated memory {memory.id} for {key}.")
                else:
                    duplicates_removed += 1
                    changes.append(f"Merged equivalent memory {memory.id} into {newest.id}.")

            if newest.content != canonical_content or newest.metadata != canonical_metadata:
                newest.content = canonical_content
                newest.metadata = canonical_metadata
                memories_updated += 1
                changes.append(f"Canonicalized memory {newest.id} for {key}.")
            kept.append(newest)

        for memory_id in removed_ids:
            store.remove(memory_id)
        for memory in kept:
            store.add(memory)

        return ConsolidationReport(
            duplicate_count=duplicates_removed,
            updated_count=memories_updated,
            kept_count=len(kept),
            changes=tuple(changes),
        )

    def _has_newer_equivalent(self, memory: MemoryEntry, memories: list[MemoryEntry]) -> bool:
        return any(
            other.id != memory.id
            and self.rules.equivalent(memory, other)
            and other.updated_at > memory.updated_at
            for other in memories
        )
