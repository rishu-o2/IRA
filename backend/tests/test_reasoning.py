"""
tests/test_reasoning.py – Sprint 7.3 ReasoningEngine tests.

Covers:
    Priority 1 – Conversation Context wins (pronoun resolved)
    Priority 2 – KnowledgeGraph contributes (entity match)
    Priority 3 – Experience / LearningEngine fallback
    Priority 4 – Raw passthrough (no enrichment)
    Confidence values for each path
    Context overrides all other sources
    Unresolvable reference → confidence = 0.0
"""
from __future__ import annotations

import pytest

from ira.context.models import ConversationContext, ContextEntity
from ira.knowledge.models import KnowledgeGraph, Entity, EntityType
from ira.reasoning.engine import ReasoningEngine
from ira.reasoning.models import ReasoningResult


# ============================================================
# Helpers
# ============================================================


def _ctx(**kwargs) -> ConversationContext:
    return ConversationContext(conversation_id="test", **kwargs)


class _FakeLearningEngine:
    """Minimal stand-in for LearningEngine with one hard-coded preference."""

    def __init__(self, app_name: str, preferred: str, confidence: float) -> None:
        self._app_name = app_name
        self._preferred = preferred
        self._confidence = confidence

    def recommend(self, tool: str, params: dict):
        if tool == "open_app" and params.get("app_name") == self._app_name:
            from types import SimpleNamespace
            return SimpleNamespace(
                preferred_parameters={"app_name": self._preferred},
                confidence=self._confidence,
            )
        return None


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def engine() -> ReasoningEngine:
    return ReasoningEngine()


# ============================================================
# Priority 1: Conversation Context
# ============================================================


class TestPriority1Context:
    def test_resolves_pronoun_via_context(self, engine):
        entity = ContextEntity(entity_type="application", name="Chrome", value="Chrome")
        ctx = _ctx(last_application="Chrome", active_entities=[entity])

        result = engine.reason("Open it", ctx)

        assert result.used_context is True
        assert result.used_memory is False
        assert result.used_experience is False
        assert "Chrome" in result.resolved_request
        assert result.confidence > 0.0

    def test_context_confidence_propagated(self, engine):
        entity = ContextEntity(entity_type="application", name="Spotify", value="Spotify")
        ctx = _ctx(
            last_application="Spotify",
            active_entities=[entity],
            context_confidence=0.8,
        )
        result = engine.reason("Open it", ctx)
        assert result.confidence == 0.8
        assert result.used_context is True

    def test_unresolvable_trigger_returns_zero_confidence(self, engine):
        ctx = _ctx()  # no entities
        result = engine.reason("Open it", ctx)
        assert result.confidence == 0.0
        assert result.used_context is True
        assert result.resolved_request == "Open it"

    def test_context_overrides_knowledge_graph(self, engine):
        """Priority 1 must win even when KG also has a match."""
        entity = ContextEntity(entity_type="application", name="Chrome", value="Chrome")
        ctx = _ctx(last_application="Chrome", active_entities=[entity])

        kg = KnowledgeGraph()
        kg_entity = Entity(name="Chrome", entity_type=EntityType.APPLICATION, confidence=0.9)
        kg.add_entity(kg_entity)

        result = engine.reason("Open it", ctx, knowledge=kg)
        assert result.used_context is True
        assert result.used_memory is False

    def test_context_overrides_experience(self, engine):
        entity = ContextEntity(entity_type="application", name="Chrome", value="Chrome")
        ctx = _ctx(last_application="Chrome", active_entities=[entity])
        fake_engine = _FakeLearningEngine("it", "google-chrome", 0.99)

        result = engine.reason("Open it", ctx, learning_engine=fake_engine)
        assert result.used_context is True
        assert result.used_experience is False


# ============================================================
# Priority 2: Knowledge Graph
# ============================================================


