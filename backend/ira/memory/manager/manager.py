from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ...storage import SQLiteStorage
from ..models import MemoryRecord

from ...knowledge.service import KnowledgeService


class MemoryManager:
    def __init__(
        self, 
        database_path: str | Path | None = None, 
        storage: SQLiteStorage | None = None,
        knowledge_service: KnowledgeService | None = None,
    ) -> None:
        self.storage = storage or SQLiteStorage(database_path)
        self.knowledge_service = knowledge_service

    def remember(self, key: str, value: str, category: str) -> MemoryRecord:
        clean_key = self._clean("key", key)
        clean_value = self._clean("value", value)
        clean_category = self._clean("category", category)
        now = datetime.now(timezone.utc).isoformat()

        with self.storage.connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM memories WHERE key = ?",
                (clean_key,),
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            connection.execute(
                """
                INSERT INTO memories(key, value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = excluded.updated_at
                """,
                (clean_key, clean_value, clean_category, created_at, now),
            )
            connection.commit()

        # Fire and forget knowledge processing (or synchronous block)
        if self.knowledge_service:
            try:
                self.knowledge_service.process(clean_value)
            except Exception as e:
                print(f"[KnowledgeService] Failed to extract knowledge from '{clean_value}': {e}")

        recalled = self._get_record(clean_key)
        if recalled is None:
            raise RuntimeError(f"Memory was not persisted: {clean_key}")
        return recalled

    def recall(self, key: str) -> str | None:
        clean_key = key.strip()
        if not clean_key:
            return None
        record = self._get_record(clean_key)
        return record.value if record is not None else None

    def search(self, query: str) -> list[MemoryRecord]:
        clean_query = query.strip()
        if not clean_query:
            return []
        like_query = f"%{clean_query}%"
        with self.storage.connect() as connection:
            rows = connection.execute(
                """
                SELECT key, value, category, created_at, updated_at
                FROM memories
                WHERE key LIKE ? OR value LIKE ? OR category LIKE ?
                ORDER BY updated_at DESC, key ASC
                """,
                (like_query, like_query, like_query),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def forget(self, key: str) -> bool:
        clean_key = key.strip()
        if not clean_key:
            return False
        with self.storage.connect() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE key = ?", (clean_key,))
            connection.commit()
            return cursor.rowcount > 0

    def _get_record(self, key: str) -> MemoryRecord | None:
        with self.storage.connect() as connection:
            row = connection.execute(
                """
                SELECT key, value, category, created_at, updated_at
                FROM memories
                WHERE key = ?
                """,
                (key,),
            ).fetchone()
        return self._row_to_record(row) if row is not None else None

    def _row_to_record(self, row) -> MemoryRecord:
        return MemoryRecord(
            key=row["key"],
            value=row["value"],
            category=row["category"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _clean(self, field: str, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError(f"Memory {field} cannot be empty.")
        return clean_value
