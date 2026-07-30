"""
tests/test_context.py – Sprint 7.3 context layer tests.

Covers:
    ConversationContextManager  – create, update, current, clear,
                                   apply_delta, remember_entity,
                                   recent_entities, expire_old_context
    ContextExtractor            – application, website, folder, file,
                                   preference extraction (returns ContextDelta)
    ReferenceResolver           – resolve "it", "that", "again",
                                   "same app", "same folder", unknown → conf=0
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from ira.context.models import ConversationContext, ContextDelta, ContextEntity
from ira.context.manager import ConversationContextManager
from ira.context.extractor import ContextExtractor
from ira.context.resolver import ReferenceResolver, REFERENCE_MAP


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mgr() -> ConversationContextManager:
    return ConversationContextManager()


@pytest.fixture
def extractor() -> ContextExtractor:
    return ContextExtractor()


@pytest.fixture
def resolver() -> ReferenceResolver:
    return ReferenceResolver()


@pytest.fixture
def ctx_with_app(mgr: ConversationContextManager) -> ConversationContext:
    """A context that already knows about Chrome."""
    delta = ContextDelta(
        conversation_id="sess-1",
        last_application="Chrome",
        new_entities=[
            ContextEntity(entity_type="application", name="Chrome", value="Chrome")
        ],
        confidence=1.0,
    )
    return mgr.apply_delta(delta)


# ============================================================
# ConversationContextManager
# ============================================================


class TestConversationContextManager:
    def test_create_returns_fresh_context(self, mgr):
        ctx = mgr.create("sess-a")
        assert ctx.conversation_id == "sess-a"
        assert ctx.last_application is None
        assert ctx.context_confidence == 1.0

    def test_current_creates_if_missing(self, mgr):
        ctx = mgr.current("sess-new")
        assert ctx.conversation_id == "sess-new"

    def test_current_returns_existing(self, mgr):
        ctx1 = mgr.create("sess-b")
        ctx1.last_application = "Firefox"
        mgr.update(ctx1)
        ctx2 = mgr.current("sess-b")
        assert ctx2.last_application == "Firefox"

    def test_clear_removes_context(self, mgr):
        mgr.create("sess-c")
        mgr.clear("sess-c")
        # After clear, current() should create a fresh one
        ctx = mgr.current("sess-c")
        assert ctx.last_application is None

    def test_apply_delta_updates_slots(self, mgr):
        delta = ContextDelta(
            conversation_id="sess-d",
            last_application="VS Code",
            last_website=None,
            confidence=0.9,
        )
        ctx = mgr.apply_delta(delta)
        assert ctx.last_application == "VS Code"
        assert ctx.context_confidence == 0.9

    def test_apply_delta_does_not_overwrite_none_fields(self, mgr):
        # First delta sets the website
        d1 = ContextDelta(conversation_id="sess-e", last_website="GitHub", confidence=1.0)
        mgr.apply_delta(d1)
        # Second delta only touches application — website must remain
        d2 = ContextDelta(conversation_id="sess-e", last_application="Chrome", confidence=1.0)
        ctx = mgr.apply_delta(d2)
        assert ctx.last_website == "GitHub"
        assert ctx.last_application == "Chrome"

    def test_remember_entity_appends(self, mgr):
        entity = ContextEntity(entity_type="application", name="Chrome", value="Chrome")
        mgr.remember_entity("sess-f", entity)
        ctx = mgr.current("sess-f")
        assert len(ctx.active_entities) == 1
        assert ctx.active_entities[0].name == "Chrome"

    def test_recent_entities_newest_first(self, mgr):
        for name in ["Chrome", "VS Code", "Spotify"]:
            mgr.remember_entity("sess-g", ContextEntity(entity_type="application", name=name, value=name))
        recent = mgr.recent_entities("sess-g", limit=2)
        assert recent[0].name == "Spotify"
        assert recent[1].name == "VS Code"

    def test_expire_old_context_removes_stale(self, mgr):
        ctx = mgr.create("sess-old")
        # Force the updated_at to be old — write directly to bypass update()'s
        # automatic timestamp so the expiry check sees the stale time.
        ctx.updated_at = datetime.now(timezone.utc) - timedelta(seconds=7200)
        mgr._store["sess-old"] = ctx
        evicted = mgr.expire_old_context(max_age_seconds=3600)
        assert evicted == 1
        # current() should now return a fresh context
        fresh = mgr.current("sess-old")
        assert fresh.last_application is None

    def test_expire_leaves_fresh_context_intact(self, mgr):
        mgr.create("sess-fresh")
        evicted = mgr.expire_old_context(max_age_seconds=3600)
        assert evicted == 0


# ============================================================
# ContextExtractor
# ============================================================


class TestContextExtractor:
    def test_extract_application(self, extractor):
        delta = extractor.extract("Open Chrome")
        assert delta.last_application == "Chrome"
        assert delta.last_website is None
        assert len(delta.new_entities) == 1
        assert delta.new_entities[0].entity_type == "application"

    def test_extract_application_vs_code(self, extractor):
        delta = extractor.extract("Open VS Code")
        assert delta.last_application == "VS Code"

    def test_extract_website_by_name(self, extractor):
        delta = extractor.extract("Open GitHub")
        assert delta.last_website == "GitHub"
        assert delta.new_entities[0].entity_type == "website"

    def test_extract_website_by_url(self, extractor):
        delta = extractor.extract("Open github.com")
        assert delta.last_website == "github.com"

    def test_extract_folder(self, extractor):
        delta = extractor.extract("Open Downloads")
        assert delta.last_folder == "Downloads"
        assert delta.new_entities[0].entity_type == "folder"

    def test_extract_file_with_extension(self, extractor):
        delta = extractor.extract("Open report.pdf")
        assert delta.last_file == "report.pdf"
        assert delta.new_entities[0].entity_type == "file"

    def test_extract_search_query(self, extractor):
        delta = extractor.extract("Search Python tutorials")
        assert delta.last_search == "Python tutorials"
        assert delta.new_entities[0].entity_type == "search"

    def test_extract_preference_ide(self, extractor):
        delta = extractor.extract("Remember my IDE is VS Code")
        assert delta.last_application == "VS Code"
        entity = delta.new_entities[0]
        assert entity.entity_type == "preference"
        assert entity.name == "ide"
        assert entity.value == "VS Code"

    def test_extract_preference_favourite_ide(self, extractor):
        delta = extractor.extract("My favourite IDE is PyCharm")
        assert delta.last_application == "PyCharm"

    def test_extract_no_match_returns_empty_delta(self, extractor):
        delta = extractor.extract("What is the weather today?")
        assert delta.last_application is None
        assert delta.last_website is None
        assert delta.last_folder is None
        assert delta.last_file is None
        assert delta.last_search is None
        assert delta.new_entities == []


# ============================================================
# ReferenceResolver
# ============================================================


class TestReferenceResolver:
    def _ctx(self, **kwargs) -> ConversationContext:
        return ConversationContext(conversation_id="t", **kwargs)

    def test_resolve_it_to_application(self, resolver):
        entity = ContextEntity(entity_type="application", name="Chrome", value="Chrome")
        ctx = self._ctx(last_application="Chrome", active_entities=[entity])
        result = resolver.resolve("Open it", ctx)
        assert result.resolved_text == "Open Chrome"
        assert result.confidence == 1.0
        assert result.was_resolved

    def test_resolve_that_to_last_entity(self, resolver):
        entity = ContextEntity(entity_type="folder", name="Downloads", value="Downloads")
        ctx = self._ctx(last_folder="Downloads", active_entities=[entity])
        result = resolver.resolve("Open that", ctx)
        assert "Downloads" in result.resolved_text
        assert result.was_resolved

    def test_resolve_again_to_last_entity(self, resolver):
        entity = ContextEntity(entity_type="website", name="GitHub", value="GitHub")
        ctx = self._ctx(last_website="GitHub", active_entities=[entity])
        result = resolver.resolve("Open GitHub again", ctx)
        assert result.was_resolved
        assert "GitHub" in result.resolved_text

    def test_resolve_same_app(self, resolver):
        entity = ContextEntity(entity_type="application", name="VS Code", value="VS Code")
        ctx = self._ctx(last_application="VS Code", active_entities=[entity])
        result = resolver.resolve("Open same app", ctx)
        assert "VS Code" in result.resolved_text
        assert result.was_resolved

    def test_resolve_same_folder(self, resolver):
        entity = ContextEntity(entity_type="folder", name="Downloads", value="Downloads")
        ctx = self._ctx(last_folder="Downloads", active_entities=[entity])
        result = resolver.resolve("Open same folder", ctx)
        assert "Downloads" in result.resolved_text

    def test_resolve_unknown_returns_zero_confidence(self, resolver):
        ctx = self._ctx()  # empty context
        result = resolver.resolve("Open it", ctx)
        assert result.confidence == 0.0
        assert not result.was_resolved
        assert result.resolved_text == "Open it"

    def test_no_trigger_passthrough(self, resolver):
        ctx = self._ctx(last_application="Chrome")
        result = resolver.resolve("Open Chrome", ctx)
        assert not result.was_resolved
        assert result.resolved_text == "Open Chrome"
        assert result.confidence == 1.0

    def test_reference_map_covers_all_generic_triggers(self):
        generic_triggers = {"it", "that", "this", "them", "those", "again", "there", "same one"}
        for trigger in generic_triggers:
            assert trigger in REFERENCE_MAP, f"Trigger {trigger!r} missing from REFERENCE_MAP"

    def test_reference_map_typed_triggers(self):
        assert REFERENCE_MAP["same app"] == "last_application"
        assert REFERENCE_MAP["same website"] == "last_website"
        assert REFERENCE_MAP["same folder"] == "last_folder"
        assert REFERENCE_MAP["same file"] == "last_file"

    def test_context_confidence_propagated(self, resolver):
        entity = ContextEntity(entity_type="application", name="Spotify", value="Spotify")
        ctx = self._ctx(
            last_application="Spotify",
            active_entities=[entity],
            context_confidence=0.8,
        )
        result = resolver.resolve("Open it", ctx)
        assert result.confidence == 0.8
