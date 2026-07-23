import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()

@dataclass
class Task:
    command: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
