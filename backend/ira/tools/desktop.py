from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .. import actions
from .base import ToolRequest, ToolResult


class DesktopTools:
    """Facade for desktop actions exposed through the tools package."""

    def __init__(self) -> None:
        self._commands: dict[str, Callable[..., str]] = {
            "get_battery_status": self.get_battery_status,
            "get_system_stats": self.get_system_stats,
            "lock_screen": self.lock_screen,
            "mute_system": self.mute_system,
            "open_app": self.open_app,
            "open_known_folder": self.open_known_folder,
            "open_path": self.open_path,
            "open_website": self.open_website,
            "play_youtube_search": self.play_youtube_search,
            "search_web": self.search_web,
            "set_brightness": self.set_brightness,
            "shutdown_system": self.shutdown_system,
            "sleep_system": self.sleep_system,
            "volume_down": self.volume_down,
            "volume_up": self.volume_up,
        }

    def supports(self, request: ToolRequest) -> bool:
        return request.intent == "desktop" and request.command in self._commands

    def execute(self, request: ToolRequest) -> ToolResult:
        if not self.supports(request):
            return ToolResult(
                text=f"Desktop tools cannot handle {request.intent}:{request.command}.",
                handled=False,
                tool_name="desktop",
            )

        command = self._commands[request.command]
        try:
            result = command(**request.params)
        except Exception as exc:
            return ToolResult(
                text=str(exc),
                handled=False,
                tool_name="desktop",
                metadata={"error_type": exc.__class__.__name__},
            )
        return ToolResult(text=result, tool_name="desktop")

    def metadata(self) -> dict[str, Any]:
        return {
            "name": "desktop",
            "description": "Opens apps, websites, folders, and controls local desktop settings.",
            "commands": tuple(sorted(self._commands)),
        }

    def open_path(self, target: str) -> str:
        return actions.open_path(target)

    def open_known_folder(self, folder_name: str) -> str:
        return actions.open_known_folder(folder_name)

    def lock_screen(self) -> str:
        return actions.lock_screen()

    def shutdown_system(self) -> str:
        return actions.shutdown_system()

    def sleep_system(self) -> str:
        return actions.sleep_system()

    def mute_system(self) -> str:
        return actions.mute_system()

    def open_app(self, app_name: str) -> str:
        return actions.open_app(app_name)

    def open_website(self, url: str) -> str:
        return actions.open_website(url)

    def search_web(self, query: str) -> str:
        return actions.search_web(query)

    def play_youtube_search(self, query: str) -> str:
        return actions.play_youtube_search(query)

    def volume_up(self) -> str:
        return actions.volume_up()

    def volume_down(self) -> str:
        return actions.volume_down()

    def set_brightness(self, level: int) -> str:
        return actions.set_brightness(level)

    def get_battery_status(self) -> str:
        return actions.get_battery_status()

    def get_system_stats(self) -> str:
        return actions.get_system_stats()


desktop_tools = DesktopTools()
