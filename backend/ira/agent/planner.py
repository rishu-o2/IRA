from ..goals.planner import GoalPlanner
from .step import AgentStep
from .plan import AgentPlan

class AgentPlanner:
    def __init__(self) -> None:
        self._goal_planner = GoalPlanner()

    def plan(self, goal: str) -> AgentPlan:
        # Use existing GoalPlanner to extract atomic tasks
        goal_obj = self._goal_planner.plan(goal)
        
        steps = []
        prev_step_id = None
        for task in goal_obj.tasks:
            deps = [prev_step_id] if prev_step_id else []
            step = AgentStep(
                description=task,
                action=task,
                dependencies=deps
            )
            steps.append(step)
            prev_step_id = step.id
            
        return AgentPlan(goal=goal_obj.description, steps=steps)
