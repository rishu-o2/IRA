"""
ira/context/models.py – Data models for Sprint 7.3 Conversation Context.

Three dataclasses:

    ContextEntity       – a named entity observed during conversation
    ConversationContext – per-conversation slot state (app, website, file, …)
    ContextDelta        – a stateless update produced by ContextExtractor
                          which ConversationContextManager applies atomically.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ContextEntity:
    """Represents a single entity mentioned during a conversation turn."""

    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str = "unknown"          # application | website | file | folder | contact | preference | search
    name: str = ""                        # human-readable label, e.g. "Chrome"
    value: str = ""                       # resolved value, e.g. "chrome.exe"
    confidence: float = 1.0              # extraction confidence [0.0 – 1.0]
    mentioned_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class ConversationContext:
    """Holds the most-recently-referenced entity for each slot type within one conversation."""

    conversation_id: str = "default"

    # Slot values — updated by ConversationContextManager.apply_delta()
    last_application: str | None = None
    last_website: str | None = None
    last_file: str | None = None
    last_folder: str | None = None
    last_contact: str | None = None
    last_search: str | None = None
    last_goal: str | None = None

    # Ordered list of entities (newest last) seen this conversation
    active_entities: list[ContextEntity] = field(default_factory=list)

    # context_confidence reflects how certain we are about the active slot values.
    # Starts at 1.0; may decrease if context is ambiguous or stale.
    context_confidence: float = 1.0

    # Arbitrary metadata for future extensions
    metadata: dict[str, Any] = field(default_factory=dict)

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ------------------------------------------------------------------
    # Convenience: most-recently-mentioned entity regardless of type
    # ------------------------------------------------------------------

    def last_entity(self) -> ContextEntity | None:
        """Return the most recently mentioned entity, or None."""
        return self.active_entities[-1] if self.active_entities else None

    def last_entity_of_type(self, entity_type: str) -> ContextEntity | None:
        """Return the most recent entity of a given type, or None."""
        for entity in reversed(self.active_entities):
            if entity.entity_type == entity_type:
                return entity
        return None


@dataclass
class ContextDelta:
    """
    Stateless update produced by ContextExtractor after a successful execution.

    ConversationContextManager.apply_delta() reads these fields and
    patches the matching ConversationContext slots.  Any field left as
    None means "no change for this slot".
    """

    conversation_id: str = "default"

    last_application: str | None = None
    last_website: str | None = None
    last_file: str | None = None
    last_folder: str | None = None
    last_contact: str | None = None
    last_search: str | None = None
    last_goal: str | None = None

    # Entities that the extractor identified in this turn (will be appended)
    new_entities: list[ContextEntity] = field(default_factory=list)

    # Confidence of the extraction (applied to context_confidence)
    confidence: float = 1.0
