"""
planning/monitor.py - ExecutionMonitor tracking task states.
"""
from __future__ import annotations

from typing import Any


class ExecutionMonitor:
    """Tracks state and progress of the ExecutionEngine."""

    def __init__(self) -> None:
        self.pending: list[str] = []
        self.running: list[str] = []
        self.paused: list[str] = []
        self.retrying: list[str] = []
        self.completed: list[str] = []
        self.failed: list[str] = []
        self.skipped: list[str] = []
        self.cancelled: list[str] = []

    def progress(self) -> float:
        total = (
            len(self.pending)
            + len(self.running)
            + len(self.paused)
            + len(self.retrying)
            + len(self.completed)
            + len(self.failed)
            + len(self.skipped)
            + len(self.cancelled)
        )
        if total == 0:
            return 0.0
        finished = len(self.completed) + len(self.failed) + len(self.skipped) + len(self.cancelled)
        return finished / total

    def current_task(self) -> str | None:
        if self.running:
            return self.running[0]
        if self.retrying:
            return self.retrying[0]
        return None

    def summary(self) -> dict[str, Any]:
        return {
            "progress": self.progress(),
            "pending": len(self.pending),
            "running": len(self.running),
            "paused": len(self.paused),
            "retrying": len(self.retrying),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "cancelled": len(self.cancelled),
        }
