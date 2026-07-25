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
        from ...skills.media import _play_pause_media
        return _play_pause_media()

    def next_track(self) -> str:
        from ...skills.media import _next_track
        return _next_track()

    def previous_track(self) -> str:
        from ...skills.media import _previous_track
        return _previous_track()

    def stop(self) -> str:
        from ...skills.media import _stop_media
        return _stop_media()

    def play_youtube_search(self, query: str) -> str:
        return actions.play_youtube_search(query)


media_tool = MediaTool()
