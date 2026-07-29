"""
assistant.py – Thin transport adapter for IRA.

Sprint 3.3 refactored this file from a 1,063-line monolith into a
focused transport adapter.  Its only responsibilities are:

    1. Receive a user message.
    2. Prepare a BrainRequest.
    3. Invoke the Brain (which delegates to RequestHandler).
    4. Return an AssistantResponse.

All business logic now lives in focused modules:

    session.py           – shared runtime singletons
    normalizer.py        – command normalization
    context_resolver.py  – pronoun / reference resolution
    memory/handler.py    – memory read / write / list / format
    self_modification.py – <write_file> / <patch_file> processing
    request_handler.py   – full single-step dispatch pipeline
    skills/preference.py – preference-aware routing
    skills/virtual_world_skill.py – virtual world interactions
    skills/modification_skill.py  – modification introspection
"""
from __future__ import annotations

import time

from .brain import AssistantResponse, BrainOrchestrator, BrainPlanner, BrainRequest
from .context_resolver import ContextResolver
from .conversation import GeminiConversation
from .memory.handler import MemoryHandler
from .memory.retrieval import Context
from .normalizer import CommandNormalizer
from .request_handler import RequestHandler
from .self_modification import SelfModificationEngine
from .skills import build_registry
from .virtual_world import VirtualWorld

from . import session


