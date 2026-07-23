from ..plan import AgentPlan
from ..step import StepStatus
from .result import ReflectionResult, ReflectionStatus
from .reflection import Reflection

class ReflectionEngine:
    def analyze(self, plan: AgentPlan) -> Reflection:
        results = []
        for step in plan.steps:
            if step.status == StepStatus.COMPLETED:
                status = ReflectionStatus.SUCCESS
                summary = f"Completed: {step.action}"
                details = "Step executed successfully."
            elif step.status == StepStatus.FAILED:
                status = ReflectionStatus.FAILED
                summary = f"Failed: {step.action}"
                details = getattr(step, "error", "Execution failed.")
            elif step.status == StepStatus.SKIPPED:
                status = ReflectionStatus.SKIPPED
                summary = f"Skipped: {step.action}"
                details = "Dependency was not satisfied."
            else:
                status = ReflectionStatus.UNKNOWN
                summary = f"Unknown: {step.action}"
                details = "Execution status unknown."
                
            results.append(ReflectionResult(
                step_id=step.id,
                status=status,
                summary=summary,
                details=details
            ))
            
        return Reflection(plan_id=plan.id, results=results)
