"""
sync/models.py - Sync layer data models.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

class SyncEventType(str, Enum):
    MEMORY = "MEMORY"
    GOAL = "GOAL"
    PREFERENCE = "PREFERENCE"
    KNOWLEDGE = "KNOWLEDGE"
    TASK = "TASK"

@dataclass
class SyncRecord:
    event_type: SyncEventType
    device_id: str
    payload: dict[str, Any]
    version: int = 1
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    synced: bool = False
