from ..planner import AgentPlanner
from ..executor import AgentExecutor
from ..reflection.engine import ReflectionEngine
from ..replanning.replanner import Replanner
from ..reflection.reflection import Reflection

class AgentController:
    def __init__(
        self,
        planner: AgentPlanner,
        executor: AgentExecutor,
        reflector: ReflectionEngine,
        replanner: Replanner,
        max_iterations: int = 3,
    ) -> None:
        self.planner = planner
        self.executor = executor
        self.reflector = reflector
        self.replanner = replanner
        self.max_iterations = max_iterations

    def run(self, goal: str) -> Reflection:
        plan = self.planner.plan(goal)
        
        if not plan.steps:
            return Reflection(plan_id=plan.id, results=[])
            
        iterations = 0
        latest_reflection = None
        
        while iterations < self.max_iterations:
            iterations += 1
            
            # Execute exactly one plan per iteration
            plan = self.executor.execute(plan)
            
            # ReflectionEngine analyzes every execution exactly once per iteration
            latest_reflection = self.reflector.analyze(plan)
            
            # Loop until Reflection.failed()==0 AND Reflection.skipped()==0
            if latest_reflection.failed() == 0 and latest_reflection.skipped() == 0:
                return latest_reflection
                
            # If max_iterations reached, stop and return latest reflection
            if iterations >= self.max_iterations:
                break
                
            # Replanner only executed if failed or skipped steps exist
            plan = self.replanner.replan(plan, latest_reflection)
            
            if not plan.steps:
                break
                
        return latest_reflection
