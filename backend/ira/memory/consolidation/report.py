from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsolidationReport:
    duplicate_count: int
    updated_count: int
    kept_count: int
    changes: tuple[str, ...]

    def duplicates_removed(self) -> int:
        return self.duplicate_count

    def memories_updated(self) -> int:
        return self.updated_count

    def memories_kept(self) -> int:
        return self.kept_count

    def all_changes(self) -> list[str]:
        return list(self.changes)
