from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List
import uuid
from .step import AgentStep, StepStatus

@dataclass
class AgentPlan:
    goal: str
    steps: List[AgentStep]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def completed(self) -> List[AgentStep]:
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    def pending(self) -> List[AgentStep]:
        return [s for s in self.steps if s.status == StepStatus.PENDING]

    def failed(self) -> List[AgentStep]:
        return [s for s in self.steps if s.status == StepStatus.FAILED]

    def ready(self) -> List[AgentStep]:
        return [s for s in self.steps if s.status == StepStatus.READY]

    def all(self) -> List[AgentStep]:
        return self.steps
