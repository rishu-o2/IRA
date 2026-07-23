"""
BrowserSkill – Phase 7.3

Handles browser navigation, website opening, web search, and browser
keyboard controls.  All delegation is done through ira.actions where the
helper already exists; browser-control shortcuts (refresh, back, forward,
new-tab, close-tab, reopen-tab) are implemented locally here using the
same ctypes keybd_event pattern already used by ira.actions for volume
keys, so no new dependency is introduced.
"""

import ctypes
import os
from .base import Skill
from ..assistant import AssistantResponse
from ..actions import open_website, search_web, ActionError

# ---------------------------------------------------------------------------
# Known website shortcuts – maps bare name → URL or resolvable domain
# ---------------------------------------------------------------------------
_WEBSITE_SHORTCUTS: dict[str, str] = {
    "youtube": "https://youtube.com",
    "yt": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://mail.google.com",
    "drive": "https://drive.google.com",
    "github": "https://github.com",
    "gh": "https://github.com",
    "reddit": "https://reddit.com",
    "chatgpt": "https://chat.openai.com",
    "linkedin": "https://linkedin.com",
    "facebook": "https://facebook.com",
    "instagram": "https://instagram.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "netflix": "https://netflix.com",
    "amazon": "https://amazon.com",
    "spotify": "https://open.spotify.com",
    "wikipedia": "https://wikipedia.org",
}

# ---------------------------------------------------------------------------
# Alias normalisation for search prefixes
# ---------------------------------------------------------------------------
_SEARCH_ALIASES: dict[str, str] = {
    "lookup": "search for",
    "look up": "search for",
    "google search": "search for",
    "google": "search for",
    "find": "search for",
}

# ---------------------------------------------------------------------------
# Low-level browser shortcut keys (ctypes, same pattern as ira.actions volume)
# ---------------------------------------------------------------------------
_KEYEVENTF_EXTENDEDKEY: int = 0x0001
_KEYEVENTF_KEYUP:       int = 0x0002

_VK = {
    "F5":       0x74,   # refresh
    "BROWSER_BACK":    0xA6,
    "BROWSER_FORWARD": 0xA7,
    "t":        0x54,
    "w":        0x57,
    "T":        0x54,   # Ctrl+Shift+T
}

def _key_down(vk: int, extended: bool = False) -> None:
    flags = _KEYEVENTF_EXTENDEDKEY if extended else 0
    ctypes.windll.user32.keybd_event(vk, 0, flags, 0)

def _key_up(vk: int, extended: bool = False) -> None:
    flags = (_KEYEVENTF_EXTENDEDKEY if extended else 0) | _KEYEVENTF_KEYUP
    ctypes.windll.user32.keybd_event(vk, 0, flags, 0)

def _send_key(vk: int, ctrl: bool = False, shift: bool = False, extended: bool = False) -> None:
    VK_CONTROL = 0x11
    VK_SHIFT   = 0x10
    if ctrl:
        _key_down(VK_CONTROL)
    if shift:
        _key_down(VK_SHIFT)
    _key_down(vk, extended)
    _key_up(vk, extended)
    if shift:
        _key_up(VK_SHIFT)
    if ctrl:
        _key_up(VK_CONTROL)


def refresh_browser() -> str:
    if os.name != "nt":
        raise ActionError("Browser refresh is only supported on Windows.")
    try:
        _send_key(_VK["F5"])
    except Exception as exc:
        raise ActionError("I could not refresh the browser.") from exc
    return "Refreshing the browser."


def go_back() -> str:
    if os.name != "nt":
        raise ActionError("Browser back is only supported on Windows.")
    try:
        _send_key(_VK["BROWSER_BACK"], extended=True)
    except Exception as exc:
        raise ActionError("I could not go back in the browser.") from exc
    return "Going back."


def go_forward() -> str:
    if os.name != "nt":
        raise ActionError("Browser forward is only supported on Windows.")
    try:
        _send_key(_VK["BROWSER_FORWARD"], extended=True)
    except Exception as exc:
        raise ActionError("I could not go forward in the browser.") from exc
    return "Going forward."


def open_new_tab() -> str:
    if os.name != "nt":
        raise ActionError("Open new tab is only supported on Windows.")
    try:
        _send_key(_VK["t"], ctrl=True)
    except Exception as exc:
        raise ActionError("I could not open a new tab.") from exc
    return "Opening a new tab."


def close_tab() -> str:
    if os.name != "nt":
        raise ActionError("Close tab is only supported on Windows.")
    try:
        _send_key(_VK["w"], ctrl=True)
    except Exception as exc:
        raise ActionError("I could not close the tab.") from exc
    return "Closing the current tab."


