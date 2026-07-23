from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from uuid import uuid4


class MemoryType(Enum):
    CONVERSATION = auto()
    FACT = auto()
    PREFERENCE = auto()
    GOAL = auto()
    NOTE = auto()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MemoryEntry:
    type: MemoryType
    content: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    metadata: dict[str, object] = field(default_factory=dict)
