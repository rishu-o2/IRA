"""
MediaSkill – Phase 7.4

Handles media playback (play, pause, stop, next, previous) and volume
operations.  Volume-related commands delegate to existing ira.actions
helpers.  Playback-control keys (no existing action function) are
implemented as private helpers using the same Win32 ctypes.keybd_event
pattern already used in ira.actions for volume/mute.
"""

import ctypes
import os
from .base import Skill
from ..assistant import AssistantResponse
from ..actions import ActionError
from ..router import default_tool_router
from ..tools import ToolRequest


def mute_system() -> str:
    result = default_tool_router.execute(ToolRequest("system", "mute_system"))
    if not result.handled:
        raise ActionError(result.text)
    return result.text


def volume_up() -> str:
    result = default_tool_router.execute(ToolRequest("system", "volume_up"))
    if not result.handled:
        raise ActionError(result.text)
    return result.text


def volume_down() -> str:
    result = default_tool_router.execute(ToolRequest("system", "volume_down"))
    if not result.handled:
        raise ActionError(result.text)
    return result.text


def play_youtube_search(query: str) -> str:
    result = default_tool_router.execute(ToolRequest("media", "play_youtube_search", {"query": query}))
    if not result.handled:
        raise ActionError(result.text)
    return result.text

# ---------------------------------------------------------------------------
# Private Win32 media-key helpers
# ---------------------------------------------------------------------------
_KEYEVENTF_EXTENDEDKEY: int = 0x0001
_KEYEVENTF_KEYUP:       int = 0x0002

# Virtual-key codes for media keys
_VK_MEDIA_PLAY_PAUSE: int = 0xB3
_VK_MEDIA_NEXT_TRACK: int = 0xB0
_VK_MEDIA_PREV_TRACK: int = 0xB1
_VK_MEDIA_STOP:       int = 0xB2


def _send_media_key(vk: int) -> None:
    """Press and release a single extended virtual key."""
    ctypes.windll.user32.keybd_event(vk, 0, _KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk, 0, _KEYEVENTF_EXTENDEDKEY | _KEYEVENTF_KEYUP, 0)


def _play_pause_media() -> str:
    if os.name != "nt":
        raise ActionError("Media play/pause is only supported on Windows.")
    try:
        _send_media_key(_VK_MEDIA_PLAY_PAUSE)
    except Exception as exc:
        raise ActionError("I could not toggle media playback.") from exc
    return "Toggling media playback."


def _next_track() -> str:
    if os.name != "nt":
        raise ActionError("Next track is only supported on Windows.")
    try:
        _send_media_key(_VK_MEDIA_NEXT_TRACK)
    except Exception as exc:
        raise ActionError("I could not skip to the next track.") from exc
    return "Skipping to the next track."


def _previous_track() -> str:
    if os.name != "nt":
        raise ActionError("Previous track is only supported on Windows.")
    try:
        _send_media_key(_VK_MEDIA_PREV_TRACK)
    except Exception as exc:
        raise ActionError("I could not go to the previous track.") from exc
    return "Going to the previous track."


def _stop_media() -> str:
    if os.name != "nt":
        raise ActionError("Media stop is only supported on Windows.")
    try:
        _send_media_key(_VK_MEDIA_STOP)
    except Exception as exc:
        raise ActionError("I could not stop media playback.") from exc
    return "Stopping media playback."


# ---------------------------------------------------------------------------
# Command classification sets / prefixes
# ---------------------------------------------------------------------------

_PLAY_PHRASES = {
    "play", "play music", "play song", "play songs", "play audio",
    "play spotify", "play youtube music", "resume", "resume music",
    "resume playback", "resume audio", "resume song",
}
_PLAY_PREFIXES = ("play ", "resume ")

_PAUSE_PHRASES = {
    "pause", "pause music", "pause song", "pause audio",
    "pause playback", "hold music", "hold on", "hold it",
}
_PAUSE_PREFIXES = ("pause ",)

_STOP_PHRASES = {
    "stop", "stop music", "stop audio", "stop playback",
    "stop song", "stop media",
}
_STOP_PREFIXES = ("stop ",)

_NEXT_PHRASES = {
    "next", "next song", "next track", "next music", "skip",
    "skip song", "skip track", "skip music",
}