class IRAAssistant:
    """Transport adapter: receives requests, invokes Brain, returns responses."""

    def __init__(self, conversation: GeminiConversation | None = None) -> None:
        self.conversation = conversation or GeminiConversation()
        self.virtual_world = VirtualWorld()
        self.recent_modifications: list = []
        self.modification_history: list = []
        self._memory_context: Context = Context(())
        self._llm_time: float = 0.0

        # Build the skill registry with injected dependencies.
        self._registry = build_registry(
            virtual_world=self.virtual_world,
            modification_history=self.modification_history,
            context_retriever=session.context_retriever,
        )

        # Assemble the RequestHandler (owns _handle_internal logic).
        self._memory_context_ref: list = [self._memory_context]
        self._request_handler = RequestHandler(
            normalizer=CommandNormalizer(),
            context_resolver=ContextResolver(session.context),
            memory_handler=MemoryHandler(
                memory_store=session.memory_store,
                memory_manager=session.memory_manager,
                persistent_memory_manager=session.persistent_memory_manager,
                memory_consolidator=session.memory_consolidator,
                suggestion_engine=session.suggestion_engine,
            ),
            skill_registry=self._registry,
            self_modification_engine=SelfModificationEngine(),
            conversation=self.conversation,
            recent_modifications=self.recent_modifications,
            modification_history=self.modification_history,
            virtual_world=self.virtual_world,
            memory_context_ref=self._memory_context_ref,
        )

        # Brain orchestration.
        self.brain = BrainOrchestrator(
            BrainPlanner(session.agent_planner),
            tool_router=session.executor,
        )

        # Wire the task executor's handler so multi-step plans can call back.
        def _exec_handler(cmd: str):
            resp = self._request_handler.handle(cmd)
            if not resp.handled:
                raise RuntimeError(resp.text)
            return resp

        session.executor.handler = _exec_handler

        # Initialise MobileServer singleton lazily.
        if session.mobile_server is None:
            from .mobile.server import MobileServer
            session.mobile_server = MobileServer(self)

    # ------------------------------------------------------------------
    # Backward-compatible delegate methods (used by existing tests)
    # ------------------------------------------------------------------

    def _normalize_command(self, message: str) -> str:
        """Delegate to CommandNormalizer for backward compat."""
        return self._request_handler._normalizer.normalize(message)

    def _apply_self_modifications(self, reply_text: str) -> list[str]:
        """Delegate to SelfModificationEngine for backward compat."""
        return self._request_handler._self_mod.apply(
            reply_text,
            self.recent_modifications,
            self.modification_history,
            self.virtual_world,
        )

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def handle(self, message: str) -> AssistantResponse:
        """Profiling wrapper: delegates to Brain and records timing + memory.

        This is the single public API that CLI, HTTP server, and Electron
        all call.
        """
        from .pipeline_log import pipeline_log
        pipeline_log("Assistant", f"Handling: '{message}'")

        self._memory_context = session.context_retriever.retrieve(message)
        self._memory_context_ref[0] = self._memory_context

        # Record user turn for context tracking.
        session.context.remember_user(message)

        goal = session.goal_manager.create(message)

        def run_single_step(current_message: str) -> AssistantResponse:
            session.goal_manager.start(goal.id)
            t_start = time.perf_counter()
            response = self._request_handler.handle(current_message)
            t_end = time.perf_counter()

            llm_ms = self._request_handler.llm_time * 1000
            total_ms = (t_end - t_start) * 1000
            intent_ms = total_ms - llm_ms

            print(f"[PERF] Command processing: {intent_ms:.0f} ms")
            print(f"[PERF] Gemini response generation: {llm_ms:.0f} ms")

            if response.handled:
                session.goal_manager.complete(goal.id)
            else:
                session.goal_manager.fail(goal.id, response.text)

            session.context.remember_assistant(response.text)
            session.learn_from_interaction(current_message, response.handled)

            return response

        def run_multi_step(current_message: str, plan: object) -> AssistantResponse:
            session.goal_manager.start(goal.id)

            session.clear_agent_results()
            executed_plan = session.agent_executor.execute(plan)

            results = []
            overall_handled = True

            from .agent.step import StepStatus
            for step in executed_plan.all():
                if step.status == StepStatus.FAILED:
                    results.append(f"\u2717 {step.error}")
                    overall_handled = False
                elif step.status == StepStatus.SKIPPED:
                    pass
                else:
                    res_text = session.get_agent_results().get(step.action, "")
                    results.append(f"\u2713 {res_text}")

            if executed_plan.failed():
                failed_msgs = [str(s.error) for s in executed_plan.failed()]
                session.goal_manager.fail(goal.id, "; ".join(failed_msgs))
            else:
                session.goal_manager.complete(goal.id)

            combined_text = "\n".join(results)
            combined_response = AssistantResponse(combined_text, handled=overall_handled)

            session.context.remember_assistant(combined_response.text)
            session.learn_from_interaction(current_message, combined_response.handled)

            return combined_response

        brain_result = self.brain.process(
            BrainRequest(message),
            run_single_step=run_single_step,
            run_multi_step=run_multi_step,
        )
        return brain_result.response


# ---------------------------------------------------------------------------
# Backward-compatible public accessors (used by server.py, cli.py, tests)
# ---------------------------------------------------------------------------

def get_context():
    """Return the shared ContextManager instance."""
    return session.context


def get_last_command() -> str | None:
    """Return the most recent user command."""
    return session.context.state.last_command


def get_last_app() -> str | None:
    """Return the most recently referenced application name."""
    return session.context.state.last_app


def get_goal(goal_id: str):
    return session.get_goal(goal_id)


def get_all_goals():
    return session.get_all_goals()


def get_goal_manager():
    return session.get_goal_manager()


def get_skill_registry():
    """Return the shared SkillRegistry singleton (read-only accessor).

    NOTE: This returns None until an IRAAssistant is constructed.
    For test compatibility, prefer accessing the registry through the
    assistant instance.
    """
    # The registry is instance-level after the refactor.  This shim
    # remains for backward compat but callers should migrate.
    return None


def start_mobile_server():
    if session.mobile_server:
        session.mobile_server.start()


def stop_mobile_server():
    if session.mobile_server:
        session.mobile_server.stop()


def mobile_server_running() -> bool:
    if session.mobile_server:
        return session.mobile_server.is_running()
    return False


# Re-export for any external code importing from assistant
_memory_store = session.memory_store
