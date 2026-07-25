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
    ) -> None:
        self._tool_router = tool_router
        self._max_retries = max_retries

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
        """Attempts to execute a task, retrying up to max_retries on failure."""
        steps = [
            ExecutionStep(
                task_id=task.id,
                tool=task.tool,
                parameters=task.parameters,
                description=task.description,
            )
        ]

        for step in steps:
            attempt = 0
            while attempt <= self._max_retries:
                try:
                    # Build a ToolRequest from the step
                    request = ToolRequest(
                        intent=step.tool or "desktop",
                        command=step.description,
                        parameters=step.parameters,
                    )
                    result = self._tool_router.execute(request)
                    task.result = result.text if hasattr(result, "text") else str(result)
                    return True
                except Exception:
                    attempt += 1
                    if attempt <= self._max_retries:
                        if task.id in monitor.running:
                            monitor.running.remove(task.id)
                        monitor.retrying.append(task.id)
                    else:
                        if task.id in monitor.retrying:
                            monitor.retrying.remove(task.id)
                        return False

        return False
