from __future__ import annotations

from typing import Any

from ..execution.result import StepExecutionResult, ExecutionStatus
from .strategies import (
    RecoveryStrategy,
    AppRecovery,
    WebsiteRecovery,
    FilesystemRecovery,
)
from ..tools import ToolRequest
from ..pipeline_log import pipeline_log


class RecoveryEngine:
    """Orchestrates deterministic recovery attempts using predefined strategies."""

    def __init__(self, tool_router: Any, learning_engine: Any = None) -> None:
        self._tool_router = tool_router
        self._learning = learning_engine
        self._strategies: list[RecoveryStrategy] = [
            AppRecovery(),
            WebsiteRecovery(),
            FilesystemRecovery(),
        ]

    def attempt_recovery(self, tool_name: str, parameters: dict[str, Any]) -> StepExecutionResult | None:
        """
        Queries the learned preferences first, then fallbacks to deterministic strategies.
        """
        # 1. Query Learned Preference (via LearningEngine)
        if self._learning:
            rec = self._learning.recommend(tool_name, parameters)
            if rec:
                pipeline_log("Recovery", f"Trying learned preference for {tool_name}: {rec.preferred_parameters}")
                request = ToolRequest(
                    intent=tool_name,
                    command="",
                    params=rec.preferred_parameters
                )
                try:
                    result = self._tool_router.execute(request)
                    pipeline_log("Recovery", f"Learned preference recovery successful: {rec.preferred_parameters}")
                    return StepExecutionResult(
                        status=ExecutionStatus.RECOVERED,
                        tool=tool_name,
                        attempt=1,
                        output=result.text if hasattr(result, "text") else str(result),
                        metadata={"recovered_parameters": rec.preferred_parameters}
                    )
                except Exception as exc:
                    pipeline_log("Recovery", f"Learned preference recovery failed: {exc}")

        # 2. Deterministic Recovery Chain
        for strategy in self._strategies:
            if strategy.can_recover(tool_name, parameters):
                fallbacks = strategy.generate_fallbacks(tool_name, parameters)
                
                for fallback_params in fallbacks:
                    pipeline_log("Recovery", f"Trying fallback for {tool_name}: {fallback_params}")
                    request = ToolRequest(
                        intent=tool_name,  # simplified, assuming intent mostly maps to tool_name for desktop tools
                        command="",
                        params=fallback_params
                    )
                    
                    try:
                        result = self._tool_router.execute(request)
                        # If we get here without exception, it succeeded
                        pipeline_log("Recovery", f"Fallback successful: {fallback_params}")
                        
                        return StepExecutionResult(
                            status=ExecutionStatus.RECOVERED,
                            tool=tool_name,
                            attempt=1,
                            output=result.text if hasattr(result, "text") else str(result),
                            metadata={"recovered_parameters": fallback_params}
                        )
                    except Exception as exc:
                        pipeline_log("Recovery", f"Fallback failed: {exc}")
                        continue
                
                # If we tried all fallbacks for a matching strategy and failed, stop
                break
                
        return None
