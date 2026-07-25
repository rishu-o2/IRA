"""
planning/strategy.py - Planning strategies.
"""
from __future__ import annotations

from typing import Protocol

from ..planner.planner import TaskPlanner as LegacyTaskPlanner
from .context import PlanningContext, PlanningResult
from .models import Plan, Task


class PlanningStrategy(Protocol):
    def supports(self, request: str) -> bool:
        ...

    def create_plan(self, context: PlanningContext) -> PlanningResult:
        ...


class SingleStepStrategy:
    def supports(self, request: str) -> bool:
        # Fallback strategy
        return True

    def create_plan(self, context: PlanningContext) -> PlanningResult:
        task = Task(
            goal_id=context.current_goal.id,
            description=context.request,
            tool="unknown",  # To be resolved by routing
            parameters={},
        )
        plan = Plan(tasks=[task], is_multi_step=False)
        return PlanningResult(
            goal=context.current_goal,
            plan=plan,
            strategy="SingleStepStrategy",
        )


class MultiStepStrategy:
    def __init__(self) -> None:
        self._legacy_planner = LegacyTaskPlanner()

    def supports(self, request: str) -> bool:
        # Check if legacy planner splits it into multiple tasks
        tasks = self._legacy_planner.plan(request)
        return len(tasks) > 1

    def create_plan(self, context: PlanningContext) -> PlanningResult:
        raw_tasks = self._legacy_planner.plan(context.request)
        tasks = []
        for raw in raw_tasks:
            tasks.append(Task(
                goal_id=context.current_goal.id,
                description=raw,
                tool="unknown",
                parameters={},
            ))
        plan = Plan(tasks=tasks, is_multi_step=True)
        return PlanningResult(
            goal=context.current_goal,
            plan=plan,
            strategy="MultiStepStrategy",
        )


class ResearchStrategy:
    def supports(self, request: str) -> bool:
        lowered = request.lower()
        return any(w in lowered for w in ["research", "find out", "who is", "what is", "search for"])

    def create_plan(self, context: PlanningContext) -> PlanningResult:
        plan = Plan()
        return PlanningResult(
            goal=context.current_goal,
            plan=plan,
            strategy="ResearchStrategy",
            confidence=0.5,
            missing_information=["needs external knowledge"],
        )


class LearningStrategy:
    def supports(self, request: str) -> bool:
        lowered = request.lower()
        return any(w in lowered for w in ["learn ", "teach me", "how to ", "tutorial on"])

    def create_plan(self, context: PlanningContext) -> PlanningResult:
        plan = Plan()
        return PlanningResult(
            goal=context.current_goal,
            plan=plan,
            strategy="LearningStrategy",
            confidence=0.5,
            missing_information=["needs external knowledge"],
        )


class ConversationStrategy:
    def supports(self, request: str) -> bool:
        lowered = request.lower()
        return any(w in lowered for w in ["hello", "hi", "how are you", "thanks"])

    def create_plan(self, context: PlanningContext) -> PlanningResult:
        task = Task(
            goal_id=context.current_goal.id,
            description=context.request,
            tool="conversation",
            parameters={},
        )
        plan = Plan(tasks=[task], is_multi_step=False)
        return PlanningResult(
            goal=context.current_goal,
            plan=plan,
            strategy="ConversationStrategy",
        )
