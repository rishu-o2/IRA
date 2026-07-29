from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ExperienceOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True)
class Experience:
    """Immutable record of a tool execution attempt."""
    tool: str
    intent: str
    parameters: dict[str, Any]
    outcome: ExperienceOutcome
    success: bool
    execution_time: float
    attempts: int
    recovery_used: bool
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1


@dataclass
class ExecutionPreference:
    """A learned preferred execution path for a tool and parameter configuration."""
    tool: str
    parameter_hash: str
    preferred_parameters: dict[str, Any]
    confidence: float
    success_rate: float
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
