"""
ira/reasoning/engine.py – Deterministic ReasoningEngine (Sprint 7.3).

Combines Conversation Context, Knowledge Graph, and Experience Memory
into a single, prioritised reasoning step that runs *before* the Planner.

Priority (highest → lowest)
---------------------------
1. ConversationContext  (pronoun / slot resolution via ReferenceResolver)
2. KnowledgeGraph       (entity lookup by name)
3. ExperienceMemory     (LearningEngine.recommend)
4. Raw passthrough      (no enrichment available)

No LLM is used at any stage.  All logic is deterministic.

The engine is intentionally *stateless* — it receives all inputs as
arguments and returns a ReasoningResult.  State lives in ConversationContext
and the external stores, not here.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..pipeline_log import pipeline_log
from ..context.models import ConversationContext
from ..context.resolver import ReferenceResolver, ResolvedRequest
from ..knowledge.models import KnowledgeGraph
from .models import ReasoningResult

if TYPE_CHECKING:
    # Optional dependency — only needed at runtime if injected
    from ..learning.engine import LearningEngine


class ReasoningEngine:
    """
    Deterministic, four-priority reasoning engine.

    Parameters
    ----------
    reference_resolver:
        ReferenceResolver instance for pronoun resolution.
        Defaults to a new instance if None.
    """

    def __init__(
        self,
        reference_resolver: ReferenceResolver | None = None,
    ) -> None:
        self._resolver = reference_resolver or ReferenceResolver()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reason(
        self,
        request: str,
        context: ConversationContext,
        knowledge: KnowledgeGraph | None = None,
        learning_engine: Any | None = None,
    ) -> ReasoningResult:
        """
        Run the 4-priority reasoning pipeline and return a ReasoningResult.

        Parameters
        ----------
        request:
            The raw user request string.
        context:
            The current ConversationContext for this conversation.
        knowledge:
            Optional KnowledgeGraph subgraph relevant to the request.
        learning_engine:
            Optional LearningEngine; used only for Priority 3.

        Returns
        -------
        ReasoningResult
            resolved_request is the string the Planner should receive.
        """
        pipeline_log("Reasoning", f"Starting reasoning for: {request!r}")

        # ── Priority 1: Conversation Context ─────────────────────────────────
        result = self._try_context(request, context)
        if result is not None:
            pipeline_log("Reasoning", f"Source=Context  resolved={result.resolved_request!r}  conf={result.confidence:.2f}")
            return result

        # ── Priority 2: Knowledge Graph ───────────────────────────────────────
        result = self._try_knowledge(request, knowledge or KnowledgeGraph())
        if result is not None:
            pipeline_log("Reasoning", f"Source=KnowledgeGraph  resolved={result.resolved_request!r}  conf={result.confidence:.2f}")
            return result

        # ── Priority 3: Experience Memory ────────────────────────────────────
        result = self._try_experience(request, learning_engine)
        if result is not None:
            pipeline_log("Reasoning", f"Source=Experience  resolved={result.resolved_request!r}  conf={result.confidence:.2f}")
            return result

        # ── Priority 4: Raw passthrough ───────────────────────────────────────
        pipeline_log("Reasoning", f"Source=Passthrough  resolved={request!r}")
        return ReasoningResult(
            resolved_request=request,
            confidence=1.0,
            explanation="raw passthrough — no enrichment required",
        )

    # ------------------------------------------------------------------
    # Priority handlers
    # ------------------------------------------------------------------

    def _try_context(
        self,
        request: str,
        context: ConversationContext,
    ) -> ReasoningResult | None:
        """
        Priority 1: Use ReferenceResolver to substitute pronouns/references.

        Returns a ReasoningResult only when a reference trigger was actually
        found AND resolved.  Unresolvable triggers (confidence = 0.0) are
        surfaced so the caller can return a clarification.
        """
        resolved: ResolvedRequest = self._resolver.resolve(request, context)

        # No trigger found — pass to next priority
        if not resolved.was_resolved and resolved.confidence == 1.0:
            return None

        # Trigger found but no referent — surface the failure
        if not resolved.was_resolved and resolved.confidence == 0.0:
            return ReasoningResult(
                resolved_request=request,
                confidence=0.0,
                used_context=True,
                resolved_entities=resolved.resolved_entities,
                explanation=f"reference trigger found but no referent in context for: {request!r}",
            )

        # Successfully resolved
        return ReasoningResult(
            resolved_request=resolved.resolved_text,
            confidence=resolved.confidence,
            used_context=True,
            resolved_entities=resolved.resolved_entities,
            explanation=f"resolved via conversation context: {request!r} → {resolved.resolved_text!r}",
        )

    def _try_knowledge(
        self,
        request: str,
        knowledge: KnowledgeGraph,
    ) -> ReasoningResult | None:
        """
        Priority 2: Check KnowledgeGraph for entities mentioned in the request.

        Currently performs a simple name-match lookup.  Returns None when
        the knowledge graph adds no value (no entities matched or empty graph).
        """
        if not knowledge.entities:
            return None

        request_lower = request.lower()
        for entity in knowledge.entities.values():
            if entity.name.lower() in request_lower:
                # The KG confirms this entity; no rewrite needed,
                # but we can return enriched metadata in future sprints.
                return ReasoningResult(
                    resolved_request=request,
                    confidence=entity.confidence,
                    used_memory=True,
                    explanation=(
                        f"knowledge graph confirmed entity '{entity.name}' "
                        f"(type={entity.entity_type.value})"
                    ),
                )
        return None

    def _try_experience(
        self,
        request: str,
        learning_engine: Any | None,
    ) -> ReasoningResult | None:
        """
        Priority 3: Consult LearningEngine for known tool preferences.

        A lightweight heuristic: if the request starts with "open " and we
        have a learned preference for the named app, surface it.
        """
        if learning_engine is None:
            return None

        lowered = request.strip().lower()
        if not lowered.startswith("open "):
            return None

        app_name = request[5:].strip()
        try:
            pref = learning_engine.recommend("open_app", {"app_name": app_name})
        except Exception:
            return None

        if pref is None:
            return None

        preferred_name = pref.preferred_parameters.get("app_name", app_name)
        resolved = request.replace(app_name, preferred_name, 1)
        return ReasoningResult(
            resolved_request=resolved,
            confidence=pref.confidence,
            used_experience=True,
            explanation=(
                f"experience memory: preferred '{preferred_name}' over '{app_name}' "
                f"(confidence={pref.confidence:.2f})"
            ),
        )
