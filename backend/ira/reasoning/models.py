"""
ira/reasoning/models.py – ReasoningResult dataclass (Sprint 7.3).

Produced by ReasoningEngine.reason() and consumed by the Brain orchestrator,
which unwraps resolved_request before passing it to the Planner.

Keeping this in a separate module makes it reusable for future sprints
(autonomous planning, agent chains, etc.) without coupling to the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..context.models import ContextEntity


@dataclass
class ReasoningResult:
    """
    The structured output of a single ReasoningEngine.reason() call.

    Fields
    ------
    resolved_request:
        The final, rewritten request string that should be passed to the Planner.
        May differ from the original if context, memory, or experience was used.

    confidence:
        Overall confidence [0.0–1.0].  Reflects the strength of whichever
        reasoning source contributed (context confidence, KG weight, etc.).

    used_context:
        True when ConversationContext supplied the winning referent.

    used_memory:
        True when MemoryManager / KnowledgeGraph supplied the winning referent.

    used_experience:
        True when ExperienceMemory (LearningEngine) supplied the winning referent.

    resolved_entities:
        The ContextEntity objects that were used for resolution (may be empty
        if raw passthrough or memory-only resolution).

    explanation:
        Human-readable string describing which reasoning path was taken.
        Useful for pipeline logging and future debugging UIs.
    """

    resolved_request: str
    confidence: float = 1.0
    used_context: bool = False
    used_memory: bool = False
    used_experience: bool = False
    resolved_entities: list[ContextEntity] = field(default_factory=list)
    explanation: str = ""
