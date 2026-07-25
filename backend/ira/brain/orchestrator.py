from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from .intent import IntentClassifier
from .models import AssistantResponse, BrainRequest, BrainResult
from .planner import BrainPlanner
from ..tools import ToolRequest, ToolResult
from ..knowledge.models import KnowledgeGraph

SingleStepHandler = Callable[[str], AssistantResponse]
MultiStepHandler = Callable[[str, object], AssistantResponse]


class MemoryReader(Protocol):
    def recall(self, key: str) -> str | None:
        ...


class MemoryWriter(Protocol):
    def remember(self, key: str, value: str, category: str) -> object:
        ...


class ToolExecutor(Protocol):
    def execute(self, request: ToolRequest) -> ToolResult:
        ...


class BrainOrchestrator:
    """Coordinates intent, goal detection, planning, execution, and memory update."""

    def __init__(
        self,
        planner: BrainPlanner,
        intent_classifier: IntentClassifier | None = None,
        memory: MemoryReader | None = None,
        tool_router: ToolExecutor | None = None,
        # Sprint 5 additions (optional, backward-compatible)
        goal_planner=None,
        execution_engine=None,
        goal_detector=None,
        memory_writer: MemoryWriter | None = None,
        # Sprint 6 additions (optional, backward-compatible)
        device_manager=None,
        session_manager=None,
        event_bus=None,
        notification_dispatcher=None,
    ) -> None:
        self._planner = planner
        self._intent_classifier = intent_classifier or IntentClassifier()
        self._memory = memory
        self._tool_router = tool_router

        # Sprint 5 components (all optional so existing callers are unaffected)
        self._goal_planner = goal_planner
        self._execution_engine = execution_engine
        self._goal_detector = goal_detector
        self._memory_writer = memory_writer

        # Sprint 6 components
        self._device_manager = device_manager
        self._session_manager = session_manager
        self._event_bus = event_bus
        self._notification_dispatcher = notification_dispatcher

    def process(
        self,
        request: BrainRequest,
        run_single_step: SingleStepHandler,
        run_multi_step: MultiStepHandler,
    ) -> BrainResult:
        # ── Step 1: resolve memory shorthands ────────────────────────────────
        request = self._resolve_memory_references(request)

        # ── Step 2: intent classification ────────────────────────────────────
        intent = self._intent_classifier.classify(request)

        # ── Step 3: legacy planning (always runs for backward-compat) ─────────
        plan = self._planner.plan(intent)

        # ── Step 4: Sprint-5 planning pipeline (runs when components injected) ─
        if self._goal_detector and self._goal_planner and self._execution_engine:
            response = self._run_planning_pipeline(request, run_single_step, run_multi_step)
        elif plan.is_multi_step:
            response = run_multi_step(request.message, plan.raw_plan)
        else:
            response = run_single_step(request.message)

        return BrainResult(response=response, intent=intent, plan=plan)

    def _run_planning_pipeline(
        self,
        request: BrainRequest,
        run_single_step: SingleStepHandler,
        run_multi_step: MultiStepHandler,
    ) -> AssistantResponse:
        """Sprint 5 pipeline: Goal Detection → Knowledge → Context → Plan → Execute → Memory."""
        from ..planning.context import GoalSnapshot, PlanningContext

        # Extract device and session
        device = None
        session = None
        if self._device_manager and request.device_id:
            device = self._device_manager._registry.get(request.device_id)
        if self._session_manager:
            if request.session_id:
                session = self._session_manager.restore(request.session_id)
            elif request.device_id:
                session = self._session_manager.get_by_device(request.device_id)

        # Step 1: Detect goal
        goal = self._goal_detector.detect(request.message)
        
        # Publish Goal Created Event
        if self._event_bus:
            from ..events.models import IRAEvent, EventType
            self._event_bus.publish(IRAEvent(
                event_type=EventType.GOAL_CREATED, 
                payload={"goal_id": goal.id, "description": goal.description},
                source_device_id=request.device_id
            ))

        # Step 2: Retrieve structured knowledge
        knowledge = self._retrieve_knowledge(request.message)

        # Step 3: Build planning context
        context = PlanningContext(
            request=request.message,
            knowledge=knowledge,
            conversation_history=session.conversation_context if session else [],
            memory={},
            preferences={},
            current_goal=goal,
            session=session,
            device=device,
        )

        # Step 4: Create plan via Planner
        planning_result = self._goal_planner.plan(context)

        # Step 5: Execute via ExecutionEngine
        execution_result = self._execution_engine.execute(planning_result)

        # Publish Goal Completed Event
        if self._event_bus:
            from ..events.models import IRAEvent, EventType
            self._event_bus.publish(IRAEvent(
                event_type=EventType.GOAL_COMPLETED, 
                payload={"goal_id": goal.id, "success": execution_result.success},
                source_device_id=request.device_id
            ))

        # Step 6: Persist GoalSnapshot to memory
        if self._memory_writer:
            try:
                snapshot = GoalSnapshot.from_goal(
                    goal,
                    result_summary=execution_result.summary,
                    duration=execution_result.execution_time,
                )
                self._memory_writer.remember(
                    key=f"goal_{snapshot.goal_id}",
                    value=json.dumps({
                        "description": snapshot.description,
                        "status": snapshot.status.value,
                        "result_summary": snapshot.result_summary,
                        "duration": snapshot.duration,
                    }),
                    category="goal",
                )
            except Exception:
                pass  # Never let memory writes break the response

        # Step 7: Fall back to legacy handlers for actual LLM response
        if execution_result.success:
            return run_single_step(request.message)
        else:
            return run_single_step(request.message)

    def _retrieve_knowledge(self, text: str) -> KnowledgeGraph:
        """Retrieve a knowledge subgraph relevant to the request."""
        # Stub returning an empty graph; future RAG/summarization hooks in here
        return KnowledgeGraph()

    def execute_tool(self, request: ToolRequest) -> ToolResult:
        if self._tool_router is None:
            return ToolResult("No tool router is configured.", handled=False)
        return self._tool_router.execute(request)

    def _resolve_memory_references(self, request: BrainRequest) -> BrainRequest:
        if self._memory is None:
            return request

        normalized = " ".join(request.message.strip().casefold().split())
        preference_commands = {
            "open my editor": ("preferred_editor", "open {value}"),
            "open editor": ("preferred_editor", "open {value}"),
            "open my browser": ("preferred_browser", "open {value}"),
            "open browser": ("preferred_browser", "open {value}"),
            "open my terminal": ("preferred_terminal", "open {value}"),
            "open terminal": ("preferred_terminal", "open {value}"),
            "play music": ("preferred_music_player", "open {value}"),
            "play my music": ("preferred_music_player", "open {value}"),
        }
        match = preference_commands.get(normalized)
        if match is None:
            return request

        key, template = match
        value = self._memory.recall(key)
        if not value:
            return request
        return BrainRequest(template.format(value=value))
