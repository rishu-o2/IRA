import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto

class GoalStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    PAUSED = auto()

def _now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass
class Goal:
    description: str
    tasks: list[str]
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: GoalStatus = GoalStatus.PENDING
    created_at: datetime = field(default_factory=_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_task: int = 0
    error: str | None = None
