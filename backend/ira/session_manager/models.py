"""
session_manager/models.py - Session models.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    EXPIRED = "EXPIRED"

@dataclass
class IRASession:
    device_id: str
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: SessionStatus = SessionStatus.ACTIVE
    conversation_context: list[dict[str, Any]] = field(default_factory=list)
    active_goal_id: str | None = None
    active_plan_id: str | None = None
    active_execution_id: str | None = None
    execution_state: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
