"""
planning/context.py - Contracts and interaction payloads between Brain, Planner, and Executor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..knowledge.models import KnowledgeGraph
from .models import Goal, GoalStatus, Plan


@dataclass
class PlanningContext:
    """The complete context passed from the Brain to the Planner."""
    request: str
    knowledge: KnowledgeGraph
    conversation: list[dict[str, Any]]
    memory: dict[str, str]
    preferences: dict[str, str]
    current_goal: Goal


@dataclass
class PlanningResult:
    """The result returned by the Planner."""
    goal: Goal
    plan: Plan
    strategy: str
    confidence: float = 1.0
    missing_information: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """The result returned by the ExecutionEngine."""
    success: bool
    completed_tasks: list[str] = field(default_factory=list)  # list of task IDs
    failed_tasks: list[str] = field(default_factory=list)
    summary: str = ""
    execution_time: float = 0.0


@dataclass
class GoalSnapshot:
    """A point-in-time representation of a Goal for persistence."""
    goal_id: str
    description: str
    status: GoalStatus
    completed_time: datetime | None = None
    result_summary: str = ""
    duration: float = 0.0

    @classmethod
    def from_goal(cls, goal: Goal, result_summary: str = "", duration: float = 0.0) -> GoalSnapshot:
        return cls(
            goal_id=goal.id,
            description=goal.description,
            status=goal.status,
            completed_time=datetime.now(timezone.utc) if goal.status == GoalStatus.COMPLETED else None,
            result_summary=result_summary,
            duration=duration,
        )
