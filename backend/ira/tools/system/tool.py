from __future__ import annotations

from collections.abc import Callable
import os
import subprocess
from typing import Any

from ... import actions
from ..base import ToolRequest, ToolResult


class SystemTool:
    def __init__(self) -> None:
        self._commands: dict[str, Callable[..., str]] = {
            "get_battery_status": self.get_battery_status,
            "get_system_stats": self.get_system_stats,
            "lock_screen": self.lock_screen,
            "mute_system": self.mute_system,
            "restart_system": self.restart_system,
            "set_brightness": self.set_brightness,
            "shutdown_system": self.shutdown_system,
            "sleep_system": self.sleep_system,
            "volume_down": self.volume_down,
            "volume_up": self.volume_up,
        }

    def supports(self, request: ToolRequest) -> bool:
        return request.intent == "system" and request.command in self._commands

    def execute(self, request: ToolRequest) -> ToolResult:
        if not self.supports(request):
            return ToolResult(f"System tool cannot handle {request.intent}:{request.command}.", handled=False, tool_name="system")
        try:
            return ToolResult(self._commands[request.command](**request.params), tool_name="system")
        except Exception as exc:
            return ToolResult(str(exc), handled=False, tool_name="system", metadata={"error_type": exc.__class__.__name__})

    def metadata(self) -> dict[str, Any]:
        return {
            "name": "system",
            "description": "Controls power state, screen lock, volume, brightness, battery, and system stats.",
            "commands": tuple(sorted(self._commands)),
        }

    def lock_screen(self) -> str:
        return actions.lock_screen()

    def shutdown_system(self) -> str:
        return actions.shutdown_system()

    def sleep_system(self) -> str:
        return actions.sleep_system()

    def restart_system(self) -> str:
        if os.name != "nt":
            raise actions.ActionError("Restart is only supported on Windows.")
        try:
            subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
        except subprocess.CalledProcessError as exc:
            raise actions.ActionError("I could not restart the computer.") from exc
        return "Restarting the computer."

    def mute_system(self) -> str:
        return actions.mute_system()

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


system_tool = SystemTool()
