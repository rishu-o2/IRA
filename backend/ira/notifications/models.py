"""
notifications/models.py - Notification models.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid

class NotificationPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class Notification:
    title: str
    body: str
    priority: NotificationPriority
    device_id: str | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered: bool = False
