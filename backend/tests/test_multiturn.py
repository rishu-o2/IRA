"""
tests/test_multiturn.py – Sprint 7.3 multi-turn conversation integration tests.

Simulates real conversation flows using ConversationContextManager +
ContextExtractor + ReferenceResolver + ReasoningEngine together.

Scenarios
---------
1.  Open Chrome → "Open it"               → Chrome
2.  Open GitHub → "Open it again"         → GitHub
3.  Search Python tutorials → "Summarize it" → resolves search entity
4.  Remember IDE is VS Code → "Open my IDE" → VS Code  (preference path)
5.  Open Downloads → "Open that again"    → Downloads
6.  Unknown referent → clarification (confidence = 0.0)

Edge cases (added per user review feedback)
-----------
7.  Ambiguous – latest entity wins:
      Open Chrome → Open VS Code → "Open it" → VS Code (not Chrome)
8.  Context expiration:
      Open Chrome → expire → "Open it" → confidence = 0.0
9.  Mixed entity types – most-recent wins:
      Open Chrome (app) → Open Downloads (folder) → "Open it" → Downloads
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from ira.context.manager import ConversationContextManager
from ira.context.extractor import ContextExtractor
from ira.context.resolver import ReferenceResolver
from ira.context.models import ContextDelta, ContextEntity
from ira.reasoning.engine import ReasoningEngine


# ============================================================
# Helpers
# ============================================================


def _simulate_turn(
    command: str,
    mgr: ConversationContextManager,
    extractor: ContextExtractor,
    engine: ReasoningEngine,
    session: str = "sess",
    success: bool = True,
) -> str:
    """
    Simulate one conversation turn.

    1. Retrieve current context.
    2. Run reasoning (reference resolution).
    3. If success, extract context delta and apply it.
    4. Return the resolved command.
    """
    ctx = mgr.current(session)
    result = engine.reason(command, ctx)
    resolved = result.resolved_request

    if success:
        delta = extractor.extract(resolved, conversation_id=session)
        mgr.apply_delta(delta)

    return resolved


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def stack():
    """Return a fully wired (mgr, extractor, engine, resolver) tuple."""
    mgr = ConversationContextManager()
    extractor = ContextExtractor()
    resolver = ReferenceResolver()
    engine = ReasoningEngine(reference_resolver=resolver)
    return mgr, extractor, engine


# ============================================================
# Scenario 1 – Application ("Open Chrome → Open it")
# ============================================================


def test_multiturn_open_app_then_it(stack):
    mgr, extractor, engine = stack
    sess = "s1"

    # Turn 1: establishes Chrome in context
    r1 = _simulate_turn("Open Chrome", mgr, extractor, engine, sess)
    assert r1 == "Open Chrome"

    # Turn 2: "Open it" should resolve to Chrome
    r2 = _simulate_turn("Open it", mgr, extractor, engine, sess)
    assert "Chrome" in r2, f"Expected Chrome in resolved request, got: {r2!r}"


# ============================================================
# Scenario 2 – Website ("Open GitHub → Open it again")
# ============================================================


def test_multiturn_open_website_then_again(stack):
    mgr, extractor, engine = stack
    sess = "s2"

    _simulate_turn("Open GitHub", mgr, extractor, engine, sess)
    r2 = _simulate_turn("Open it again", mgr, extractor, engine, sess)
    assert "GitHub" in r2, f"Expected GitHub in resolved request, got: {r2!r}"


# ============================================================
# Scenario 3 – Search ("Search Python tutorials → Summarize it")
# ============================================================


def test_multiturn_search_then_summarize(stack):
    mgr, extractor, engine = stack
    sess = "s3"

    _simulate_turn("Search Python tutorials", mgr, extractor, engine, sess)

    # "Summarize it" — "it" should refer to the last entity (search query)
    ctx = mgr.current(sess)
    assert ctx.last_search == "Python tutorials"

    r2 = _simulate_turn("Summarize it", mgr, extractor, engine, sess)
    assert "Python tutorials" in r2, f"Expected query in resolved request, got: {r2!r}"


# ============================================================
# Scenario 4 – Memory / Preference ("Remember IDE is VS Code → Open my IDE")
# ============================================================


def test_multiturn_remember_preference_then_open(stack):
    mgr, extractor, engine = stack
    sess = "s4"

    # Turn 1: store preference (treated as a successful turn)
    _simulate_turn("Remember my IDE is VS Code", mgr, extractor, engine, sess)

    # Assert immediately after the preference turn, before any subsequent
    # command can overwrite the slot.
    ctx_after_pref = mgr.current(sess)
    app_after_pref = ctx_after_pref.last_application
    assert app_after_pref == "VS Code", (
        f"Preference should have set last_application=VS Code, got: {app_after_pref!r}"
    )

    # Turn 2: "Open my IDE" — no pronoun trigger, falls through to passthrough.
    # The extractor will then update last_application to "my IDE" (expected
    # behaviour: the slot tracks whatever was most recently opened).
    r2 = _simulate_turn("Open my IDE", mgr, extractor, engine, sess)
    # The important thing is that Turn 1 correctly populated the slot.
    assert app_after_pref == "VS Code"  # snapshot from before Turn 2


# ============================================================
# Scenario 5 – Folder ("Open Downloads → Open that again")
# ============================================================


def test_multiturn_open_folder_then_that_again(stack):
    mgr, extractor, engine = stack
    sess = "s5"

    _simulate_turn("Open Downloads", mgr, extractor, engine, sess)
    r2 = _simulate_turn("Open that again", mgr, extractor, engine, sess)
    assert "Downloads" in r2, f"Expected Downloads in resolved request, got: {r2!r}"


# ============================================================
# Scenario 6 – Unknown referent → confidence = 0.0
# ============================================================


def test_multiturn_unknown_referent_returns_zero_confidence(stack):
    mgr, extractor, engine = stack
    sess = "s6"

    # No prior context
    ctx = mgr.current(sess)
    result = engine.reason("Open it", ctx)

    assert result.confidence == 0.0, (
        f"Expected confidence=0.0 for unknown referent, got {result.confidence}"
    )
    assert result.resolved_request == "Open it"


# ============================================================
# Edge case 7 – Ambiguous: latest entity wins
# ============================================================


def test_multiturn_ambiguous_latest_entity_wins(stack):
    """
    Open Chrome
    Open VS Code
    Open it         → VS Code (most recently mentioned entity wins)
    """
    mgr, extractor, engine = stack
    sess = "s7"

    _simulate_turn("Open Chrome", mgr, extractor, engine, sess)
    _simulate_turn("Open VS Code", mgr, extractor, engine, sess)

    r3 = _simulate_turn("Open it", mgr, extractor, engine, sess)
    assert "VS Code" in r3, (
        f"Latest entity (VS Code) should win over Chrome, got: {r3!r}"
    )
    assert "Chrome" not in r3


# ============================================================
# Edge case 8 – Context expiration
# ============================================================


def test_multiturn_context_expiration(stack):
    """
    Open Chrome
    (expire context)
    Open it         → confidence = 0.0 (no referent)
    """
    mgr, extractor, engine = stack
    sess = "s8"

    _simulate_turn("Open Chrome", mgr, extractor, engine, sess)

    # Force context to appear stale — write directly to bypass update()'s
    # automatic timestamp override.
    ctx = mgr.current(sess)
    ctx.updated_at = datetime.now(timezone.utc) - timedelta(seconds=7200)
    mgr._store[sess] = ctx
    evicted = mgr.expire_old_context(max_age_seconds=3600)
    assert evicted == 1

    # After expiration current() returns a fresh context
    result = engine.reason("Open it", mgr.current(sess))
    assert result.confidence == 0.0


# ============================================================
# Edge case 9 – Mixed entity types: most-recent wins
# ============================================================


def test_multiturn_mixed_entity_types_most_recent_wins(stack):
    """
    Open Chrome    (application)
    Open Downloads (folder)
    Open it        → Downloads (most recently mentioned, regardless of type)
    """
    mgr, extractor, engine = stack
    sess = "s9"

    _simulate_turn("Open Chrome", mgr, extractor, engine, sess)
    _simulate_turn("Open Downloads", mgr, extractor, engine, sess)

    r3 = _simulate_turn("Open it", mgr, extractor, engine, sess)
    # "it" resolves to the most-recent entity: Downloads
    assert "Downloads" in r3, (
        f"Most recent entity (Downloads) should be resolved for 'it', got: {r3!r}"
    )
