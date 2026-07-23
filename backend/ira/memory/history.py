"""
ConversationHistory – a fixed-size rolling log of conversation turns,
backed by collections.deque so the oldest entries are evicted
automatically when the buffer is full.
"""

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional


class ConversationHistory:
    """Maintains a bounded, ordered list of conversation turns.

    Parameters
    ----------
    max_size:
        Maximum number of turns to keep in memory.  When the deque is
        full, the oldest entry is discarded automatically.
    """

    def __init__(self, max_size: int = 25) -> None:
        self._max_size = max_size
        self._entries: deque = deque(maxlen=max_size)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, role: str, text: str) -> None:
        """Append a new turn to the history.

        Parameters
        ----------
        role:
            Typically ``"user"`` or ``"assistant"``.
        text:
            The spoken / typed content of the turn.
        """
        entry: Dict[str, str] = {
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat(),
        }
        self._entries.append(entry)

    def last(self) -> Optional[Dict[str, str]]:
        """Return the most recent entry, or *None* if history is empty."""
        if not self._entries:
            return None
        return self._entries[-1]

    def all(self) -> List[Dict[str, str]]:
        """Return all entries as a plain list (oldest first)."""
        return list(self._entries)

    def clear(self) -> None:
        """Remove all entries from the history."""
        self._entries.clear()
