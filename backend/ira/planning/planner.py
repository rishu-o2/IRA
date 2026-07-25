"""
planning/planner.py - The Planner coordinates strategies to build plans from contexts.
"""
from __future__ import annotations

from .context import PlanningContext, PlanningResult
from .strategy import (
    ConversationStrategy,
    LearningStrategy,
    MultiStepStrategy,
    PlanningStrategy,
    ResearchStrategy,
    SingleStepStrategy,
)


class Planner:
    """Consumes PlanningContext and returns a PlanningResult without executing tools."""

    def __init__(self, strategies: list[PlanningStrategy] | None = None) -> None:
        if strategies is None:
            self.strategies = [
                ConversationStrategy(),
                ResearchStrategy(),
                MultiStepStrategy(),
                LearningStrategy(),
                SingleStepStrategy(),
            ]
        else:
            self.strategies = strategies

    def plan(self, context: PlanningContext) -> PlanningResult:
        """Determines the best strategy and generates a plan."""
        best_strategy: PlanningStrategy | None = None
        for strategy in self.strategies:
            if strategy.supports(context.request):
                best_strategy = strategy
                break

        if best_strategy is None:
            # Fallback to SingleStepStrategy if somehow everything fails
            best_strategy = SingleStepStrategy()

        return best_strategy.create_plan(context)
