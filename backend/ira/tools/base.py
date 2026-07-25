from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolRequest:
    intent: str
    command: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    text: str
    handled: bool = True
    tool_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(Protocol):
    def supports(self, intent: ToolRequest) -> bool:
        ...

    def execute(self, request: ToolRequest) -> ToolResult:
        ...

    def metadata(self) -> dict[str, Any]:
        ...
