from typing import Callable, Any
from .plan import AgentPlan
from .step import AgentStep, StepStatus

class AgentExecutor:
    def __init__(self, handler: Callable[[str], Any]) -> None:
        self._handler = handler

    def execute(self, plan: AgentPlan) -> AgentPlan:
        for step in plan.steps:
            # If step is PENDING, we could transition it to READY conceptually
            # But the requirement says "Allowed transitions only READY->RUNNING..."
            # So let's make it READY if it's PENDING
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.READY

            if not self._dependencies_completed(step, plan):
                step.status = StepStatus.SKIPPED
                continue

            step.status = StepStatus.RUNNING
            try:
                self._handler(step.action)
                step.status = StepStatus.COMPLETED
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)

        return plan

    def _dependencies_completed(self, step: AgentStep, plan: AgentPlan) -> bool:
        for dep_id in step.dependencies:
            dep_step = next((s for s in plan.steps if s.id == dep_id), None)
            if not dep_step or dep_step.status != StepStatus.COMPLETED:
                return False
        return True
