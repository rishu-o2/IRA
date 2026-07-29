"""
planning/executor.py - ExecutionEngine that runs ExecutionSteps via the ToolRouter.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol

from .context import ExecutionResult, PlanningResult
from .models import ExecutionStep, GoalStatus, Task, TaskStatus
from .monitor import ExecutionMonitor

if TYPE_CHECKING:
    from ..tools import ToolRequest, ToolResult


class ToolRouterProtocol(Protocol):
    def execute(self, request: "ToolRequest") -> "ToolResult":
        ...


class ExecutionEngine:
    """Executes a PlanningResult sequentially through the ToolRouter.
    
    - Only communicates with ToolRouter (never calls tools directly).
    - Retries safe failures up to `max_retries` times.
    - Halts on critical/unrecoverable failures.
    """

    def __init__(
        self,
        tool_router: ToolRouterProtocol,
        max_retries: int = 2,
        reflection_engine: Any = None,
        retry_policy: Any = None,
        recovery_engine: Any = None,
        memory_writer: Any = None,
        experience_store: Any = None,
        learning_engine: Any = None,
    ) -> None:
        self._tool_router = tool_router
        self._max_retries = max_retries

        # Initialize new pipeline components
        from ..reflection.engine import ReflectionEngine
        from ..execution.retry import RetryPolicy
        from ..recovery.engine import RecoveryEngine

        self._learning = learning_engine
        self._experience_store = experience_store

        self._reflection = reflection_engine or ReflectionEngine()
        self._retry = retry_policy or RetryPolicy(max_attempts=max_retries)
        self._recovery = recovery_engine or RecoveryEngine(tool_router, learning_engine=self._learning)
        self._memory = memory_writer

    def execute(self, planning_result: PlanningResult) -> ExecutionResult:
        """Execute the plan and return an ExecutionResult."""
        from ..tools import ToolRequest

        monitor = ExecutionMonitor()
        plan = planning_result.plan
        start_time = time.monotonic()

        completed_tasks: list[str] = []
        failed_tasks: list[str] = []

        # Initialise monitor with pending tasks
        for task in plan.tasks:
            monitor.pending.append(task.id)

        for task in plan.tasks:
            # Skip tasks with unfulfilled dependencies
            unmet_deps = [d for d in task.dependencies if d not in completed_tasks]
            if unmet_deps:
                monitor.pending.remove(task.id)
                monitor.skipped.append(task.id)
                task.status = TaskStatus.CANCELLED
                continue

            # Move task from pending → running
            monitor.pending.remove(task.id)
            monitor.running.append(task.id)
            task.status = TaskStatus.RUNNING

            success = self._execute_task(task, monitor, ToolRequest)

            monitor.running.remove(task.id)

            if success:
                monitor.completed.append(task.id)
                completed_tasks.append(task.id)
                task.status = TaskStatus.COMPLETED
            else:
                monitor.failed.append(task.id)
                failed_tasks.append(task.id)
                task.status = TaskStatus.FAILED
                # Stop sequential execution on first failure
                # Mark all remaining pending as cancelled
                for remaining_id in list(monitor.pending):
                    monitor.pending.remove(remaining_id)
                    monitor.cancelled.append(remaining_id)
                break

        elapsed = time.monotonic() - start_time
        overall_success = len(failed_tasks) == 0

        # Update goal status
        goal = planning_result.goal
        goal.status = GoalStatus.COMPLETED if overall_success else GoalStatus.FAILED

        summary_parts = []
        if completed_tasks:
            summary_parts.append(f"Completed {len(completed_tasks)} task(s).")
        if failed_tasks:
            summary_parts.append(f"Failed {len(failed_tasks)} task(s).")
        summary = " ".join(summary_parts) or "No tasks were executed."

        return ExecutionResult(
            success=overall_success,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            summary=summary,
            execution_time=elapsed,
        )

    def _execute_task(
        self,
        task: Task,
        monitor: ExecutionMonitor,
        ToolRequest: type,
    ) -> bool:
        from ..execution.result import StepExecutionResult, ExecutionStatus
        from ..experience.models import Experience, ExperienceOutcome
        from ..pipeline_log import pipeline_log
        import json

        tool_name = task.tool or "desktop"
        parameters = task.parameters
        
        start_step_time = time.perf_counter()

        # Check for learned recommendation first
        if self._learning:
            rec = self._learning.recommend(tool_name, parameters)
            if rec:
                pipeline_log("Execution", f"Using learned preferred parameters for {tool_name}: {rec.preferred_parameters}")
                parameters = rec.preferred_parameters
        
        attempt = 0
        success = False
        recovery_used = False
        outcome = ExecutionStatus.FAILED
        metadata_dict = {}

        while attempt <= self._retry.max_attempts:
            attempt += 1
            request = ToolRequest(intent=tool_name, command=task.description, params=parameters)
            
            try:
                result = self._tool_router.execute(request)
                step_result = StepExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    tool=tool_name,
                    attempt=attempt,
                    output=result.text if hasattr(result, "text") else str(result)
                )
            except Exception as exc:
                step_result = StepExecutionResult(
                    status=ExecutionStatus.FAILED,
                    tool=tool_name,
                    attempt=attempt,
                    error=exc
                )

            # Reflection Phase
            self._reflection.evaluate(step_result)

            if step_result.status == ExecutionStatus.SUCCESS:
                task.result = step_result.output
                success = True
                outcome = ExecutionStatus.SUCCESS
                break

            # Retry Phase
            if self._reflection.should_retry(step_result) and self._retry.is_safe(tool_name):
                if attempt < self._retry.max_attempts:
                    pipeline_log("Execution", f"Retry attempt {attempt} for {tool_name}")
                    if task.id in monitor.running:
                        monitor.running.remove(task.id)
                    monitor.retrying.append(task.id)
                    self._retry.wait(attempt)
                    continue
                else:
                    pipeline_log("Execution", f"Retry exhausted for {tool_name}")

            # Recovery Phase
            if self._reflection.should_recover(step_result):
                pipeline_log("Execution", f"Attempting recovery for {tool_name}")
                recovery_result = self._recovery.attempt_recovery(tool_name, parameters)
                if recovery_result and recovery_result.status == ExecutionStatus.RECOVERED:
                    pipeline_log("Execution", f"Recovery succeeded for {tool_name}")
                    task.result = recovery_result.output
                    success = True
                    recovery_used = True
                    outcome = ExecutionStatus.RECOVERED
                    metadata_dict["recovered_parameters"] = recovery_result.metadata.get("recovered_parameters")
                    
                    # Memory Integration
                    if self._memory:
                        recovered_params = recovery_result.metadata.get("recovered_parameters")
                        if recovered_params:
                            try:
                                # Write successful recovered parameters to memory to avoid future failures
                                self._memory.remember(
                                    key=f"recovery_{tool_name}",
                                    value=json.dumps(recovered_params),
                                    category="preference"
                                )
                            except Exception as mem_exc:
                                pipeline_log("Memory", f"Failed to persist recovery: {mem_exc}")
                    break
                
            # If we exhausted retries and recovery failed (or wasn't attempted), we fail
            pipeline_log("Execution", f"Unrecoverable failure for {tool_name}")
            break

        if task.id in monitor.retrying:
            monitor.retrying.remove(task.id)

        # Experience Recording Phase
        elapsed_step_time = time.perf_counter() - start_step_time
        
        if outcome == ExecutionStatus.SUCCESS:
            exp_outcome = ExperienceOutcome.SUCCESS
        elif outcome == ExecutionStatus.RECOVERED:
            exp_outcome = ExperienceOutcome.RECOVERED
        else:
            exp_outcome = ExperienceOutcome.FAILED

        experience = Experience(
            tool=tool_name,
            intent=task.description,
            parameters=task.parameters,  # store original parameters requested
            outcome=exp_outcome,
            success=success,
            execution_time=elapsed_step_time,
            attempts=attempt,
            recovery_used=recovery_used,
            metadata=metadata_dict
        )

        if self._experience_store:
            try:
                self._experience_store.record(experience)
            except Exception as e:
                pipeline_log("Learning", f"Failed to record experience: {e}")

        if self._learning:
            try:
                self._learning.learn(experience)
            except Exception as e:
                pipeline_log("Learning", f"Failed to learn from experience: {e}")

        return success
