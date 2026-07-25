from __future__ import annotations

from ira.tools import ToolRegistry, ToolRequest, ToolResult, tool_registry


class ToolRouter:
    """Selects and executes tools behind a stable Brain-facing boundary."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, request: ToolRequest) -> ToolResult:
        tool = self._registry.select(request)
        if tool is None:
            return ToolResult(
                text=f"No tool can handle {request.intent}:{request.command}.",
                handled=False,
            )

        try:
            return tool.execute(request)
        except Exception as exc:
            tool_name = str(tool.metadata().get("name", tool.__class__.__name__))
            return ToolResult(
                text=str(exc),
                handled=False,
                tool_name=tool_name,
                metadata={"error_type": exc.__class__.__name__},
            )


default_tool_router = ToolRouter(tool_registry)
