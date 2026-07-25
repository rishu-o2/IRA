"""
knowledge/store.py - SQLite storage operations for the Knowledge Graph.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ..storage import SQLiteStorage
from .models import (
    Context,
    Entity,
    EntityType,
    Importance,
    Relationship,
    RelationshipType,
)


class KnowledgeStore:
    def __init__(self, storage: SQLiteStorage) -> None:
        self.storage = storage

    def create_entity(self, entity: Entity) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.storage.connect() as conn:
            conn.execute(
                """
                INSERT INTO entities (
                    id, entity_type, name, category, importance, source, 
                    confidence, last_accessed, access_count, is_archived, 
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.entity_type.value,
                    entity.name,
                    entity.category,
                    entity.importance.value,
                    entity.source,
                    entity.confidence,
                    entity.last_accessed.isoformat() if entity.last_accessed else None,
                    entity.access_count,
                    1 if entity.is_archived else 0,
                    entity.created_at.isoformat(),
                    entity.updated_at.isoformat(),
                ),
            )
            for tag in entity.tags:
                conn.execute(
                    "INSERT INTO entity_tags (entity_id, tag) VALUES (?, ?)",
                    (entity.id, tag),
                )
            conn.commit()

    def update_entity(self, entity: Entity) -> None:
        entity.updated_at = datetime.now(timezone.utc)
        with self.storage.connect() as conn:
            conn.execute(
                """
                UPDATE entities SET
                    entity_type = ?, name = ?, category = ?, importance = ?,
                    source = ?, confidence = ?, last_accessed = ?, 
                    access_count = ?, is_archived = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    entity.entity_type.value,
                    entity.name,
                    entity.category,
                    entity.importance.value,
                    entity.source,
                    entity.confidence,
                    entity.last_accessed.isoformat() if entity.last_accessed else None,
                    entity.access_count,
                    1 if entity.is_archived else 0,
                    entity.updated_at.isoformat(),
                    entity.id,
                ),
            )
            conn.execute("DELETE FROM entity_tags WHERE entity_id = ?", (entity.id,))
            for tag in entity.tags:
                conn.execute(
                    "INSERT INTO entity_tags (entity_id, tag) VALUES (?, ?)",
                    (entity.id, tag),
                )
            conn.commit()

    def delete_entity(self, entity_id: str) -> bool:
        with self.storage.connect() as conn:
            cursor = conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
            conn.commit()
            return cursor.rowcount > 0

    def find_entity(self, entity_id: str) -> Entity | None:
        with self.storage.connect() as conn:
            row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
            if not row:
                return None
            return self._row_to_entity(row, conn)

    def find_entity_by_name(self, name: str) -> Entity | None:
        with self.storage.connect() as conn:
            row = conn.execute("SELECT * FROM entities WHERE name = ?", (name,)).fetchone()
            if not row:
                return None
            return self._row_to_entity(row, conn)

    def list_entities(self, limit: int = 100) -> list[Entity]:
        with self.storage.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM entities ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_entity(row, conn) for row in rows]

    def create_relationship(self, relationship: Relationship) -> None:
        with self.storage.connect() as conn:
            conn.execute(
                """
                INSERT INTO relationships (
                    id, source_entity, target_entity, relationship_type,
                    confidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relationship.id,
                    relationship.source_entity,
                    relationship.target_entity,
                    relationship.relationship_type.value,
                    relationship.confidence,
                    relationship.created_at.isoformat(),
                    relationship.updated_at.isoformat(),
                ),
            )
            conn.commit()

    def create_context(self, context: Context) -> None:
        with self.storage.connect() as conn:
            conn.execute(
                """
                INSERT INTO contexts (id, entity_id, conversation_id, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    context.id,
                    context.entity_id,
                    context.conversation_id,
                    context.timestamp.isoformat(),
                ),
            )
            conn.commit()

    def find_relationships(self, entity_id: str) -> list[Relationship]:
        with self.storage.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM relationships 
                WHERE source_entity = ? OR target_entity = ?
                """,
                (entity_id, entity_id),
            ).fetchall()
            return [self._row_to_relationship(row) for row in rows]

    def _row_to_entity(self, row: sqlite3.Row, conn: sqlite3.Connection) -> Entity:
        tags_rows = conn.execute(
            "SELECT tag FROM entity_tags WHERE entity_id = ?", (row["id"],)
        ).fetchall()
        tags = {t["tag"] for t in tags_rows}
        return Entity(
            id=row["id"],
            entity_type=EntityType(row["entity_type"]),
            name=row["name"],
            category=row["category"],
            importance=Importance(row["importance"]),
            source=row["source"],
            confidence=row["confidence"],
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
            access_count=row["access_count"],
            is_archived=bool(row["is_archived"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            tags=tags,
        )

    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        return Relationship(
            id=row["id"],
            source_entity=row["source_entity"],
            target_entity=row["target_entity"],
            relationship_type=RelationshipType(row["relationship_type"]),
            confidence=row["confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
