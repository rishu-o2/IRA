import re
from .base import Skill

# We need to return the exact type expected by assistant.py handlers
# which is AssistantResponse. We import it to instantiate it.
from ..assistant import AssistantResponse
from ..actions import ActionError
from ..router import default_tool_router
from ..tools import ToolRequest


def _run_system_tool(command: str, **params: object) -> str:
    result = default_tool_router.execute(ToolRequest("system", command, params))
    if not result.handled:
        raise ActionError(result.text)
    return result.text


def lock_screen() -> str:
    return _run_system_tool("lock_screen")


def shutdown_system() -> str:
    return _run_system_tool("shutdown_system")


def sleep_system() -> str:
    return _run_system_tool("sleep_system")


def restart_system() -> str:
    return _run_system_tool("restart_system")


def mute_system() -> str:
    return _run_system_tool("mute_system")


def volume_up() -> str:
    return _run_system_tool("volume_up")


def volume_down() -> str:
    return _run_system_tool("volume_down")


def set_brightness(level: int) -> str:
    return _run_system_tool("set_brightness", level=level)

class SystemSkill(Skill):
    @property
    def name(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return "System operations like volume, brightness, power state, and screen lock."

    def can_handle(self, command: str) -> bool:
        lowered = command.lower()
        if lowered.startswith(("lock screen", "lock my screen", "lock computer", "lock pc", "lock the screen")):
            return True
        if lowered.startswith(("shut down", "shutdown", "turn off", "power off", "shut down the computer", "shutdown the computer", "turn off the computer", "power off the computer")):
            return True
        if lowered.startswith(("sleep", "go to sleep", "put the computer to sleep", "hibernate", "go to hibernate", "enter sleep mode", "enter hibernate mode", "sleep pc", "sleep my", "sleep the", "sleep computer", "sleep my computer", "suspend", "put pc to sleep", "put my computer to sleep")):
            return True
        if lowered.startswith(("restart", "reboot", "restart computer", "restart the computer", "restart my computer", "restart pc", "restart my pc")):
            return True
        if lowered.startswith(("mute", "mute the volume", "silence", "turn volume off", "turn off volume", "volume mute")):
            return True
        if lowered.startswith(("unmute", "unmute the volume", "turn volume on", "turn on volume")):
            return True
        if lowered.startswith(("volume up", "increase volume", "louder", "make it louder")):
            return True
        if lowered.startswith(("volume down", "decrease volume", "quieter", "make it quieter")):
            return True
        if "brightness" in lowered:
            return True
        return False

    def execute(self, command: str) -> AssistantResponse:
        lowered = command.lower()
        try:
            if lowered.startswith(("lock screen", "lock my screen", "lock computer", "lock pc", "lock the screen")):
                return AssistantResponse(lock_screen())

            if lowered.startswith(("shut down", "shutdown", "turn off", "power off", "shut down the computer", "shutdown the computer", "turn off the computer", "power off the computer")):
                return AssistantResponse(shutdown_system())

            if lowered.startswith((
                "sleep", "go to sleep", "put the computer to sleep",
                "hibernate", "go to hibernate", "enter sleep mode", "enter hibernate mode",
                "sleep pc", "sleep my", "sleep the", "sleep computer",
                "sleep my computer", "suspend", "put pc to sleep",
                "put my computer to sleep",
            )):
                return AssistantResponse(sleep_system())

            if lowered.startswith((
                "restart", "reboot", "restart computer", "restart the computer",
                "restart my computer", "restart pc", "restart my pc",
            )):
                return AssistantResponse(restart_system())

            if lowered.startswith(("mute", "mute the volume", "silence", "turn volume off", "turn off volume", "volume mute")):
                return AssistantResponse(mute_system())

            if lowered.startswith(("unmute", "unmute the volume", "turn volume on", "turn on volume")):
                return AssistantResponse(mute_system())

            if lowered.startswith(("volume up", "increase volume", "louder", "make it louder")):
                return AssistantResponse(volume_up())

            if lowered.startswith(("volume down", "decrease volume", "quieter", "make it quieter")):
                return AssistantResponse(volume_down())

            if "brightness" in lowered:
                match = re.search(r"(\d+)", lowered)
                if match:
                    level = int(match.group(1))
                    return AssistantResponse(set_brightness(level))
                if "up" in lowered or "increase" in lowered or "brighter" in lowered:
                    return AssistantResponse(set_brightness(80))
                if "down" in lowered or "decrease" in lowered or "dimmer" in lowered:
                    return AssistantResponse(set_brightness(30))

        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)
        # Fallback if matched but no condition triggered (shouldn't happen)
        return AssistantResponse("I could not process the system command.", handled=False)
