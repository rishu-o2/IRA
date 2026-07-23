"""
ContextManager – top-level facade that combines AssistantState and
ConversationHistory into a single, easy-to-use interface.

Intended usage
--------------
    ctx = ContextManager()
    ctx.remember_user("open chrome")
    ctx.set_app("chrome")
    ctx.remember_assistant("Opening Chrome for you.")
"""

from datetime import datetime
from typing import Optional

from .history import ConversationHistory
from .state import AssistantState


class ContextManager:
    """Maintains both the rolling conversation history and the current
    assistant state for a single session."""

    def __init__(self) -> None:
        self._state = AssistantState()
        self._history = ConversationHistory()

    # ------------------------------------------------------------------
    # History helpers
    # ------------------------------------------------------------------

    def remember_user(self, text: str) -> None:
        """Record a user utterance and update *last_command*.

        Parameters
        ----------
        text:
            The raw text of the user's message.
        """
        self._history.add(role="user", text=text)
        self._state.last_command = text
        self._state.updated_at = datetime.now()

    def remember_assistant(self, text: str) -> None:
        """Append the assistant's response to conversation history.

        Parameters
        ----------
        text:
            The text of the assistant's reply.
        """
        self._history.add(role="assistant", text=text)
        self._state.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # State setters
    # ------------------------------------------------------------------

    def set_app(self, app: Optional[str]) -> None:
        """Update the most-recently-referenced application."""
        self._state.last_app = app
        self._state.updated_at = datetime.now()

    def set_website(self, site: Optional[str]) -> None:
        """Update the most-recently-referenced website."""
        self._state.last_website = site
        self._state.updated_at = datetime.now()

    def set_topic(self, topic: Optional[str]) -> None:
        """Update the most-recently-discussed topic."""
        self._state.last_topic = topic
        self._state.updated_at = datetime.now()

    def set_action(self, action: Optional[str]) -> None:
        """Update the most-recently-executed action."""
        self._state.last_action = action
        self._state.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear conversation history and reinitialise assistant state."""
        self._history.clear()
        self._state = AssistantState()

    # ------------------------------------------------------------------
    # Read-only accessors (convenience)
    # ------------------------------------------------------------------

    @property
    def state(self) -> AssistantState:
        """The current :class:`AssistantState` snapshot."""
        return self._state

    @property
    def history(self) -> ConversationHistory:
        """The underlying :class:`ConversationHistory` instance."""
        return self._history
