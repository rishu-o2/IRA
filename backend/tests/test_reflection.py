import pytest

from ira.reflection.classifier import FailureClassifier, FailureCategory
from ira.reflection.engine import ReflectionEngine
from ira.execution.result import StepExecutionResult, ExecutionStatus
from ira.recovery.strategies import AppRecovery, WebsiteRecovery, FilesystemRecovery
from ira.recovery.engine import RecoveryEngine
from ira.tools import ToolRequest, ToolResult
from ira.actions import ActionError


def test_failure_classifier():
    assert FailureClassifier.classify(FileNotFoundError()) == FailureCategory.NOT_FOUND
    assert FailureClassifier.classify(PermissionError()) == FailureCategory.PERMISSION
    assert FailureClassifier.classify(TimeoutError()) == FailureCategory.TIMEOUT
    assert FailureClassifier.classify(ConnectionError()) == FailureCategory.NETWORK
    
    action_err_not_found = ActionError("I could not find the file.")
    assert FailureClassifier.classify(action_err_not_found) == FailureCategory.NOT_FOUND
    
    action_err_generic = ActionError("Something broke.")
    assert FailureClassifier.classify(action_err_generic) == FailureCategory.TOOL_ERROR


def test_reflection_engine_transient():
    engine = ReflectionEngine()
    result = StepExecutionResult(status=ExecutionStatus.FAILED, tool="search_web", attempt=1, error=TimeoutError())
    
    engine.evaluate(result)
    assert result.recoverable is True
    assert engine.should_retry(result) is True
    assert engine.should_recover(result) is False


def test_reflection_engine_structural():
    engine = ReflectionEngine()
    result = StepExecutionResult(status=ExecutionStatus.FAILED, tool="open_app", attempt=1, error=FileNotFoundError())
    
    engine.evaluate(result)
    assert result.recoverable is True
    assert engine.should_retry(result) is False
    assert engine.should_recover(result) is True


def test_reflection_engine_unrecoverable():
    engine = ReflectionEngine()
    result = StepExecutionResult(status=ExecutionStatus.FAILED, tool="delete", attempt=1, error=PermissionError())
    
    engine.evaluate(result)
    assert result.recoverable is False
    assert engine.should_retry(result) is False
    assert engine.should_recover(result) is False
    assert engine.needs_user(result) is True


def test_recovery_engine_integration():
    class MockToolRouter:
        def execute(self, request: ToolRequest) -> ToolResult:
            if "google-chrome" in request.params.get("app_name", ""):
                return ToolResult("Opened Google Chrome")
            raise FileNotFoundError("Mock fail")

    router = MockToolRouter()
    recovery = RecoveryEngine(tool_router=router)
    
    # "chrome" will fail first, but the recovery engine tries "google-chrome" next
    result = recovery.attempt_recovery("open_app", {"app_name": "chrome"})
    
    assert result is not None
    assert result.status == ExecutionStatus.RECOVERED
    assert result.output == "Opened Google Chrome"
    assert result.metadata["recovered_parameters"]["app_name"] == "google-chrome"

def test_recovery_engine_exhaustion():
    class MockToolRouter:
        def execute(self, request: ToolRequest) -> ToolResult:
            raise FileNotFoundError("Mock fail forever")

    router = MockToolRouter()
    recovery = RecoveryEngine(tool_router=router)
    
    result = recovery.attempt_recovery("open_app", {"app_name": "fakeappxyz"})
    assert result is None
