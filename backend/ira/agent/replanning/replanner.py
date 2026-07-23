from typing import Dict, List
import uuid
from datetime import datetime, timezone

from ..plan import AgentPlan
from ..step import AgentStep, StepStatus
from ..reflection.reflection import Reflection
from ..reflection.result import ReflectionStatus

class Replanner:
    def replan(self, plan: AgentPlan, reflection: Reflection) -> AgentPlan:
        new_steps: List[AgentStep] = []
        id_map: Dict[str, str] = {}
        
        for step in plan.steps:
            # Find the reflection result for this step
            ref_result = next((r for r in reflection.results if r.step_id == step.id), None)
            
            # Keep steps that didn't succeed (FAILED, SKIPPED, UNKNOWN) or missing reflection
            if not ref_result or ref_result.status != ReflectionStatus.SUCCESS:
                new_id = str(uuid.uuid4())
                id_map[step.id] = new_id
                
                # Copy dependencies but only those that are also in the new plan
                new_deps = []
                for dep in step.dependencies:
                    if dep in id_map:
                        new_deps.append(id_map[dep])
                        
                new_step = AgentStep(
                    id=new_id,
                    description=step.description,
                    action=step.action,
                    dependencies=new_deps,
                    status=StepStatus.PENDING
                )
                
                new_steps.append(new_step)
                
        new_plan = AgentPlan(
            goal=plan.goal,
            steps=new_steps,
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc)
        )
        return new_plan