_PREV_PHRASES = {
    "previous", "previous song", "previous track", "previous music",
    "prev", "prev song", "prev track",
    "go back song", "go back track", "go back music",
    "last song", "last track",
}

_VOLUME_UP_PHRASES = {
    "volume up", "increase volume", "louder", "make it louder",
    "make louder", "turn it up", "turn up",
}
_VOLUME_DOWN_PHRASES = {
    "volume down", "decrease volume", "quieter", "lower volume",
    "make it quieter", "make quieter", "turn it down", "turn down",
}
_MUTE_PHRASES = {
    "mute", "mute volume", "silence", "turn volume off",
    "turn off volume", "volume mute", "go silent",
}
_UNMUTE_PHRASES = {
    "unmute", "unmute volume", "turn volume on",
    "turn on volume", "unsilence",
}

# Everything that explicitly does NOT belong to MediaSkill
_NOT_MEDIA = {
    "open chrome", "open firefox", "open edge", "open browser",
    "search python", "search for python", "google python",
    "lock screen", "lock computer", "shutdown", "restart", "sleep",
    "hibernate", "brightness", "set brightness",
    "calculator", "open calculator", "open notepad", "open paint",
    "weather", "what time is it", "what's the time",
    "open youtube",   # that is a BrowserSkill command
    "battery", "system stats",
}


def _lowered(command: str) -> str:
    return command.lower().strip()


class MediaSkill(Skill):
    """Skill responsible for media playback and volume operations."""

    @property
    def name(self) -> str:
        return "media"

    @property
    def description(self) -> str:
        return "Controls media playback (play, pause, stop, skip) and volume."

    # ------------------------------------------------------------------
    # can_handle
    # ------------------------------------------------------------------
    def can_handle(self, command: str) -> bool:
        low = _lowered(command)

        # Hard exclusions first
        if low in _NOT_MEDIA:
            return False
        for excluded in _NOT_MEDIA:
            if low.startswith(excluded):
                return False

        if low in _PLAY_PHRASES or low in _PAUSE_PHRASES or low in _STOP_PHRASES:
            return True
        if low in _NEXT_PHRASES or low in _PREV_PHRASES:
            return True
        if low in _VOLUME_UP_PHRASES or low in _VOLUME_DOWN_PHRASES:
            return True
        if low in _MUTE_PHRASES or low in _UNMUTE_PHRASES:
            return True

        # Prefix matches for compound commands ("play relaxing music", etc.)
        for prefix in _PLAY_PREFIXES:
            if low.startswith(prefix):
                return True
        for prefix in _PAUSE_PREFIXES:
            if low.startswith(prefix):
                return True
        for prefix in _STOP_PREFIXES:
            if low.startswith(prefix):
                # Exclude "stop ... app/website" patterns
                rest = low[len(prefix):]
                if rest and rest.split()[0] not in {"music", "audio", "playback", "media", "song", "track"}:
                    return False
                return True

        return False

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------
    def execute(self, command: str) -> AssistantResponse:
        low = _lowered(command)

        try:
            # Volume – delegate to ira.actions
            if low in _MUTE_PHRASES:
                return AssistantResponse(mute_system())

            if low in _UNMUTE_PHRASES:
                return AssistantResponse(mute_system())  # toggle

            if low in _VOLUME_UP_PHRASES:
                return AssistantResponse(volume_up())

            if low in _VOLUME_DOWN_PHRASES:
                return AssistantResponse(volume_down())

            # Next / previous
            if low in _NEXT_PHRASES:
                return AssistantResponse(_next_track())

            if low in _PREV_PHRASES:
                return AssistantResponse(_previous_track())

            # Stop
            if low in _STOP_PHRASES or any(low.startswith(p) for p in _STOP_PREFIXES):
                return AssistantResponse(_stop_media())

            # Pause
            if low in _PAUSE_PHRASES or any(low.startswith(p) for p in _PAUSE_PREFIXES):
                return AssistantResponse(_play_pause_media())

            # Play / resume (catch-all after above)
            if low in _PLAY_PHRASES or any(low.startswith(p) for p in _PLAY_PREFIXES):
                if low.startswith("play ") and low.endswith(" on youtube"):
                    query = command[len("play ") : -len(" on youtube")].strip()
                    return AssistantResponse(play_youtube_search(query))
                return AssistantResponse(_play_pause_media())

        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        return AssistantResponse("I could not handle that media command.", handled=False)
