from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ira.brain import AssistantResponse, BrainOrchestrator, BrainPlan, BrainRequest
from ira.router import ToolRouter
from ira.tools import (
    BrowserTool,
    CommunicationTool,
    DesktopTools,
    FilesystemTool,
    MediaTool,
    SystemTool,
    ToolRegistry,
    ToolRequest,
    ToolResult,
    tool_registry,
)


@dataclass
class FakeTool:
    name: str
    command: str = "run"
    response: str = "done"

    def supports(self, request: ToolRequest) -> bool:
        return request.intent == self.name and request.command == self.command

    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(self.response, tool_name=self.name)

    def metadata(self) -> dict[str, Any]:
        return {"name": self.name}


class FailingTool(FakeTool):
    def execute(self, request: ToolRequest) -> ToolResult:
        raise RuntimeError("boom")


class SingleStepPlanner:
    def plan(self, intent: object) -> BrainPlan:
        return BrainPlan(raw_plan=object(), is_multi_step=False)


def test_tool_registry_discovers_registered_tools() -> None:
    tool = FakeTool("fake")
    registry = ToolRegistry([tool])

    assert registry.discover() == [tool]
    assert registry.get("fake") is tool


def test_tool_registry_replaces_tools_by_metadata_name() -> None:
    first = FakeTool("fake", response="old")
    second = FakeTool("fake", response="new")
    registry = ToolRegistry([first])

    registry.register(second)

    assert registry.discover() == [second]


def test_tool_router_selects_and_executes_matching_tool() -> None:
    registry = ToolRegistry([FakeTool("fake", response="routed")])
    router = ToolRouter(registry)

    result = router.execute(ToolRequest("fake", "run"))

    assert result.handled is True
    assert result.text == "routed"
    assert result.tool_name == "fake"


def test_tool_router_returns_unhandled_result_when_no_tool_matches() -> None:
    router = ToolRouter(ToolRegistry())

    result = router.execute(ToolRequest("missing", "run"))

    assert result.handled is False
    assert "No tool can handle missing:run" in result.text


def test_tool_router_normalizes_tool_exceptions() -> None:
    router = ToolRouter(ToolRegistry([FailingTool("fake")]))

    result = router.execute(ToolRequest("fake", "run"))

    assert result.handled is False
    assert result.text == "boom"
    assert result.tool_name == "fake"
    assert result.metadata["error_type"] == "RuntimeError"


def test_default_registry_registers_desktop_tool() -> None:
    desktop = tool_registry.get("desktop")

    assert isinstance(desktop, DesktopTools)
    assert tool_registry.select(ToolRequest("desktop", "open_app", {"app_name": "notepad"})) is desktop


def test_default_registry_registers_capability_tools() -> None:
    assert isinstance(tool_registry.get("browser"), BrowserTool)
    assert isinstance(tool_registry.get("media"), MediaTool)
    assert isinstance(tool_registry.get("system"), SystemTool)
    assert isinstance(tool_registry.get("filesystem"), FilesystemTool)
    assert isinstance(tool_registry.get("communication"), CommunicationTool)


def test_browser_tool_opens_websites_and_searches(monkeypatch) -> None:
    opened: list[str] = []

    monkeypatch.setattr("ira.actions.webbrowser.open", opened.append)
    browser = BrowserTool()

    open_result = browser.execute(ToolRequest("browser", "open_website", {"url": "example.com"}))
    search_result = browser.execute(ToolRequest("browser", "search_web", {"query": "python tutorials"}))

    assert open_result == ToolResult("Opening https://example.com", tool_name="browser")
    assert search_result == ToolResult("Searching Google for python tutorials", tool_name="browser")
    assert opened == ["https://example.com", "https://www.google.com/search?q=python+tutorials"]


def test_media_tool_plays_youtube_search(monkeypatch) -> None:
    opened: list[str] = []

    monkeypatch.setattr("ira.actions.webbrowser.open", opened.append)
    media = MediaTool()

    result = media.execute(ToolRequest("media", "play_youtube_search", {"query": "lofi"}))

    assert result == ToolResult("Searching YouTube for lofi", tool_name="media")
    assert opened == ["https://www.youtube.com/results?search_query=lofi"]


def test_system_tool_routes_volume_and_brightness(monkeypatch) -> None:
    key_calls: list[tuple[object, ...]] = []
    brightness_calls: list[str] = []

    monkeypatch.setattr("ira.actions.os.name", "nt")
    monkeypatch.setattr("ira.actions.ctypes.windll.user32.keybd_event", lambda *args: key_calls.append(args))
    monkeypatch.setattr("ira.actions.subprocess.run", lambda cmd, **kwargs: brightness_calls.append(cmd))
    system = SystemTool()

    volume_result = system.execute(ToolRequest("system", "volume_up"))
    brightness_result = system.execute(ToolRequest("system", "set_brightness", {"level": 55}))

    assert volume_result == ToolResult("Increasing volume.", tool_name="system")
    assert brightness_result == ToolResult("Screen brightness set to 55%.", tool_name="system")
    assert len(key_calls) == 2
    assert "WmiSetBrightness(0, 55)" in brightness_calls[0]


def test_filesystem_tool_opens_known_folders(monkeypatch) -> None:
    opened: list[object] = []

    monkeypatch.setattr("ira.actions.os.startfile", opened.append)
    filesystem = FilesystemTool()

    result = filesystem.execute(ToolRequest("filesystem", "open_known_folder", {"folder_name": "downloads"}))

    assert result.text.endswith("Downloads")
    assert result.tool_name == "filesystem"
    assert opened


def test_communication_tool_uses_existing_call_behavior(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("ira.actions.open_app", lambda app_name: calls.append(app_name) or f"Opening {app_name}")
    communication = CommunicationTool()

    result = communication.execute(ToolRequest("communication", "call", {"app_name": "skype"}))

    assert result == ToolResult("Opening skype", tool_name="communication")
    assert calls == ["skype"]


def test_registry_selects_registered_capability_by_intent_and_command() -> None:
    assert isinstance(tool_registry.select(ToolRequest("browser", "search_web", {"query": "x"})), BrowserTool)
    assert isinstance(tool_registry.select(ToolRequest("media", "play_youtube_search", {"query": "x"})), MediaTool)
    assert isinstance(tool_registry.select(ToolRequest("system", "get_system_stats")), SystemTool)
    assert isinstance(tool_registry.select(ToolRequest("filesystem", "open_known_folder", {"folder_name": "downloads"})), FilesystemTool)
    assert isinstance(tool_registry.select(ToolRequest("communication", "call")), CommunicationTool)


def test_brain_executes_tools_through_injected_router() -> None:
    router = ToolRouter(ToolRegistry([FakeTool("fake", response="from router")]))
    brain = BrainOrchestrator(SingleStepPlanner(), tool_router=router)

    result = brain.execute_tool(ToolRequest("fake", "run"))

    assert result == ToolResult("from router", tool_name="fake")


def test_brain_request_flow_still_uses_legacy_callback() -> None:
    brain = BrainOrchestrator(SingleStepPlanner())

    result = brain.process(
        BrainRequest("hello"),
        run_single_step=lambda message: AssistantResponse(f"handled {message}"),
        run_multi_step=lambda message, plan: AssistantResponse("multi"),
    )

    assert result.response == AssistantResponse("handled hello")
