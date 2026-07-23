from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .memory import MemoryEntry, MemoryType


class MemoryStorage:
    def __init__(self, path: str):
        self.path = Path(path)

    def save(self, entries: list[MemoryEntry]) -> None:
        records = [self._entry_to_record(entry) for entry in entries]
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=self.path.parent,
            encoding="utf-8",
        ) as temp_file:
            json.dump(records, temp_file, indent=2)
            temp_file.write("\n")
            temp_path = temp_file.name

        os.replace(temp_path, self.path)

    def load(self) -> list[MemoryEntry]:
        if not self.path.exists():
            return []

        try:
            with self.path.open("r", encoding="utf-8") as memory_file:
                records = json.load(memory_file)
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(records, list):
            return []

        entries: list[MemoryEntry] = []
        for record in records:
            if not isinstance(record, dict):
                return []
            try:
                entries.append(self._record_to_entry(record))
            except (KeyError, TypeError, ValueError):
                return []
        return entries

    def _entry_to_record(self, entry: MemoryEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "type": entry.type.name,
            "content": entry.content,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "metadata": entry.metadata,
        }

    def _record_to_entry(self, record: dict[str, Any]) -> MemoryEntry:
        return MemoryEntry(
            id=record["id"],
            type=MemoryType[record["type"]],
            content=record["content"],
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
            metadata=record["metadata"],
        )
