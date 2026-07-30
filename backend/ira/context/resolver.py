"""
ira/context/resolver.py – Deterministic Reference Resolver (Sprint 7.3).

Resolves pronouns and contextual references (it, that, again, same app, …)
to concrete entity values using the current ConversationContext.

Design
------
* REFERENCE_MAP  – lookup table that maps trigger token → context slot name.
  Trivially extensible in Sprint 8 without touching any logic.

* Resolution order (per-turn, highest priority first):
  1. Most-recently-mentioned entity (any type) — "it", "that", "this", "them"
  2. Slot-typed reference — "same app", "same website", "same folder", …
  3. Directional / repeat — "again", "there"

* Returns ResolvedRequest:
    original_text   – unchanged original
    resolved_text   – rewritten command (or original if unresolvable)
    resolved_entities – list of ContextEntity objects used
    confidence      – 1.0 if resolved, 0.0 if unknown referent
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..pipeline_log import pipeline_log
from .models import ConversationContext, ContextEntity


# ---------------------------------------------------------------------------
# Trigger → slot-name lookup table
# "None" slot means "use last_entity() regardless of type"
# ---------------------------------------------------------------------------
REFERENCE_MAP: dict[str, str | None] = {
    # Generic pronouns → most-recent entity (any type)
    "it":       None,
    "that":     None,
    "this":     None,
    "them":     None,
    "those":    None,

    # Type-specific references
    "same app":       "last_application",
    "same application": "last_application",
    "same website":   "last_website",
    "same site":      "last_website",
    "same folder":    "last_folder",
    "same directory": "last_folder",
    "same file":      "last_file",

    # Directional / repeat — resolve to most-recent entity (any type)
    "again":    None,
    "there":    None,
    "same one": None,
}

# Ordered by descending length so multi-word triggers are checked first
_SORTED_TRIGGERS: tuple[str, ...] = tuple(
    sorted(REFERENCE_MAP.keys(), key=len, reverse=True)
)

# Suffixes that indicate a trailing reference (e.g. "open it", "open it again")
_TRAILING_TRIGGERS: tuple[str, ...] = tuple(
    f" {t}" for t in _SORTED_TRIGGERS
)


@dataclass
class ResolvedRequest:
    """Outcome of a single ReferenceResolver.resolve() call."""

    original_text: str
    resolved_text: str
    resolved_entities: list[ContextEntity] = field(default_factory=list)
    confidence: float = 1.0

    @property
    def was_resolved(self) -> bool:
        """True when the resolver actually substituted a referent."""
        return self.original_text != self.resolved_text


class ReferenceResolver:
    """
    Deterministic pronoun / reference resolver.

    No LLM.  No regex.  Pure lookup-table and string matching.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        command: str,
        context: ConversationContext,
    ) -> ResolvedRequest:
        """
        Attempt to resolve any reference trigger found in *command*.

        Parameters
        ----------
        command:
            The raw user request (original casing preserved).
        context:
            The current ConversationContext for this conversation.

        Returns
        -------
        ResolvedRequest
            If a referent is found → resolved_text contains the rewritten
            command and confidence = context.context_confidence.
            If no referent is available → resolved_text = original_text,
            confidence = 0.0, resolved_entities = [].
        """
        lowered = command.strip().lower()

        # ── Fast path: no trigger present ────────────────────────────────────
        trigger, slot_name = self._find_trigger(lowered)
        if trigger is None:
            return ResolvedRequest(
                original_text=command,
                resolved_text=command,
                confidence=1.0,
            )

        # ── Resolve referent from context ─────────────────────────────────────
        referent_entity, referent_value = self._resolve_referent(
            trigger, slot_name, context
        )

        if referent_value is None:
            pipeline_log(
                "Resolver",
                f"No referent for trigger={trigger!r} — returning clarification",
            )
            return ResolvedRequest(
                original_text=command,
                resolved_text=command,
                confidence=0.0,
            )

        # ── Rewrite the command ───────────────────────────────────────────────
        resolved_text = self._rewrite(command, lowered, trigger, referent_value)

        pipeline_log(
            "Resolver",
            f"Resolved {trigger!r} → {referent_value!r}  "
            f"(slot={slot_name or 'last_entity'}, "
            f"confidence={context.context_confidence:.2f})",
        )

        return ResolvedRequest(
            original_text=command,
            resolved_text=resolved_text,
            resolved_entities=[referent_entity] if referent_entity else [],
            confidence=context.context_confidence,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_trigger(
        self, lowered: str
    ) -> tuple[str, str | None] | tuple[None, None]:
        """
        Scan *lowered* for any REFERENCE_MAP trigger.

        Returns (trigger_token, slot_name_or_None) or (None, None).
        Multi-word triggers are checked first (sorted by length desc).
        """
        for trigger in _SORTED_TRIGGERS:
            # Whole-word match: trigger must appear as a standalone token
            # (i.e. preceded by space / start, followed by space / end)
            if (
                lowered == trigger
                or lowered.endswith(f" {trigger}")
                or f" {trigger} " in lowered
                or lowered.startswith(f"{trigger} ")
            ):
                return trigger, REFERENCE_MAP[trigger]
        return None, None

    def _resolve_referent(
        self,
        trigger: str,
        slot_name: str | None,
        context: ConversationContext,
    ) -> tuple[ContextEntity | None, str | None]:
        """
        Return (entity, value) for the given trigger.

        If *slot_name* is None → use last_entity() (most recent any-type).
        If *slot_name* is set → look up context.<slot_name>.
        """
        if slot_name is None:
            # Use the most-recently mentioned entity regardless of type
            entity = context.last_entity()
            if entity:
                return entity, entity.value
            return None, None

        # Typed slot lookup
        value: str | None = getattr(context, slot_name, None)
        if value:
            # Try to find the matching entity in active_entities
            entity = context.last_entity_of_type(
                slot_name.replace("last_", "")  # "last_application" → "application"
            )
            return entity, value
        return None, None

    def _rewrite(
        self,
        original: str,
        lowered: str,
        trigger: str,
        referent_value: str,
    ) -> str:
        """
        Replace the trailing trigger token(s) in *original* with *referent_value*.

        Strategy:
        1. Find where the trigger starts in the lowered copy.
        2. Slice the original at the same character offset.
        3. Append the referent value, preserving the original verb casing.
        """
        # Find the last occurrence of the trigger in lowered
        trigger_lower = trigger.lower()
        idx = lowered.rfind(trigger_lower)
        if idx == -1:
            # Fallback: just append referent
            return f"{original.strip()} {referent_value}"

        prefix = original[:idx].rstrip()
        if prefix:
            return f"{prefix} {referent_value}"
        return referent_value
