from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timezone

class ReflectionStatus(Enum):
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()
    UNKNOWN = auto()

@dataclass
class ReflectionResult:
    step_id: str
    status: ReflectionStatus
    summary: str
    details: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
