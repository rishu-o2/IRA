from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ... import actions
from ..base import ToolRequest, ToolResult


class BrowserTool:
    def __init__(self) -> None:
        self._commands: dict[str, Callable[..., str]] = {
            "open_website": self.open_website,
            "search_web": self.search_web,
            "refresh": self.refresh,
            "back": self.back,
            "forward": self.forward,
            "new_tab": self.new_tab,
            "close_tab": self.close_tab,
            "reopen_tab": self.reopen_tab,
        }

    def supports(self, request: ToolRequest) -> bool:
        return request.intent == "browser" and request.command in self._commands

    def execute(self, request: ToolRequest) -> ToolResult:
        if not self.supports(request):
            return ToolResult(f"Browser tool cannot handle {request.intent}:{request.command}.", handled=False, tool_name="browser")
        try:
            return ToolResult(self._commands[request.command](**request.params), tool_name="browser")
        except Exception as exc:
            return ToolResult(str(exc), handled=False, tool_name="browser", metadata={"error_type": exc.__class__.__name__})

    def metadata(self) -> dict[str, Any]:
        return {
            "name": "browser",
            "description": "Opens websites, searches the web, and sends browser navigation shortcuts.",
            "commands": tuple(sorted(self._commands)),
        }

    def open_website(self, url: str) -> str:
        return actions.open_website(url)

    def search_web(self, query: str) -> str:
        return actions.search_web(query)

    def refresh(self) -> str:
        from ...skills.browser import refresh_browser
        return refresh_browser()

    def back(self) -> str:
        from ...skills.browser import go_back
        return go_back()

    def forward(self) -> str:
        from ...skills.browser import go_forward
        return go_forward()

    def new_tab(self) -> str:
        from ...skills.browser import open_new_tab
        return open_new_tab()

    def close_tab(self) -> str:
        from ...skills.browser import close_tab
        return close_tab()

    def reopen_tab(self) -> str:
        from ...skills.browser import reopen_tab
        return reopen_tab()


browser_tool = BrowserTool()
