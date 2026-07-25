import pytest
import json

from ira.planning.models import (
    Goal, GoalStatus, Task, TaskStatus, Plan, ExecutionStep
)
from ira.planning.context import (
    PlanningContext, PlanningResult, ExecutionResult, GoalSnapshot
)
from ira.planning.goal_detector import GoalDetector
from ira.planning.planner import Planner
from ira.planning.monitor import ExecutionMonitor
from ira.planning.strategy import (
    SingleStepStrategy, MultiStepStrategy, ConversationStrategy,
    ResearchStrategy, LearningStrategy,
)
from ira.knowledge.models import KnowledgeGraph


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_context(request: str, goal: Goal | None = None) -> PlanningContext:
    if goal is None:
        goal = GoalDetector().detect(request)
    return PlanningContext(
        request=request,
        knowledge=KnowledgeGraph(),
        conversation_history=[],
        memory={},
        preferences={},
        current_goal=goal,
    )


# ── Goal model ───────────────────────────────────────────────────────────────

def test_goal_creation():
    goal = Goal(description="Prepare for interview")
    assert goal.description == "Prepare for interview"
    assert goal.status == GoalStatus.PENDING
    assert goal.priority == "MEDIUM"
    assert goal.confidence == 1.0


def test_goal_status_transition():
    goal = Goal(description="Test goal")
    goal.status = GoalStatus.ACTIVE
    assert goal.status == GoalStatus.ACTIVE
    goal.status = GoalStatus.COMPLETED
    assert goal.status == GoalStatus.COMPLETED


# ── Task model ───────────────────────────────────────────────────────────────

def test_task_creation():
    goal = Goal(description="Open browser and search")
    task = Task(
        goal_id=goal.id,
        description="Open browser",
        tool="desktop",
        parameters={"app": "chrome"},
    )
    assert task.status == TaskStatus.PENDING
    assert task.dependencies == []


# ── GoalDetector ────────────────────────────────────────────────────────────

def test_goal_detector_basic():
    detector = GoalDetector()
    goal = detector.detect("Prepare me for my interview")
    assert isinstance(goal, Goal)
    assert goal.status == GoalStatus.PENDING
    assert "interview" in goal.description.lower()


def test_goal_detector_urgent_priority():
    detector = GoalDetector()
    goal = detector.detect("Urgent: submit report asap")
    assert goal.priority == "CRITICAL"


def test_goal_detector_deadline_today():
    detector = GoalDetector()
    goal = detector.detect("Finish the report today")
    assert goal.deadline is not None


def test_goal_detector_deadline_tomorrow():
    detector = GoalDetector()
    goal = detector.detect("Do it tomorrow")
    assert goal.deadline is not None


# ── GoalSnapshot ─────────────────────────────────────────────────────────────

def test_goal_snapshot_creation():
    goal = Goal(description="Run tests")
    goal.status = GoalStatus.COMPLETED
    snapshot = GoalSnapshot.from_goal(goal, result_summary="All passed", duration=1.5)
    assert snapshot.goal_id == goal.id
    assert snapshot.status == GoalStatus.COMPLETED
    assert snapshot.result_summary == "All passed"
    assert snapshot.duration == 1.5
    assert snapshot.completed_time is not None


# ── Strategy selection ───────────────────────────────────────────────────────

def test_conversation_strategy_supports():
    strategy = ConversationStrategy()
    assert strategy.supports("Hello there")
    assert not strategy.supports("Open Chrome and search Python tutorials")


def test_research_strategy_supports():
    strategy = ResearchStrategy()
    assert strategy.supports("Research the best Python frameworks")
    assert strategy.supports("What is machine learning")


def test_learning_strategy_supports():
    strategy = LearningStrategy()
    assert strategy.supports("Teach me how to write tests")
    assert strategy.supports("How to use pytest")


def test_single_step_strategy_is_fallback():
    strategy = SingleStepStrategy()
    assert strategy.supports("anything at all")


def test_multi_step_strategy_detects_multi():
    strategy = MultiStepStrategy()
    assert strategy.supports("Open Chrome and then search Python")
    assert not strategy.supports("open chrome")


# ── Planner ───────────────────────────────────────────────────────────────────

def test_planner_selects_conversation_strategy():
    planner = Planner()
    ctx = _make_context("Hello, how are you?")
    result = planner.plan(ctx)
    assert result.strategy == "ConversationStrategy"
    assert isinstance(result.plan, Plan)


def test_planner_selects_multi_step_strategy():
    planner = Planner()
    ctx = _make_context("Open Chrome and then search Python tutorials")
    result = planner.plan(ctx)
    assert result.strategy == "MultiStepStrategy"
    assert result.plan.is_multi_step


def test_planner_selects_research_strategy():
    planner = Planner()
    ctx = _make_context("Research best Python web frameworks")
    result = planner.plan(ctx)
    assert result.strategy == "ResearchStrategy"


def test_planner_returns_planning_result():
    planner = Planner()
    ctx = _make_context("Do something")
    result = planner.plan(ctx)
    assert isinstance(result, PlanningResult)
    assert result.goal is ctx.current_goal
    assert result.confidence >= 0.0


# ── ExecutionMonitor ──────────────────────────────────────────────────────────

def test_monitor_initial_state():
    monitor = ExecutionMonitor()
    assert monitor.progress() == 0.0
    assert monitor.current_task() is None
    assert monitor.summary()["pending"] == 0


def test_monitor_progress_calculation():
    monitor = ExecutionMonitor()
    monitor.pending = ["t1", "t2"]
    monitor.completed = ["t3"]
    # 1 completed / 3 total = 0.333...
    assert abs(monitor.progress() - (1 / 3)) < 0.01


def test_monitor_current_task():
    monitor = ExecutionMonitor()
    monitor.running = ["task-42"]
    assert monitor.current_task() == "task-42"


def test_monitor_retrying_task():
    monitor = ExecutionMonitor()
    monitor.retrying = ["task-retry"]
    assert monitor.current_task() == "task-retry"


def test_monitor_summary_keys():
    monitor = ExecutionMonitor()
    summary = monitor.summary()
    for key in ["progress", "pending", "running", "paused", "retrying", "completed", "failed", "skipped", "cancelled"]:
        assert key in summary


# ── PlanningContext contract ─────────────────────────────────────────────────

def test_planning_context_holds_all_fields():
    goal = Goal(description="Test")
    ctx = PlanningContext(
        request="Do test",
        knowledge=KnowledgeGraph(),
        conversation=[{"role": "user", "content": "hi"}],
        memory={"key": "value"},
        preferences={"theme": "dark"},
        current_goal=goal,
    )
    assert ctx.request == "Do test"
    assert ctx.current_goal is goal
    assert ctx.preferences["theme"] == "dark"


# ── ExecutionResult ───────────────────────────────────────────────────────────

def test_execution_result_success():
    result = ExecutionResult(
        success=True,
        completed_tasks=["t1", "t2"],
        failed_tasks=[],
        summary="Done.",
        execution_time=0.5,
    )
    assert result.success
    assert len(result.completed_tasks) == 2
    assert result.execution_time == 0.5
