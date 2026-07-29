import pytest
from datetime import datetime, timezone
import json

from ira.storage.sqlite import SQLiteStorage
from ira.experience.store import ExperienceStore
from ira.experience.models import Experience, ExperienceOutcome, ExecutionPreference
from ira.learning.engine import LearningEngine
from ira.planning.executor import ExecutionEngine
from ira.tools import ToolRequest, ToolResult
from ira.planning.models import Task, Goal
from ira.planning.context import PlanningResult, Plan
from ira.reflection.engine import ReflectionEngine
from ira.execution.retry import RetryPolicy


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_experience.sqlite3"
    storage = SQLiteStorage(db_file)
    return storage


@pytest.fixture
def experience_store(temp_db):
    return ExperienceStore(temp_db)


@pytest.fixture
def learning_engine(experience_store):
    return LearningEngine(experience_store)


def test_experience_persistence(experience_store):
    exp = Experience(
        tool="open_app",
        intent="open chrome",
        parameters={"app_name": "chrome"},
        outcome=ExperienceOutcome.SUCCESS,
        success=True,
        execution_time=0.1,
        attempts=1,
        recovery_used=False
    )
    experience_store.record(exp)
    
    history = experience_store.history(limit=10)
    assert len(history) == 1
    assert history[0].tool == "open_app"
    assert history[0].parameters == {"app_name": "chrome"}
    assert history[0].outcome == ExperienceOutcome.SUCCESS
    assert history[0].success is True


def test_learning_confidence_formula(learning_engine, experience_store):
    # Base setup: we record experiences matching {"app_name": "chrome"}
    # 1 Success
    exp1 = Experience(
        tool="open_app",
        intent="open chrome",
        parameters={"app_name": "chrome"},
        outcome=ExperienceOutcome.SUCCESS,
        success=True,
        execution_time=0.1,
        attempts=1,
        recovery_used=False
    )
    experience_store.record(exp1)
    learning_engine.learn(exp1)
    
    # Check updated preference
    pref = experience_store.preferred_parameters("open_app", learning_engine.compute_hash({"app_name": "chrome"}))
    assert pref is not None
    # 1 Success - 0 Failure = 1 net. 1.0 - 0.75 ** 1 = 0.25
    assert pref.confidence == 0.25
    assert pref.success_rate == 1.0

    # Add 4 more successes (total 5)
    for _ in range(4):
        exp = Experience(
            tool="open_app",
            intent="open chrome",
            parameters={"app_name": "chrome"},
            outcome=ExperienceOutcome.SUCCESS,
            success=True,
            execution_time=0.1,
            attempts=1,
            recovery_used=False
        )
        experience_store.record(exp)
        learning_engine.learn(exp)
        
    pref = experience_store.preferred_parameters("open_app", learning_engine.compute_hash({"app_name": "chrome"}))
    # 5 Success - 0 Failure = 5 net. 1.0 - 0.75 ** 5 = 0.7627 (clamped to range, near 0.76)
    assert 0.76 <= pref.confidence <= 0.77
    
    # Add 1 failure
    fail_exp = Experience(
        tool="open_app",
        intent="open chrome",
        parameters={"app_name": "chrome"},
        outcome=ExperienceOutcome.FAILED,
        success=False,
        execution_time=0.1,
        attempts=1,
        recovery_used=False
    )
    experience_store.record(fail_exp)
    learning_engine.learn(fail_exp)
    
    pref = experience_store.preferred_parameters("open_app", learning_engine.compute_hash({"app_name": "chrome"}))
    # 5 Success - 1 Failure = 4 net. 1.0 - 0.75 ** 4 = 0.68359
    assert 0.68 <= pref.confidence <= 0.69
    assert pref.success_rate == 5 / 6


def test_learned_preference_selection(learning_engine, experience_store):
    # Set a learned preferred parameter config
    param_hash = learning_engine.compute_hash({"app_name": "chrome"})
    pref = ExecutionPreference(
        tool="open_app",
        parameter_hash=param_hash,
        preferred_parameters={"app_name": "google-chrome"},
        confidence=0.5,
        success_rate=0.8,
    )
    experience_store.save_preference(pref)
    
    # Query recommendation
    rec = learning_engine.recommend("open_app", {"app_name": "chrome"})
    assert rec is not None
    assert rec.preferred_parameters == {"app_name": "google-chrome"}
    
    # Zero/negative confidence shouldn't recommend
    pref_low = ExecutionPreference(
        tool="open_app",
        parameter_hash=param_hash,
        preferred_parameters={"app_name": "google-chrome"},
        confidence=0.0,
        success_rate=0.0,
    )
    experience_store.save_preference(pref_low)
    assert learning_engine.recommend("open_app", {"app_name": "chrome"}) is None


def test_recovery_using_learned_path(temp_db, experience_store, learning_engine):
    class MockToolRouter:
        def __init__(self):
            self.calls = []
        def execute(self, request: ToolRequest) -> ToolResult:
            self.calls.append(request)
            if request.params.get("app_name") == "google-chrome":
                return ToolResult("Opened Google Chrome")
            raise FileNotFoundError("App not found")

    router = MockToolRouter()
    
    # Save a learned preference: "chrome" -> "google-chrome"
    pref = ExecutionPreference(
        tool="open_app",
        parameter_hash=learning_engine.compute_hash({"app_name": "chrome"}),
        preferred_parameters={"app_name": "google-chrome"},
        confidence=0.75,
        success_rate=1.0,
    )
    experience_store.save_preference(pref)
    
    # ExecutionEngine setup
    exec_engine = ExecutionEngine(
        tool_router=router,
        experience_store=experience_store,
        learning_engine=learning_engine
    )
    
    task = Task(id="1", goal_id="g1", tool="open_app", parameters={"app_name": "chrome"}, description="open chrome")
    goal = Goal(id="g1", description="Open chrome")
    plan = Plan(tasks=[task])
    planning_res = PlanningResult(goal=goal, plan=plan, strategy="sequential")
    
    res = exec_engine.execute(planning_res)
    assert res.success is True
    assert task.result == "Opened Google Chrome"
    
    # Verify that executor bypassed initial "chrome" attempt and immediately tried "google-chrome"
    assert len(router.calls) == 1
    assert router.calls[0].params["app_name"] == "google-chrome"
