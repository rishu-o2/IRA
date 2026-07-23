from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List
import uuid

class StepStatus(Enum):
    PENDING = auto()
    READY = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()

@dataclass
class AgentStep:
    description: str
    action: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dependencies: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
