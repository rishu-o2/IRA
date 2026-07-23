from datetime import datetime, timezone
from .goal import Goal, GoalStatus
from .planner import GoalPlanner

class GoalManager:
    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}
        self._planner = GoalPlanner()

    def create(self, goal_text: str) -> Goal:
        goal = self._planner.plan(goal_text)
        self._goals[goal.id] = goal
        return goal

    def get(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def all(self) -> list[Goal]:
        return list(self._goals.values())

    def delete(self, goal_id: str) -> None:
        if goal_id in self._goals:
            del self._goals[goal_id]

    def clear(self) -> None:
        self._goals.clear()

    def start(self, goal_id: str) -> None:
        goal = self.get(goal_id)
        if goal and goal.status == GoalStatus.PENDING:
            goal.status = GoalStatus.RUNNING
            goal.started_at = datetime.now(timezone.utc)

    def complete(self, goal_id: str) -> None:
        goal = self.get(goal_id)
        if goal and goal.status == GoalStatus.RUNNING:
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(timezone.utc)

    def fail(self, goal_id: str, reason: str) -> None:
        goal = self.get(goal_id)
        if goal:
            goal.status = GoalStatus.FAILED
            goal.error = reason
