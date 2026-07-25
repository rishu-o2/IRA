from __future__ import annotations

from types import SimpleNamespace

from ira.brain import AssistantResponse, BrainOrchestrator, BrainPlan, BrainRequest
from ira.memory import MemoryManager, UserProfile


class FakePlanner:
    def plan(self, intent) -> BrainPlan:
        return BrainPlan(raw_plan=SimpleNamespace(steps=[intent.message]), is_multi_step=False)


def test_memory_manager_creates_database_and_round_trips(tmp_path) -> None:
    db_path = tmp_path / "memory.sqlite3"
    manager = MemoryManager(db_path)

    record = manager.remember("preferred_editor", "code", "profile")

    assert db_path.exists()
    assert record.key == "preferred_editor"
    assert manager.recall("preferred_editor") == "code"


def test_memory_manager_updates_searches_and_forgets(tmp_path) -> None:
    manager = MemoryManager(tmp_path / "memory.sqlite3")

    first = manager.remember("preferred_browser", "chrome", "profile")
    second = manager.remember("preferred_browser", "firefox", "profile")
    results = manager.search("browser")

    assert first.created_at == second.created_at
    assert second.updated_at >= first.updated_at
    assert [record.key for record in results] == ["preferred_browser"]
    assert manager.recall("preferred_browser") == "firefox"
    assert manager.forget("preferred_browser") is True
    assert manager.recall("preferred_browser") is None
    assert manager.forget("preferred_browser") is False


def test_user_profile_fields_use_memory_manager(tmp_path) -> None:
    manager = MemoryManager(tmp_path / "memory.sqlite3")
    profile = UserProfile(manager)

    profile.set("preferred_editor", "code")
    profile.set("timezone", "Asia/Calcutta")
    profile.set_current_projects(["IRA", "Memory System"])

    assert profile.preferred_editor == "code"
    assert profile.timezone == "Asia/Calcutta"
    assert profile.current_projects == ["IRA", "Memory System"]


def test_brain_resolves_preference_from_memory(tmp_path) -> None:
    manager = MemoryManager(tmp_path / "memory.sqlite3")
    manager.remember("preferred_editor", "code", "profile")
    brain = BrainOrchestrator(FakePlanner(), memory=manager)
    handled_messages: list[str] = []

    def single_step(message: str) -> AssistantResponse:
        handled_messages.append(message)
        return AssistantResponse(f"handled {message}")

    def multi_step(message: str, plan: object) -> AssistantResponse:
        raise AssertionError("Expected a single-step command")

    result = brain.process(
        BrainRequest("Open my editor"),
        run_single_step=single_step,
        run_multi_step=multi_step,
    )

    assert handled_messages == ["open code"]
    assert result.response.text == "handled open code"
