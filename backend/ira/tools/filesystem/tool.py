from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ... import actions
from ..base import ToolRequest, ToolResult


class FilesystemTool:
    def __init__(self) -> None:
        self._commands: dict[str, Callable[..., str]] = {
            "open_path": self.open_path,
            "open_known_folder": self.open_known_folder,
        }

    def supports(self, request: ToolRequest) -> bool:
        return request.intent == "filesystem" and request.command in self._commands

    def execute(self, request: ToolRequest) -> ToolResult:
        if not self.supports(request):
            return ToolResult(
                f"Filesystem tool cannot handle {request.intent}:{request.command}.",
                handled=False,
                tool_name="filesystem",
            )
        try:
            return ToolResult(self._commands[request.command](**request.params), tool_name="filesystem")
        except Exception as exc:
            return ToolResult(str(exc), handled=False, tool_name="filesystem", metadata={"error_type": exc.__class__.__name__})

    def metadata(self) -> dict[str, Any]:
        return {
            "name": "filesystem",
            "description": "Opens files and known user folders.",
            "commands": tuple(sorted(self._commands)),
        }

    def open_path(self, target: str) -> str:
        return actions.open_path(target)

    def open_known_folder(self, folder_name: str) -> str:
        return actions.open_known_folder(folder_name)


filesystem_tool = FilesystemTool()
