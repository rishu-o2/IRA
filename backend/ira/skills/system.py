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


def get_battery_status() -> str:
    return _run_system_tool("get_battery_status")

def get_system_stats() -> str:
    return _run_system_tool("get_system_stats")

def set_brightness(level: int) -> str:
    return _run_system_tool("set_brightness", level=level)


# ---------------------------------------------------------------------------
# Exact-match phrase sets for time and date (checked before startswith)
# ---------------------------------------------------------------------------

_TIME_PHRASES: frozenset[str] = frozenset({
    "what time is it",
    "what time is it?",
    "what's the time",
    "whats the time",
    "current time",
    "tell me the time",
    "time please",
    "what time",
    "give me the time",
    "what is the time",
    "what is the current time",
    "what is the time now",
    "do you know the time",
})

_DATE_PHRASES: frozenset[str] = frozenset({
    "what is today's date",
    "what is today's date?",
    "what is todays date",
    "what is the date",
    "today's date",
    "todays date",
    "current date",
    "what day is it",
    "what day is it today",
    "what day is today",
    "what date is it today",
    "tell me the date",
    "what is the current date",
    "what date is it",
})

_BATTERY_PREFIXES: tuple[str, ...] = (
    "battery",
    "check battery",
    "battery status",
    "how is the battery",
    "battery level",
    "battery percentage",
    "battery percent",
    "how much battery",
    "check my battery",
    "show battery",
    "battery life",
    "remaining battery",
    "how much charge",
)


class SystemSkill(Skill):
    @property
    def name(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return (
            "System operations: time, date, volume, brightness, "
            "power state, screen lock, and battery status."
        )

    def can_handle(self, command: str) -> bool:
        lowered = command.lower().strip()

        # Time / Date — checked first so these never fall to LLM
        if lowered in _TIME_PHRASES:
            return True
        if lowered in _DATE_PHRASES:
            return True

        if lowered.startswith(("lock screen", "lock my screen", "lock computer", "lock pc", "lock the screen")):
            return True
        if lowered.startswith(("shut down", "shutdown", "turn off", "power off", "shut down the computer", "shutdown the computer", "turn off the computer", "power off the computer")):
            return True
        if lowered.startswith((
            "sleep", "go to sleep", "put the computer to sleep",
            "hibernate", "go to hibernate", "enter sleep mode", "enter hibernate mode",
            "sleep pc", "sleep my", "sleep the", "sleep computer",
            "sleep my computer", "suspend", "put pc to sleep", "put my computer to sleep",
        )):
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
        if lowered.startswith(_BATTERY_PREFIXES):
            return True
        if lowered.startswith(("system stats", "check system stats", "resource usage", "cpu usage", "performance stats")):
            return True
        return False

    def execute(self, command: str) -> AssistantResponse:
        from datetime import datetime

        lowered = command.lower().strip()
        try:
            # ── Time ─────────────────────────────────────────────────────────
            if lowered in _TIME_PHRASES:
                now = datetime.now()
                # %#I strips the leading zero on Windows; %-I on Linux/macOS.
                # Use %I and strip manually to be cross-platform safe.
                time_str = now.strftime("%I:%M %p").lstrip("0") or now.strftime("%I:%M %p")
                return AssistantResponse(f"The current time is {time_str}.")

            # ── Date ─────────────────────────────────────────────────────────
            if lowered in _DATE_PHRASES:
                date_str = datetime.now().strftime("%A, %B %d, %Y")
                return AssistantResponse(f"Today is {date_str}.")

            # ── Power / Screen ────────────────────────────────────────────────
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

            # ── Volume / Mute ─────────────────────────────────────────────────
            if lowered.startswith(("mute", "mute the volume", "silence", "turn volume off", "turn off volume", "volume mute")):
                return AssistantResponse(mute_system())

            if lowered.startswith(("unmute", "unmute the volume", "turn volume on", "turn on volume")):
                return AssistantResponse(mute_system())

            if lowered.startswith(("volume up", "increase volume", "louder", "make it louder")):
                return AssistantResponse(volume_up())

            if lowered.startswith(("volume down", "decrease volume", "quieter", "make it quieter")):
                return AssistantResponse(volume_down())

            # ── Brightness ────────────────────────────────────────────────────
            if "brightness" in lowered:
                match = re.search(r"(\d+)", lowered)
                if match:
                    level = int(match.group(1))
                    return AssistantResponse(set_brightness(level))
                if "up" in lowered or "increase" in lowered or "brighter" in lowered:
                    return AssistantResponse(set_brightness(80))
                if "down" in lowered or "decrease" in lowered or "dimmer" in lowered:
                    return AssistantResponse(set_brightness(30))

            # ── Battery ───────────────────────────────────────────────────────
            if lowered.startswith(_BATTERY_PREFIXES):
                return AssistantResponse(get_battery_status())

            # ── System stats ──────────────────────────────────────────────────
            if lowered.startswith(("system stats", "check system stats", "resource usage", "cpu usage", "performance stats")):
                return AssistantResponse(get_system_stats())

        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        # Fallback — can_handle matched but no branch triggered (should not happen)
        return AssistantResponse("I could not process the system command.", handled=False)