def reopen_tab() -> str:
    if os.name != "nt":
        raise ActionError("Reopen tab is only supported on Windows.")
    try:
        _send_key(_VK["T"], ctrl=True, shift=True)
    except Exception as exc:
        raise ActionError("I could not reopen the last closed tab.") from exc
    return "Reopening the last closed tab."


# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------
_WEBSITE_OPEN_PREFIXES = ("open ", "go to ", "visit ", "navigate to ")
_SEARCH_PREFIXES = (
    "search ", "search for ", "look up ", "lookup ", "find ",
    "google ", "google search ",
)
_REFRESH_PHRASES = {
    "refresh", "refresh browser", "refresh the browser",
    "reload", "reload browser", "reload the browser", "reload page",
    "refresh page",
}
_BACK_PHRASES = {"go back", "back", "browser back", "go back in browser"}
_FORWARD_PHRASES = {"go forward", "forward", "browser forward", "go forward in browser"}
_NEW_TAB_PHRASES = {"new tab", "open new tab", "open a new tab"}
_CLOSE_TAB_PHRASES = {"close tab", "close the tab", "close current tab"}
_REOPEN_TAB_PHRASES = {
    "reopen tab", "restore tab", "reopen last tab",
    "restore last tab", "undo close tab",
}

# Things that belong to other skills and must NOT match here
_NOT_BROWSER = {
    "lock screen", "mute", "mute volume", "unmute", "shutdown", "restart",
    "sleep", "hibernate", "lock", "volume up", "volume down", "brightness",
    "calculator", "notepad", "paint", "weather", "hello", "hi",
    "what time is it", "what's the time", "play music",
}


def _is_website_command(lowered: str) -> bool:
    """Return True if the command is a website-opening request."""
    for prefix in _WEBSITE_OPEN_PREFIXES:
        if lowered.startswith(prefix):
            target = lowered[len(prefix):].strip()
            # Known shortcut OR looks like a domain
            if target in _WEBSITE_SHORTCUTS:
                return True
            if "." in target and " " not in target:
                return True
    return False


def _is_search_command(lowered: str) -> bool:
    for prefix in _SEARCH_PREFIXES:
        if lowered.startswith(prefix):
            return True
    return False


class BrowserSkill(Skill):
    """Skill that handles browser navigation, website opening, and search."""

    @property
    def name(self) -> str:
        return "browser"

    @property
    def description(self) -> str:
        return "Handles browser navigation, websites, searches and browser controls."

    def can_handle(self, command: str) -> bool:
        lowered = command.lower().strip()

        # Hard-exclude things that belong to system or app skills
        if lowered in _NOT_BROWSER:
            return True if False else False  # explicit exclusion gate
        for excluded in _NOT_BROWSER:
            if lowered == excluded or lowered.startswith(excluded + " "):
                return False

        if lowered in _REFRESH_PHRASES:
            return True
        if lowered in _BACK_PHRASES:
            return True
        if lowered in _FORWARD_PHRASES:
            return True
        if lowered in _NEW_TAB_PHRASES:
            return True
        if lowered in _CLOSE_TAB_PHRASES:
            return True
        if lowered in _REOPEN_TAB_PHRASES:
            return True
        if _is_website_command(lowered):
            return True
        if _is_search_command(lowered):
            return True

        return False

    def execute(self, command: str) -> AssistantResponse:
        lowered = command.lower().strip()

        try:
            # --- Browser controls ---
            if lowered in _REFRESH_PHRASES:
                return AssistantResponse(refresh_browser())
            if lowered in _BACK_PHRASES:
                return AssistantResponse(go_back())
            if lowered in _FORWARD_PHRASES:
                return AssistantResponse(go_forward())
            if lowered in _NEW_TAB_PHRASES:
                return AssistantResponse(open_new_tab())
            if lowered in _CLOSE_TAB_PHRASES:
                return AssistantResponse(close_tab())
            if lowered in _REOPEN_TAB_PHRASES:
                return AssistantResponse(reopen_tab())

            # --- Website opening ---
            for prefix in _WEBSITE_OPEN_PREFIXES:
                if lowered.startswith(prefix):
                    target = lowered[len(prefix):].strip()
                    url = _WEBSITE_SHORTCUTS.get(target, target)
                    return AssistantResponse(open_website(url))

            # --- Web search ---
            for prefix in sorted(_SEARCH_PREFIXES, key=len, reverse=True):
                if lowered.startswith(prefix):
                    query = command[len(prefix):].strip().strip('"')
                    return AssistantResponse(search_web(query))

        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        return AssistantResponse("I could not handle that browser command.", handled=False)
