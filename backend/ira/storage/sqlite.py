from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .migrations import apply_migrations


def default_database_path() -> Path:
    configured = os.environ.get("IRA_MEMORY_DB")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[1] / "data" / "ira_memory.sqlite3"


class SQLiteStorage:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            apply_migrations(connection)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
