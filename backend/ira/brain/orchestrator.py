from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from .intent import IntentClassifier
from .models import AssistantResponse, BrainRequest, BrainResult
from .planner import BrainPlanner
from ..tools import ToolRequest, ToolResult
from ..knowledge.models import KnowledgeGraph
from ..pipeline_log import pipeline_log

# Sprint 7.3 imports (TYPE_CHECKING avoids circular import at startup)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..context.manager import ConversationContextManager
    from ..context.resolver import ReferenceResolver
    from ..context.extractor import ContextExtractor
    from ..reasoning.engine import ReasoningEngine

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
        # Sprint 7.3 additions (optional, backward-compatible)
        context_manager: "ConversationContextManager | None" = None,
        reference_resolver: "ReferenceResolver | None" = None,
        context_extractor: "ContextExtractor | None" = None,
        reasoning_engine: "ReasoningEngine | None" = None,
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

        # Sprint 7.3 components
        self._context_manager = context_manager
        self._reference_resolver = reference_resolver
        self._context_extractor = context_extractor
        self._reasoning_engine = reasoning_engine

    def process(
        self,
        request: BrainRequest,
        run_single_step: SingleStepHandler,
        run_multi_step: MultiStepHandler,
    ) -> BrainResult:
        # ── Step 1: resolve memory shorthands ────────────────────────────────
        pipeline_log("Brain", "Resolving memory shorthands")
        request = self._resolve_memory_references(request)

        # ── Step 2: intent classification ────────────────────────────────────
        pipeline_log("Brain", "Intent classification")
        intent = self._intent_classifier.classify(request)

        # ── Step 3: legacy planning (always runs for backward-compat) ─────────
        pipeline_log("Brain", "Legacy planning")
        plan = self._planner.plan(intent)

        # ── Step 4: Sprint-5 planning pipeline (runs when components injected) ─
        pipeline_log("Brain", "Execution routing")
        if self._goal_detector and self._goal_planner and self._execution_engine:
            pipeline_log("Brain", "Using Sprint 5 planning pipeline")
            response = self._run_planning_pipeline(request, run_single_step, run_multi_step)
        elif plan.is_multi_step:
            pipeline_log("Brain", "Using legacy multi-step")
            response = run_multi_step(request.message, plan.raw_plan)
        else:
            pipeline_log("Brain", "Using legacy single-step")
            response = run_single_step(request.message)

        return BrainResult(response=response, intent=intent, plan=plan)

    def _run_planning_pipeline(
        self,
        request: BrainRequest,
        run_single_step: SingleStepHandler,
        run_multi_step: MultiStepHandler,
    ) -> AssistantResponse:
        """Sprint 5–7.3 pipeline: Context → Resolver → Knowledge → Reasoning → Plan → Execute → ContextUpdate."""
        from ..planning.context import GoalSnapshot, PlanningContext

        # ── Derive conversation_id (use session_id with "default" fallback) ───
        conversation_id = request.session_id or "default"

        # ── Step 0: Retrieve conversation context (Sprint 7.3) ────────────────
        pipeline_log("Context", f"Retrieving context for conversation '{conversation_id}'")
        conv_context = None
        if self._context_manager:
            conv_context = self._context_manager.current(conversation_id)
            pipeline_log(
                "Context",
                f"last_application={conv_context.last_application!r}  "
                f"last_website={conv_context.last_website!r}  "
                f"last_folder={conv_context.last_folder!r}  "
                f"confidence={conv_context.context_confidence:.2f}",
            )

        # ── Step 0b: Reference resolution (Sprint 7.3) ────────────────────────
        active_request = request.message
        reasoning_result = None
        if self._reasoning_engine and conv_context is not None:
            pipeline_log("Resolver", f"Resolving references in: {active_request!r}")
            # Retrieve knowledge subgraph for Priority 2
            knowledge_for_reasoning = self._retrieve_knowledge(active_request)
            reasoning_result = self._reasoning_engine.reason(
                request=active_request,
                context=conv_context,
                knowledge=knowledge_for_reasoning,
                learning_engine=None,  # injected separately if available
            )
            pipeline_log(
                "Reasoning",
                f"explanation={reasoning_result.explanation!r}  "
                f"used_context={reasoning_result.used_context}  "
                f"used_memory={reasoning_result.used_memory}  "
                f"used_experience={reasoning_result.used_experience}  "
                f"confidence={reasoning_result.confidence:.2f}",
            )
            # Brain unwraps resolved_request — Planner receives a plain string
            active_request = reasoning_result.resolved_request
            pipeline_log("Reasoning", f"Final resolved request: {active_request!r}")

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
        goal = self._goal_detector.detect(active_request)

        # Publish Goal Created Event
        if self._event_bus:
            from ..events.models import IRAEvent, EventType
            self._event_bus.publish(IRAEvent(
                event_type=EventType.GOAL_CREATED,
                payload={"goal_id": goal.id, "description": goal.description},
                source_device_id=request.device_id
            ))

        # Step 2: Retrieve structured knowledge (full graph for planner)
        knowledge = self._retrieve_knowledge(active_request)

        # Step 3: Build planning context (Planner receives the resolved request)
        context = PlanningContext(
            request=active_request,
            knowledge=knowledge,
            conversation_history=session.conversation_context if session else [],
            memory={},
            preferences={},
            current_goal=goal,
            session=session,
            device=device,
        )

        # Step 4: Create plan via Planner (unchanged API — receives plain string)
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

        # Step 7 (Sprint 7.3): Update conversation context — only on success ──
        if execution_result.success and self._context_manager and self._context_extractor:
            try:
                delta = self._context_extractor.extract(
                    active_request, conversation_id=conversation_id
                )
                self._context_manager.apply_delta(delta)
                pipeline_log(
                    "ContextUpdate",
                    f"last_application={delta.last_application!r}  "
                    f"last_website={delta.last_website!r}  "
                    f"last_folder={delta.last_folder!r}  "
                    f"confidence={delta.confidence:.2f}",
                )
            except Exception:
                pass  # Context updates never break the response

        # Step 8: Fall back to legacy handlers for actual response
        if execution_result.success:
            return run_single_step(active_request)
        else:
            return run_single_step(active_request)

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
