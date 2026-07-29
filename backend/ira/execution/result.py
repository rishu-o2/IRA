from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    RECOVERED = "RECOVERED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"


@dataclass
class StepExecutionResult:
    """Represents the outcome of a single tool execution step."""
    status: ExecutionStatus
    tool: str
    attempt: int
    output: str = ""
    error: Exception | None = None
    recoverable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
