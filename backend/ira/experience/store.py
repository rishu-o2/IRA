from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ..storage.sqlite import SQLiteStorage
from .models import Experience, ExperienceOutcome, ExecutionPreference


class ExperienceStore:
    """SQLite-backed storage for experiences and learned execution preferences."""

    def __init__(self, storage: SQLiteStorage) -> None:
        self.storage = storage

    def record(self, experience: Experience) -> None:
        with self.storage.connect() as conn:
            conn.execute(
                """
                INSERT INTO experiences (
                    id, tool, intent, parameters, outcome, success,
                    execution_time, attempts, recovery_used, timestamp,
                    metadata, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experience.id,
                    experience.tool,
                    experience.intent,
                    json.dumps(experience.parameters),
                    experience.outcome.value,
                    1 if experience.success else 0,
                    experience.execution_time,
                    experience.attempts,
                    1 if experience.recovery_used else 0,
                    experience.timestamp.isoformat(),
                    json.dumps(experience.metadata),
                    experience.schema_version,
                ),
            )
            conn.commit()

    def history(self, limit: int = 100) -> list[Experience]:
        with self.storage.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM experiences ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_experience(row) for row in rows]

    def success_rate(self, tool: str, parameter_hash: str | None = None) -> float:
        """Returns success rate of a tool, optionally filtered by original parameter hash."""
        with self.storage.connect() as conn:
            if parameter_hash:
                # We need to compute success rate from experiences matching original parameters
                # In order to filter by parameter_hash, we can query experiences and match hashes.
                # Since we don't store parameter_hash in experiences table, we can load them or compute.
                # Alternatively, we can check execution_preferences which computes it, or query experiences.
                # Let's query experiences for the tool and do in-memory filtering.
                rows = conn.execute(
                    "SELECT parameters, success FROM experiences WHERE tool = ?", (tool,)
                ).fetchall()
                matching = 0
                successes = 0
                for row in rows:
                    params = json.loads(row["parameters"])
                    import hashlib
                    h = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
                    if h == parameter_hash:
                        matching += 1
                        if row["success"]:
                            successes += 1
                return successes / matching if matching > 0 else 0.0
            else:
                row = conn.execute(
                    "SELECT AVG(success) FROM experiences WHERE tool = ?", (tool,)
                ).fetchone()
                return row[0] if row and row[0] is not None else 0.0

    def last_success(self, tool: str) -> Experience | None:
        with self.storage.connect() as conn:
            row = conn.execute(
                "SELECT * FROM experiences WHERE tool = ? AND success = 1 ORDER BY timestamp DESC LIMIT 1",
                (tool,),
            ).fetchone()
            return self._row_to_experience(row) if row else None

    def last_failure(self, tool: str) -> Experience | None:
        with self.storage.connect() as conn:
            row = conn.execute(
                "SELECT * FROM experiences WHERE tool = ? AND success = 0 ORDER BY timestamp DESC LIMIT 1",
                (tool,),
            ).fetchone()
            return self._row_to_experience(row) if row else None

    def preferred_parameters(self, tool: str, parameter_hash: str) -> ExecutionPreference | None:
        with self.storage.connect() as conn:
            row = conn.execute(
                "SELECT * FROM execution_preferences WHERE tool = ? AND parameter_hash = ?",
                (tool, parameter_hash),
            ).fetchone()
            if not row:
                return None
            return ExecutionPreference(
                tool=row["tool"],
                parameter_hash=row["parameter_hash"],
                preferred_parameters=json.loads(row["preferred_parameters"]),
                confidence=row["confidence"],
                success_rate=row["success_rate"],
                last_used=datetime.fromisoformat(row["last_used"]),
            )

    def save_preference(self, pref: ExecutionPreference) -> None:
        with self.storage.connect() as conn:
            conn.execute(
                """
                INSERT INTO execution_preferences (
                    tool, parameter_hash, preferred_parameters, confidence, success_rate, last_used
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tool, parameter_hash) DO UPDATE SET
                    preferred_parameters = excluded.preferred_parameters,
                    confidence = excluded.confidence,
                    success_rate = excluded.success_rate,
                    last_used = excluded.last_used
                """,
                (
                    pref.tool,
                    pref.parameter_hash,
                    json.dumps(pref.preferred_parameters),
                    pref.confidence,
                    pref.success_rate,
                    pref.last_used.isoformat(),
                ),
            )
            conn.commit()

    def cleanup(self, max_records: int = 1000) -> None:
        with self.storage.connect() as conn:
            # Delete older experiences if count exceeds max_records
            conn.execute(
                """
                DELETE FROM experiences WHERE id NOT IN (
                    SELECT id FROM experiences ORDER BY timestamp DESC LIMIT ?
                )
                """,
                (max_records,),
            )
            conn.commit()

    def _row_to_experience(self, row: sqlite3.Row) -> Experience:
        return Experience(
            id=row["id"],
            tool=row["tool"],
            intent=row["intent"],
            parameters=json.loads(row["parameters"]),
            outcome=ExperienceOutcome(row["outcome"]),
            success=bool(row["success"]),
            execution_time=row["execution_time"],
            attempts=row["attempts"],
            recovery_used=bool(row["recovery_used"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            metadata=json.loads(row["metadata"]),
            schema_version=row["schema_version"],
        )
