"""
ira/context/extractor.py – Stateless ContextExtractor (Sprint 7.3).

Analyses an executed command string and returns a ContextDelta describing
which conversation-context slots should be updated.  The extractor does
*not* mutate any state; the ConversationContextManager applies the delta.

Rules are deterministic and regex-free — plain prefix/keyword matching.

Supported extractions
---------------------
    open <app>                   → last_application
    open <url-like>              → last_website
    open <folder>                → last_folder   (known folder names)
    open <file>                  → last_file      (has file extension)
    search <query>               → last_search + last_website (search engine)
    remember my <key> is <val>   → preference entity + appropriate slot
    open my ide / editor / …     → preference alias → application slot
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ..pipeline_log import pipeline_log
from .models import ContextDelta, ContextEntity


# ---------------------------------------------------------------------------
# Known folder names (case-insensitive).  Extend freely.
# ---------------------------------------------------------------------------
_KNOWN_FOLDERS: frozenset[str] = frozenset({
    "downloads", "documents", "desktop", "pictures", "videos", "music",
    "home", "root", "temp", "tmp", "appdata", "program files",
})

# ---------------------------------------------------------------------------
# Known web verbs that precede a website/query.
# ---------------------------------------------------------------------------
_SEARCH_PREFIXES: tuple[str, ...] = (
    "search for ", "search ", "google ", "look up ", "find ",
)

# ---------------------------------------------------------------------------
# Preference patterns:  "remember my <key> is <value>"
# Mapped to slot names.
# ---------------------------------------------------------------------------
_PREFERENCE_SLOT_MAP: dict[str, str] = {
    "ide": "last_application",
    "editor": "last_application",
    "browser": "last_website",
    "terminal": "last_application",
    "music player": "last_application",
    "favourite ide": "last_application",
    "favorite ide": "last_application",
    "favourite editor": "last_application",
    "favorite editor": "last_application",
    "favourite browser": "last_website",
    "favorite browser": "last_website",
}

# Regex: "remember my <key> is <value>" / "my <key> is <value>"
_PREF_PATTERN = re.compile(
    r"(?:remember\s+)?my\s+(?P<key>[a-z ]+?)\s+is\s+(?P<value>.+)",
    re.IGNORECASE,
)


def _has_file_extension(word: str) -> bool:
    """Return True if *word* looks like a filename (has a non-TLD dot-extension)."""
    # Exclude common TLDs so 'github.com' is not treated as a file
    _TLD_LIKE = {
        "com", "org", "net", "io", "dev", "ai", "co", "uk",
        "edu", "gov", "info", "biz", "app", "me", "us",
    }
    match = re.search(r"\.([a-z]{2,5})$", word.lower())
    if not match:
        return False
    ext = match.group(1)
    return ext not in _TLD_LIKE


class ContextExtractor:
    """
    Stateless extractor: given a command string, return a ContextDelta.

    The caller (ConversationContextManager or BrainOrchestrator) applies
    the delta; this class never reads or writes any external state.
    """

    def extract(self, command: str, conversation_id: str = "default") -> ContextDelta:
        """
        Analyse *command* and return a ContextDelta describing what changed.

        Parameters
        ----------
        command:
            The original (or already-resolved) user command.
        conversation_id:
            Passed through so the caller can route the delta correctly.
        """
        delta = ContextDelta(conversation_id=conversation_id, confidence=1.0)
        lowered = command.strip().lower()

        # ── 1. Preference pattern ("remember my IDE is VS Code") ─────────────
        # Match against the original command so captured value preserves casing.
        pref_match = _PREF_PATTERN.match(command.strip())
        if pref_match:
            key = pref_match.group("key").strip().lower()
            value = pref_match.group("value").strip()

            entity = ContextEntity(
                entity_type="preference",
                name=key,
                value=value,
                confidence=1.0,
                mentioned_at=datetime.now(timezone.utc),
            )
            delta.new_entities.append(entity)

            # Map to a context slot if we recognise the key
            slot = _PREFERENCE_SLOT_MAP.get(key)
            if slot == "last_application":
                delta.last_application = value
            elif slot == "last_website":
                delta.last_website = value

            pipeline_log(
                "Context",
                f"Extracted preference: {key!r} = {value!r} → slot={slot}",
            )
            return delta

        # ── 2. Search prefix ─────────────────────────────────────────────────
        for prefix in _SEARCH_PREFIXES:
            if lowered.startswith(prefix):
                query = command[len(prefix):].strip()
                delta.last_search = query
                entity = ContextEntity(
                    entity_type="search",
                    name="search",
                    value=query,
                    confidence=1.0,
                    mentioned_at=datetime.now(timezone.utc),
                )
                delta.new_entities.append(entity)
                pipeline_log("Context", f"Extracted search query: {query!r}")
                return delta

        # ── 3. Open <target> ─────────────────────────────────────────────────
        if lowered.startswith("open "):
            target = command[5:].strip()
            target_lower = target.lower()

            # 3a. URL-like or known website shortcut
            if (
                "." in target_lower
                and not _has_file_extension(target_lower)
            ) or target_lower in {
                "github", "youtube", "google", "twitter", "x", "reddit",
                "stackoverflow", "linkedin", "facebook", "instagram",
            }:
                delta.last_website = target
                entity = ContextEntity(
                    entity_type="website",
                    name=target,
                    value=target,
                    confidence=1.0,
                    mentioned_at=datetime.now(timezone.utc),
                )
                delta.new_entities.append(entity)
                pipeline_log("Context", f"Extracted website: {target!r}")
                return delta

            # 3b. Known folder name
            if target_lower in _KNOWN_FOLDERS:
                delta.last_folder = target
                entity = ContextEntity(
                    entity_type="folder",
                    name=target,
                    value=target,
                    confidence=1.0,
                    mentioned_at=datetime.now(timezone.utc),
                )
                delta.new_entities.append(entity)
                pipeline_log("Context", f"Extracted folder: {target!r}")
                return delta

            # 3c. File (has extension)
            if _has_file_extension(target_lower):
                delta.last_file = target
                entity = ContextEntity(
                    entity_type="file",
                    name=target,
                    value=target,
                    confidence=0.9,
                    mentioned_at=datetime.now(timezone.utc),
                )
                delta.new_entities.append(entity)
                pipeline_log("Context", f"Extracted file: {target!r}")
                return delta

            # 3d. Default → application
            delta.last_application = target
            entity = ContextEntity(
                entity_type="application",
                name=target,
                value=target,
                confidence=1.0,
                mentioned_at=datetime.now(timezone.utc),
            )
            delta.new_entities.append(entity)
            pipeline_log("Context", f"Extracted application: {target!r}")
            return delta

        # ── 4. No match — return empty delta ─────────────────────────────────
        pipeline_log("Context", f"No entity extracted from: {command!r}")
        return delta
