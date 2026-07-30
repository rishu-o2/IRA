"""
ira/context/manager.py – In-memory ConversationContextManager (Sprint 7.3).

Stores one ConversationContext per conversation_id.
No database.  No external dependencies.

Usage
-----
    mgr = ConversationContextManager()
    ctx = mgr.current("session-123")
    mgr.apply_delta(delta)
    entities = mgr.recent_entities("session-123", limit=5)
    mgr.expire_old_context(max_age_seconds=3600)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..pipeline_log import pipeline_log
from .models import ConversationContext, ContextDelta, ContextEntity


class ConversationContextManager:
    """
    Pure in-memory store for per-conversation context.

    Thread-safety note: intentionally single-threaded for Sprint 7.3.
    A lock layer can be added in a future sprint without changing the API.
    """

    def __init__(self) -> None:
        # conversation_id → ConversationContext
        self._store: dict[str, ConversationContext] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def create(self, conversation_id: str) -> ConversationContext:
        """Create and register a fresh ConversationContext for *conversation_id*."""
        ctx = ConversationContext(conversation_id=conversation_id)
        self._store[conversation_id] = ctx
        pipeline_log("Context", f"Created context for conversation '{conversation_id}'")
        return ctx

    def current(self, conversation_id: str) -> ConversationContext:
        """Return the existing context or create a new one if absent."""
        if conversation_id not in self._store:
            return self.create(conversation_id)
        return self._store[conversation_id]

    def update(self, context: ConversationContext) -> None:
        """Persist (overwrite) a mutated ConversationContext back into the store.

        This method stamps ``context.updated_at`` with the current UTC time.
        If you need to preserve an existing ``updated_at`` (e.g. for testing
        expiry logic), write directly to ``manager._store[conversation_id]``.
        """
        context.updated_at = datetime.now(timezone.utc)
        self._store[context.conversation_id] = context
        pipeline_log(
            "Context",
            f"Updated context for '{context.conversation_id}' "
            f"(confidence={context.context_confidence:.2f})",
        )

    def _write(self, context: ConversationContext) -> None:
        """Internal write that does NOT update the timestamp.

        Used when we need to preserve an existing ``updated_at``, for example
        inside :meth:`apply_delta` when appending entities without resetting
        the slot-update timestamp.
        """
        self._store[context.conversation_id] = context

    def clear(self, conversation_id: str) -> None:
        """Remove the context for *conversation_id* entirely."""
        self._store.pop(conversation_id, None)
        pipeline_log("Context", f"Cleared context for '{conversation_id}'")

    # ------------------------------------------------------------------
    # Delta application (called after ContextExtractor runs)
    # ------------------------------------------------------------------

    def apply_delta(self, delta: ContextDelta) -> ConversationContext:
        """
        Apply a ContextDelta to the matching ConversationContext.

        Only non-None delta fields overwrite existing slots.
        New entities are appended to active_entities (newest last).
        """
        ctx = self.current(delta.conversation_id)

        if delta.last_application is not None:
            ctx.last_application = delta.last_application
            pipeline_log(
                "ContextUpdate",
                f"last_application = {delta.last_application}  "
                f"confidence = {delta.confidence:.2f}",
            )
        if delta.last_website is not None:
            ctx.last_website = delta.last_website
            pipeline_log(
                "ContextUpdate",
                f"last_website = {delta.last_website}  "
                f"confidence = {delta.confidence:.2f}",
            )
        if delta.last_file is not None:
            ctx.last_file = delta.last_file
            pipeline_log(
                "ContextUpdate",
                f"last_file = {delta.last_file}  "
                f"confidence = {delta.confidence:.2f}",
            )
        if delta.last_folder is not None:
            ctx.last_folder = delta.last_folder
            pipeline_log(
                "ContextUpdate",
                f"last_folder = {delta.last_folder}  "
                f"confidence = {delta.confidence:.2f}",
            )
        if delta.last_contact is not None:
            ctx.last_contact = delta.last_contact
            pipeline_log("ContextUpdate", f"last_contact = {delta.last_contact}")
        if delta.last_search is not None:
            ctx.last_search = delta.last_search
            pipeline_log("ContextUpdate", f"last_search = {delta.last_search}")
        if delta.last_goal is not None:
            ctx.last_goal = delta.last_goal
            pipeline_log("ContextUpdate", f"last_goal = {delta.last_goal}")

        # Append new entities
        ctx.active_entities.extend(delta.new_entities)

        # Update confidence
        ctx.context_confidence = delta.confidence

        self.update(ctx)
        return ctx

    # ------------------------------------------------------------------
    # Entity helpers
    # ------------------------------------------------------------------

    def remember_entity(
        self,
        conversation_id: str,
        entity: ContextEntity,
    ) -> None:
        """Append *entity* to the active_entities list for *conversation_id*."""
        ctx = self.current(conversation_id)
        ctx.active_entities.append(entity)
        self.update(ctx)
        pipeline_log(
            "Context",
            f"Remembered entity '{entity.name}' (type={entity.entity_type}) "
            f"for '{conversation_id}'",
        )

    def recent_entities(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[ContextEntity]:
        """Return the most recent *limit* entities (newest first)."""
        ctx = self.current(conversation_id)
        return list(reversed(ctx.active_entities[-limit:]))

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def expire_old_context(self, max_age_seconds: float = 3600.0) -> int:
        """
        Remove contexts that have not been updated within *max_age_seconds*.

        Returns the number of conversations evicted.
        """
        now = datetime.now(timezone.utc)
        to_evict = [
            cid
            for cid, ctx in self._store.items()
            if (now - ctx.updated_at).total_seconds() > max_age_seconds
        ]
        for cid in to_evict:
            del self._store[cid]
        if to_evict:
            pipeline_log("Context", f"Expired {len(to_evict)} stale conversation(s)")
        return len(to_evict)
