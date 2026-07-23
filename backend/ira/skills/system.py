import re
import subprocess
import os
from .base import Skill

# We need to return the exact type expected by assistant.py handlers
# which is AssistantResponse. We import it to instantiate it.
from ira.assistant import AssistantResponse
from ira.actions import (
    lock_screen,
    shutdown_system,
    sleep_system,
    mute_system,
    volume_up,
    volume_down,
    set_brightness,
    ActionError
)

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
                if os.name != "nt":
                    raise ActionError("Restart is only supported on Windows.")
                subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
                return AssistantResponse("Restarting the computer.")

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
        except subprocess.CalledProcessError:
            # Handle the specific restart subprocess error identical to assistant.py
            return AssistantResponse("I could not restart the computer.", handled=False)

        # Fallback if matched but no condition triggered (shouldn't happen)
        return AssistantResponse("I could not process the system command.", handled=False)
