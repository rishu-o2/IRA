"""
session.py – Shared runtime singletons for IRA.

All module-level service instances that were previously scattered across
assistant.py are consolidated here.  Components that need these services
import from this module rather than from assistant.py, breaking the
circular-import hazard and reducing coupling.

DO NOT store per-request or per-user state here.
Instance state (brain, virtual_world, modification_history) remains
owned by IRAAssistant.
"""
from __future__ import annotations

from pathlib import Path

from .memory.context import ContextManager
from .memory.consolidation import MemoryConsolidator
from .memory.long_term import MemoryStore
from .memory.long_term.storage import MemoryStorage
from .memory.manager import LegacyMemoryManager, MemoryManager
from .memory.retrieval import ContextRetriever
from .planner.planner import TaskPlanner
from .execution.executor import TaskExecutor
from .goals.manager import GoalManager
from .suggestions import ProactiveSuggestionEngine

# ---------------------------------------------------------------------------
# Long-term memory
# ---------------------------------------------------------------------------
_MEMORY_PATH = str(
    Path(__file__).resolve().parent / "memory" / "long_term" / "memories.json"
)

memory_store: MemoryStore = MemoryStore(MemoryStorage(_MEMORY_PATH))
memory_manager: LegacyMemoryManager = LegacyMemoryManager(memory_store)
persistent_memory_manager: MemoryManager = MemoryManager()
context_retriever: ContextRetriever = ContextRetriever(memory_store)
memory_consolidator: MemoryConsolidator = MemoryConsolidator()
suggestion_engine: ProactiveSuggestionEngine = ProactiveSuggestionEngine()

# Consolidation throttle – run consolidation every N memory writes.
MEMORY_CONSOLIDATION_INTERVAL: int = 25
_memory_changes_since_consolidation: int = 0

# ---------------------------------------------------------------------------
# Conversation context (rolling history + assistant state)
# ---------------------------------------------------------------------------
context: ContextManager = ContextManager()

# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------
planner: TaskPlanner = TaskPlanner()

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
executor: TaskExecutor = TaskExecutor(handler=None)

# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------
goal_manager: GoalManager = GoalManager()

# ---------------------------------------------------------------------------
# Agent layer (Phase 8.3)
# ---------------------------------------------------------------------------
from .agent.planner import AgentPlanner
from .agent.executor import AgentExecutor

agent_planner: AgentPlanner = AgentPlanner()
_agent_results: dict = {}


def _global_agent_handler(action: str):
    queue = executor.execute([action])
    task = queue.all()[0]
    from .execution.task import TaskStatus
    if task.status == TaskStatus.FAILED:
        raise RuntimeError(task.error)
    _agent_results[action] = task.result
    return task.result


agent_executor: AgentExecutor = AgentExecutor(handler=_global_agent_handler)

# ---------------------------------------------------------------------------
# Mobile server (Phase 6) – initialised lazily in IRAAssistant.__init__
# ---------------------------------------------------------------------------
from .mobile.server import MobileServer
mobile_server: MobileServer | None = None


def get_agent_results() -> dict:
    return _agent_results


def clear_agent_results() -> None:
    _agent_results.clear()


# ---------------------------------------------------------------------------
# Memory-learning helper (called after each successful interaction)
# ---------------------------------------------------------------------------
def learn_from_interaction(message: str, successful: bool) -> None:
    global _memory_changes_since_consolidation

    if not successful:
        return

    remembered = memory_manager.remember(message)
    if not remembered:
        return

    _memory_changes_since_consolidation += len(remembered)
    if _memory_changes_since_consolidation >= MEMORY_CONSOLIDATION_INTERVAL:
        memory_consolidator.consolidate(memory_store)
        _memory_changes_since_consolidation = 0


# ---------------------------------------------------------------------------
# Public goal helpers (backward-compat with server.py / external callers)
# ---------------------------------------------------------------------------
def get_goal(goal_id: str):
    return goal_manager.get(goal_id)


def get_all_goals():
    return goal_manager.all()


def get_goal_manager() -> GoalManager:
    return goal_manager
