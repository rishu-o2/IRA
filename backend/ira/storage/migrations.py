from __future__ import annotations

import sqlite3


MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS memories (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_memories_category
        ON memories(category);
        """,
    ),
    (
        2,
        """
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            importance TEXT DEFAULT 'MEDIUM',
            source TEXT,
            confidence REAL DEFAULT 1.0,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            source_entity TEXT NOT NULL,
            target_entity TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(source_entity) REFERENCES entities(id) ON DELETE CASCADE,
            FOREIGN KEY(target_entity) REFERENCES entities(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS entity_tags (
            entity_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE,
            PRIMARY KEY(entity_id, tag)
        );

        CREATE TABLE IF NOT EXISTS contexts (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            conversation_id TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
        CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_entity);
        CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_entity);
        """,
    ),
)


def apply_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        row[0]
        for row in connection.execute("SELECT version FROM schema_migrations")
    }

    for version, sql in MIGRATIONS:
        if version in applied:
            continue
        connection.executescript(sql)
        connection.execute(
            "INSERT INTO schema_migrations(version) VALUES (?)",
            (version,),
        )

    connection.commit()
