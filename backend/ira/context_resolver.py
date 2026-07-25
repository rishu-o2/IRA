"""
context_resolver.py – Pronoun / reference resolution for IRA commands.

Extracted from IRAAssistant._resolve_context (Phase 2.6 Step 3).

Takes a command string and, when a pronoun or reference trigger is
detected, attempts to rewrite it using the current session context
(last_app / last_website).  Returns either a rewritten (command, lowered)
pair or an AssistantResponse clarification when no referent is available.

No circular imports: imports only from brain.models and memory.context.
"""
from __future__ import annotations

from .brain.models import AssistantResponse
from .memory.context import ContextManager


# Verbs that act on an *application* referent.
_APP_VERBS: frozenset[str] = frozenset({
    "close", "minimize", "minimise", "maximize", "maximise",
    "restore", "focus", "switch to", "reopen", "relaunch",
})

# Verbs that act on a *website* referent.
_WEB_VERBS: frozenset[str] = frozenset({
    "refresh", "reload", "go back", "go forward",
    "open again", "reopen", "revisit",
})

# Triggers that indicate a pronoun / reference is present.
_CONTEXT_TRIGGERS: tuple[str, ...] = (
    " it", " this", " that", " them", " again",
    " the previous", " the same",
)

# Clarification messages per-verb (kept as a dict for readability).
_CLARIFICATIONS: dict[str, str] = {
    "close":      "What would you like me to close?",
    "minimize":   "What would you like me to minimize?",
    "minimise":   "What would you like me to minimize?",
    "maximize":   "What would you like me to maximize?",
    "maximise":   "What would you like me to maximize?",
    "restore":    "What would you like me to restore?",
    "focus":      "Which application should I focus?",
    "switch to":  "Which application would you like to switch to?",
    "reopen":     "What would you like me to reopen?",
    "relaunch":   "What would you like me to relaunch?",
    "refresh":    "Which website would you like me to refresh?",
    "reload":     "Which website would you like me to reload?",
    "revisit":    "Which website would you like me to revisit?",
    "open again": "Which website or application would you like me to open again?",
}


class ContextResolver:
    """Rewrites pronoun-bearing commands using the session ContextManager."""

    def __init__(self, context: ContextManager) -> None:
        self._context = context

    def resolve(
        self,
        command: str,
        lowered: str,
    ) -> tuple[str, str] | AssistantResponse:
        """Return the (possibly rewritten) ``(command, lowered)`` pair, or
        an ``AssistantResponse`` clarification when the referent is unknown.
        """
        # Fast exit – no pronoun / reference trigger in the command.
        if not any(trigger in lowered for trigger in _CONTEXT_TRIGGERS):
            return command, lowered

        state = self._context.state

        # Identify the verb.
        verb: str | None = None
        for v in _APP_VERBS | _WEB_VERBS:
            if lowered.startswith(v + " ") or lowered == v:
                verb = v
                break
        # Multi-word verbs checked separately (longer ones first).
        for mv in ("switch to", "go back", "go forward", "open again"):
            if lowered.startswith(mv):
                verb = mv
                break

        if verb is None:
            # Trigger word present but verb unidentifiable; pass through.
            return command, lowered

        # Resolve referent from context state.
        referent: str | None
        if verb in _WEB_VERBS:
            referent = state.last_website
        elif verb in _APP_VERBS:
            referent = state.last_app
        else:
            referent = state.last_app or state.last_website

        if not referent:
            msg = _CLARIFICATIONS.get(verb, f"What would you like me to {verb}?")
            print("[CTX] No context available for pronoun resolution")
            return AssistantResponse(msg, handled=False)

        # Strip trailing trigger and append resolved referent.
        rewritten = lowered
        for trigger in _CONTEXT_TRIGGERS:
            if rewritten.endswith(trigger):
                rewritten = rewritten[: -len(trigger)].strip()
                break

        resolved = f"{rewritten} {referent}"
        print(f'[CTX] Resolved "{command}" -> "{resolved}" (referent: {referent!r})')
        return resolved, resolved.lower()
