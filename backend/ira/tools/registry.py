from __future__ import annotations

from collections.abc import Iterable

from .base import Tool, ToolRequest


class ToolRegistry:
    def __init__(self, tools: Iterable[Tool] | None = None) -> None:
        self._tools: list[Tool] = []
        if tools is not None:
            for tool in tools:
                self.register(tool)

    def register(self, tool: Tool) -> None:
        name = str(tool.metadata().get("name", tool.__class__.__name__))
        self._tools = [
            registered
            for registered in self._tools
            if str(registered.metadata().get("name", registered.__class__.__name__)) != name
        ]
        self._tools.append(tool)

    def discover(self) -> list[Tool]:
        return list(self._tools)

    def select(self, request: ToolRequest) -> Tool | None:
        for tool in self._tools:
            if tool.supports(request):
                return tool
        return None
