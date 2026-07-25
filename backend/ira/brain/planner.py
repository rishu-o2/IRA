from __future__ import annotations

from typing import Any

from .models import BrainIntent, BrainPlan


class BrainPlanner:
    """Adapter around the current agent planner."""

    def __init__(self, agent_planner: Any) -> None:
        self._agent_planner = agent_planner

    def plan(self, intent: BrainIntent) -> BrainPlan:
        raw_plan = self._agent_planner.plan(intent.message)
        steps = getattr(raw_plan, "steps", ())
        return BrainPlan(raw_plan=raw_plan, is_multi_step=len(steps) > 1)
