from __future__ import annotations

from ..execution.result import StepExecutionResult, ExecutionStatus
from .classifier import FailureClassifier, FailureCategory


class ReflectionEngine:
    """Deterministically evaluates execution results to decide next steps."""

    def evaluate(self, result: StepExecutionResult) -> None:
        """Evaluate the result in-place, updating its recoverable flag and metadata."""
        if result.status == ExecutionStatus.SUCCESS:
            result.recoverable = False
            result.metadata["lesson_learned"] = "No recovery needed. Tool executed successfully."
            result.metadata["confidence_delta"] = 0.25
            return

        if result.error:
            category = FailureClassifier.classify(result.error)
            result.metadata["failure_category"] = category.value
            
            # Determine recoverability based on category
            if category in (
                FailureCategory.NOT_FOUND, 
                FailureCategory.TIMEOUT, 
                FailureCategory.NETWORK
            ):
                result.recoverable = True
                result.metadata["lesson_learned"] = "Recovered using fallback path."
                result.metadata["reason"] = "Original target failed but alternative succeeded."
                result.metadata["confidence_delta"] = 0.18
            elif category == FailureCategory.PERMISSION:
                result.recoverable = False
                result.metadata["lesson_learned"] = "Execution failed completely."
                result.metadata["reason"] = "All retry attempts and recovery fallbacks failed."
                result.metadata["confidence_delta"] = -0.25
            else:
                # Tool errors might be recoverable if we can fallback
                result.recoverable = True
                result.metadata["lesson_learned"] = "Recovered using fallback path."
                result.metadata["reason"] = "Original target failed but alternative succeeded."
                result.metadata["confidence_delta"] = 0.18
        else:
            # If failed but no error attached, assume non-recoverable
            result.recoverable = False
            result.metadata["lesson_learned"] = "Execution failed completely."
            result.metadata["reason"] = "All retry attempts and recovery fallbacks failed."
            result.metadata["confidence_delta"] = -0.25

    def should_retry(self, result: StepExecutionResult) -> bool:
        """Returns True if the failure is transient and might succeed on retry."""
        if result.status == ExecutionStatus.SUCCESS:
            return False
            
        category_val = result.metadata.get("failure_category")
        return category_val in (
            FailureCategory.TIMEOUT.value,
            FailureCategory.NETWORK.value,
        )

    def should_recover(self, result: StepExecutionResult) -> bool:
        """Returns True if a structural recovery strategy is needed (e.g. NOT_FOUND)."""
        if result.status == ExecutionStatus.SUCCESS:
            return False
            
        category_val = result.metadata.get("failure_category")
        return category_val in (
            FailureCategory.NOT_FOUND.value,
            FailureCategory.TOOL_ERROR.value,
        ) and result.recoverable

    def needs_user(self, result: StepExecutionResult) -> bool:
        """Returns True if the failure is unrecoverable and requires user intervention."""
        return result.status == ExecutionStatus.FAILED and not result.recoverable

    def reflection_summary(self, result: StepExecutionResult) -> str:
        """Generates a brief summary of the reflection outcome."""
        if result.status == ExecutionStatus.SUCCESS:
            return "Execution succeeded."
        
        category = result.metadata.get("failure_category", "UNKNOWN")
        if self.should_retry(result):
            return f"Transient failure ({category}). Eligible for retry."
        if self.should_recover(result):
            return f"Structural failure ({category}). Eligible for recovery."
        
        return f"Unrecoverable failure ({category}). Needs user intervention."
