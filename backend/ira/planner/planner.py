"""
TaskPlanner – splits a single natural-language request into an ordered list
of atomic command strings without executing any of them.

Design principles
-----------------
* Pure function logic – no I/O, no side effects.
* No external dependencies (stdlib ``re`` only).
* Quoted sub-strings are never split, even if they contain separator words.
* Leading/trailing whitespace and repeated spaces are collapsed in every task.
* Empty tasks (produced by consecutive separators) are silently dropped.
"""

from __future__ import annotations

import re
from typing import List


# ---------------------------------------------------------------------------
# Separator table – order matters: longer phrases must come before shorter
# sub-phrases so the regex alternation matches the most specific form first.
# ---------------------------------------------------------------------------
_SEPARATORS: tuple[str, ...] = (
    "after that",
    "then please",
    "and then",
    "and also",
    "and next",
    "and finally",
    "then",
    "next",
    "also",
    "after",
    "finally",
    "and",
    ",",
)

# Build a single regex that matches any separator (case-insensitive, word-
# boundaries on word-based separators so "bands" is not split on "and").
def _build_separator_pattern(separators: tuple[str, ...]) -> re.Pattern[str]:
    parts: list[str] = []
    for sep in separators:
        if sep == ",":
            parts.append(r",")
        else:
            # Use word boundaries so "sandbox" isn't split on "and".
            escaped = re.escape(sep)
            parts.append(rf"\b{escaped}\b")
    return re.compile("|".join(parts), re.IGNORECASE)


_SEP_RE: re.Pattern[str] = _build_separator_pattern(_SEPARATORS)

# Matches a double-quoted or single-quoted string (non-greedy).
_QUOTE_RE: re.Pattern[str] = re.compile(r'"[^"]*"|\'[^\']*\'')


class TaskPlanner:
    """Converts a multi-step natural-language request into an ordered list of
    atomic command strings.

    Usage
    -----
    >>> planner = TaskPlanner()
    >>> planner.plan("Open Chrome and search Python tutorials")
    ['open chrome', 'search python tutorials']
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, command: str) -> List[str]:
        """Split *command* into an ordered list of atomic task strings.

        Parameters
        ----------
        command:
            A raw natural-language request that may contain one or more
            sub-tasks joined by separator words or punctuation.

        Returns
        -------
        list[str]
            Ordered list of trimmed, lower-cased atomic task strings.
            Always contains at least one element (the original command,
            lowered and stripped) even when no separator is found.
        """
        if not command or not command.strip():
            return []

        tasks = self._split_respecting_quotes(command.strip())
        # Normalise whitespace and case; drop blanks.
        cleaned: list[str] = []
        for task in tasks:
            task = " ".join(task.split()).lower()
            if task:
                cleaned.append(task)

        return cleaned if cleaned else [command.strip().lower()]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _split_respecting_quotes(self, text: str) -> list[str]:
        """Split *text* on separators while leaving quoted sub-strings intact.

        Strategy
        --------
        1. Scan the text for quoted sub-strings and record their spans.
        2. Walk the text left-to-right; when a separator match falls entirely
           inside a quoted span, skip it.
        3. Use the surviving separator positions to slice the text.
        """
        # Collect all quoted spans so we can guard against splitting inside them.
        quoted_spans: list[tuple[int, int]] = [
            (m.start(), m.end()) for m in _QUOTE_RE.finditer(text)
        ]

        def _inside_quote(start: int, end: int) -> bool:
            """Return True if the interval [start, end) overlaps any quoted span."""
            for qs, qe in quoted_spans:
                if start < qe and end > qs:
                    return True
            return False

        # Find all separator matches that are NOT inside quotes.
        split_points: list[tuple[int, int]] = []  # (match.start, match.end)
        for m in _SEP_RE.finditer(text):
            if not _inside_quote(m.start(), m.end()):
                split_points.append((m.start(), m.end()))

        if not split_points:
            return [text]

        parts: list[str] = []
        prev_end = 0
        for sep_start, sep_end in split_points:
            parts.append(text[prev_end:sep_start])
            prev_end = sep_end
        parts.append(text[prev_end:])

        return parts