class TestPriority2KnowledgeGraph:
    def test_kg_entity_match_used_when_no_context_trigger(self, engine):
        ctx = _ctx()  # no pronoun trigger → context Priority 1 returns None
        kg = KnowledgeGraph()
        e = Entity(name="Chrome", entity_type=EntityType.APPLICATION, confidence=0.85)
        kg.add_entity(e)

        result = engine.reason("Open Chrome", ctx, knowledge=kg)
        assert result.used_memory is True
        assert result.confidence == pytest.approx(0.85)
        assert result.resolved_request == "Open Chrome"

    def test_empty_kg_skipped(self, engine):
        ctx = _ctx()
        result = engine.reason("Open Chrome", ctx, knowledge=KnowledgeGraph())
        # Should fall through to Priority 4 passthrough
        assert result.used_memory is False
        assert result.used_context is False
        assert result.used_experience is False

    def test_kg_does_not_rewrite_request(self, engine):
        """KG Priority 2 confirms the entity but does not change the request string."""
        ctx = _ctx()
        kg = KnowledgeGraph()
        e = Entity(name="VS Code", entity_type=EntityType.APPLICATION, confidence=0.7)
        kg.add_entity(e)

        result = engine.reason("Open VS Code", ctx, knowledge=kg)
        assert result.resolved_request == "Open VS Code"


# ============================================================
# Priority 3: Experience Memory
# ============================================================


class TestPriority3Experience:
    def test_learning_engine_rewrites_app_name(self, engine):
        ctx = _ctx()  # no context, no KG
        fake = _FakeLearningEngine("chrome", "google-chrome", 0.75)

        result = engine.reason("Open chrome", ctx, learning_engine=fake)
        assert result.used_experience is True
        assert "google-chrome" in result.resolved_request
        assert result.confidence == pytest.approx(0.75)

    def test_experience_skipped_for_non_open_commands(self, engine):
        ctx = _ctx()
        fake = _FakeLearningEngine("chrome", "google-chrome", 0.75)

        result = engine.reason("Search for python", ctx, learning_engine=fake)
        assert result.used_experience is False

    def test_experience_none_skipped(self, engine):
        ctx = _ctx()
        result = engine.reason("Open chrome", ctx, learning_engine=None)
        # Should fall through to passthrough
        assert result.used_experience is False

    def test_experience_no_recommendation_skipped(self, engine):
        ctx = _ctx()
        fake = _FakeLearningEngine("firefox", "firefox-esr", 0.5)  # different app

        result = engine.reason("Open chrome", ctx, learning_engine=fake)
        assert result.used_experience is False


# ============================================================
# Priority 4: Raw passthrough
# ============================================================


class TestPriority4Passthrough:
    def test_no_enrichment_passthrough(self, engine):
        ctx = _ctx()
        result = engine.reason("What time is it?", ctx)
        assert result.resolved_request == "What time is it?"
        assert result.used_context is False
        assert result.used_memory is False
        assert result.used_experience is False
        assert result.confidence == 1.0

    def test_passthrough_explanation_set(self, engine):
        ctx = _ctx()
        result = engine.reason("Hello", ctx)
        assert "passthrough" in result.explanation


# ============================================================
# ReasoningResult model
# ============================================================


class TestReasoningResultModel:
    def test_defaults(self):
        r = ReasoningResult(resolved_request="hello")
        assert r.confidence == 1.0
        assert r.used_context is False
        assert r.used_memory is False
        assert r.used_experience is False
        assert r.resolved_entities == []
        assert r.explanation == ""

    def test_custom_values(self):
        entity = ContextEntity(entity_type="application", name="Chrome", value="Chrome")
        r = ReasoningResult(
            resolved_request="Open Chrome",
            confidence=0.9,
            used_context=True,
            resolved_entities=[entity],
            explanation="test",
        )
        assert r.used_context is True
        assert len(r.resolved_entities) == 1
        assert r.explanation == "test"
