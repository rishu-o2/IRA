from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AssistantResponse:
    text: str
    handled: bool = True


@dataclass(frozen=True)
class BrainRequest:
    message: str


@dataclass(frozen=True)
class BrainIntent:
    message: str
    normalized_message: str
    kind: str = "command"


@dataclass(frozen=True)
class BrainPlan:
    raw_plan: Any
    is_multi_step: bool


@dataclass(frozen=True)
class BrainResult:
    response: AssistantResponse
    intent: BrainIntent
    plan: BrainPlan
