from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ... import actions
from ..base import ToolRequest, ToolResult


class CommunicationTool:
    def __init__(self) -> None:
        self._commands: dict[str, Callable[..., str]] = {
            "call": self.call,
        }

    def supports(self, request: ToolRequest) -> bool:
        return request.intent == "communication" and request.command in self._commands

    def execute(self, request: ToolRequest) -> ToolResult:
        if not self.supports(request):
            return ToolResult(
                f"Communication tool cannot handle {request.intent}:{request.command}.",
                handled=False,
                tool_name="communication",
            )
        try:
            return ToolResult(self._commands[request.command](**request.params), tool_name="communication")
        except Exception as exc:
            return ToolResult(str(exc), handled=False, tool_name="communication", metadata={"error_type": exc.__class__.__name__})

    def metadata(self) -> dict[str, Any]:
        return {
            "name": "communication",
            "description": "Routes existing communication actions such as calls.",
            "commands": tuple(sorted(self._commands)),
        }

    def call(self, app_name: str = "skype") -> str:
        return actions.open_app(app_name)


communication_tool = CommunicationTool()
