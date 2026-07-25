"""
events/models.py - Event Bus data models.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

class EventType(str, Enum):
    MEMORY_CREATED = "MEMORY_CREATED"
    GOAL_CREATED = "GOAL_CREATED"
    GOAL_COMPLETED = "GOAL_COMPLETED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    DEVICE_CONNECTED = "DEVICE_CONNECTED"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    KNOWLEDGE_UPDATED = "KNOWLEDGE_UPDATED"

@dataclass
class IRAEvent:
    event_type: EventType | str
    payload: dict[str, Any]
    source_device_id: str | None = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
