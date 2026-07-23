from ira.planner.planner import TaskPlanner
from .goal import Goal

class GoalPlanner:
    def __init__(self) -> None:
        self._task_planner = TaskPlanner()

    def plan(self, goal: str) -> Goal:
        tasks = self._task_planner.plan(goal)
        return Goal(description=goal.strip(), tasks=tasks)
