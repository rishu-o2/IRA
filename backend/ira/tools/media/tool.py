from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ... import actions
from ..base import ToolRequest, ToolResult


class MediaTool:
    def __init__(self) -> None:
        self._commands: dict[str, Callable[..., str]] = {
            "play_pause": self.play_pause,
            "next_track": self.next_track,
            "previous_track": self.previous_track,
            "stop": self.stop,
            "play_youtube_search": self.play_youtube_search,
        }

    def supports(self, request: ToolRequest) -> bool:
        return request.intent == "media" and request.command in self._commands

    def execute(self, request: ToolRequest) -> ToolResult:
        if not self.supports(request):
            return ToolResult(f"Media tool cannot handle {request.intent}:{request.command}.", handled=False, tool_name="media")
        try:
            return ToolResult(self._commands[request.command](**request.params), tool_name="media")
        except Exception as exc:
            return ToolResult(str(exc), handled=False, tool_name="media", metadata={"error_type": exc.__class__.__name__})

    def metadata(self) -> dict[str, Any]:
        return {
            "name": "media",
            "description": "Controls media playback and opens YouTube search results.",
            "commands": tuple(sorted(self._commands)),
        }

    def play_pause(self) -> str:
        return actions.play_pause_media()

    def next_track(self) -> str:
        return actions.next_track()

    def previous_track(self) -> str:
        return actions.previous_track()

    def stop(self) -> str:
        return actions.stop_media()

    def play_youtube_search(self, query: str) -> str:
        return actions.play_youtube_search(query)


media_tool = MediaTool()
