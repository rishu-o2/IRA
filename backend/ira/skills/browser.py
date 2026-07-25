"""
BrowserSkill – Phase 7.3

Handles browser navigation, website opening, web search, and browser
keyboard controls.  All delegation is done through ira.actions where the
helper already exists; browser-control shortcuts (refresh, back, forward,
new-tab, close-tab, reopen-tab) are implemented locally here using the
same ctypes keybd_event pattern already used by ira.actions for volume
keys, so no new dependency is introduced.
"""

from .base import Skill
from ..assistant import AssistantResponse
from ..actions import ActionError
from ..router import default_tool_router
from ..tools import ToolRequest


def open_website(url: str) -> str:
    result = default_tool_router.execute(ToolRequest("browser", "open_website", {"url": url}))
    if not result.handled:
        raise ActionError(result.text)
    return result.text


def search_web(query: str) -> str:
    result = default_tool_router.execute(ToolRequest("browser", "search_web", {"query": query}))
    if not result.handled:
        raise ActionError(result.text)
    return result.text

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
                res = default_tool_router.execute(ToolRequest("browser", "refresh"))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)
            if lowered in _BACK_PHRASES:
                res = default_tool_router.execute(ToolRequest("browser", "back"))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)
            if lowered in _FORWARD_PHRASES:
                res = default_tool_router.execute(ToolRequest("browser", "forward"))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)
            if lowered in _NEW_TAB_PHRASES:
                res = default_tool_router.execute(ToolRequest("browser", "new_tab"))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)
            if lowered in _CLOSE_TAB_PHRASES:
                res = default_tool_router.execute(ToolRequest("browser", "close_tab"))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)
            if lowered in _REOPEN_TAB_PHRASES:
                res = default_tool_router.execute(ToolRequest("browser", "reopen_tab"))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)

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
