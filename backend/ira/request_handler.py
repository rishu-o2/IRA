"""
request_handler.py – Request lifecycle handler for IRA.

Extracted from IRAAssistant._handle_internal.  This module owns the
full single-step request lifecycle:

    normalize → resolve context → memory commands → greeting set →
    sensitivity guard → memory answers → skill dispatch → LLM fallback

RequestHandler does NOT perform planning — that remains the
responsibility of BrainOrchestrator.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .actions import ActionError
from .brain.models import AssistantResponse
from .context_resolver import ContextResolver
from .conversation import ConversationError, GeminiConversation
from .memory.handler import MemoryHandler
from .memory.retrieval import Context
from .normalizer import CommandNormalizer
from .self_modification import SelfModificationEngine
from .skills.registry import SkillRegistry

if TYPE_CHECKING:
    from .virtual_world import VirtualWorld

# Wake / greeting commands that return a canned response.
_WAKE_COMMANDS: frozenset[str] = frozenset({
    "date",
    "what date is it",
    "open ira",
    "wake ira",
    "wake up ira",
    "activate ira",
    "ira",
    "open my laptop",
    "wake my laptop",
    "wake laptop",
    "open laptop",
    "activate laptop",
    "activate my laptop",
})


class RequestHandler:
    """Processes a single command through the full dispatch pipeline.

    This is the callable that BrainOrchestrator invokes for each
    single-step request.
    """

    def __init__(
        self,
        *,
        normalizer: CommandNormalizer,
        context_resolver: ContextResolver,
        memory_handler: MemoryHandler,
        skill_registry: SkillRegistry,
        self_modification_engine: SelfModificationEngine,
        conversation: GeminiConversation,
        # Mutable state owned by IRAAssistant — passed by reference.
        recent_modifications: list,
        modification_history: list,
        virtual_world: "VirtualWorld",
        # Pre-retrieved memory context (set before each call by handle()).
        memory_context_ref: list,   # single-element list used as a mutable reference
    ) -> None:
        self._normalizer = normalizer
        self._ctx_resolver = context_resolver
        self._memory = memory_handler
        self._registry = skill_registry
        self._self_mod = self_modification_engine
        self._conversation = conversation
        self._recent_mods = recent_modifications
        self._mod_history = modification_history
        self._virtual_world = virtual_world
        self._memory_context_ref = memory_context_ref
        self._llm_time: float = 0.0

    @property
    def llm_time(self) -> float:
        """Seconds spent in the LLM during the most recent handle() call."""
        return self._llm_time

    def handle(self, message: str) -> AssistantResponse:
        """Full single-step request lifecycle."""
        command = self._normalizer.normalize(message)
        lowered = command.lower()
        self._recent_mods.clear()
        self._llm_time = 0.0

        if not command:
            return AssistantResponse(
                "I'm here. Tell me what you want to do.", handled=False
            )

        # 1. Context resolution (pronoun rewriting).
        ctx_result = self._ctx_resolver.resolve(command, lowered)
        if isinstance(ctx_result, AssistantResponse):
            return ctx_result
        command, lowered = ctx_result

        # 2. Memory commands (remember / forget / show).
        memory_command = self._memory.handle_command(command, lowered)
        if memory_command is not None:
            return memory_command

        # 3. Memory statements (implicit learning).
        memory_statement = self._memory.handle_statement(command)
        if memory_statement is not None:
            return memory_statement

        # 4. Wake / greeting set.
        if lowered in _WAKE_COMMANDS:
            return AssistantResponse("Hello sir. I am awake and ready.")

        # 5. Sensitivity guard.
        if self._normalizer.looks_sensitive_or_unsupported(lowered):
            return AssistantResponse(
                "I cannot complete that action yet. I can talk, open apps and "
                "websites, search Google, play YouTube results, and open files "
                "or folders.",
                handled=False,
            )

        # 6. Memory-based answers.
        memory_ctx: Context = self._memory_context_ref[0]
        memory_answer = self._memory.answer_from_context(command, lowered, memory_ctx)
        if memory_answer is not None:
            return memory_answer

        # 7. Skill dispatch (includes preference, virtual world, modification, etc.)
        try:
            skill = self._registry.dispatch(command)
            if skill is not None:
                print(f"[SKILL] Routing '{command}' \u2192 {skill.name}")
                skill_result = skill.execute(command)
                if isinstance(skill_result, AssistantResponse):
                    return skill_result
                return AssistantResponse(str(skill_result))
        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        # 8. LLM fallback.
        try:
            t_llm_start = time.perf_counter()
            reply_text = self._conversation.reply(command)
            self._llm_time = time.perf_counter() - t_llm_start
            applied_mods = self._self_mod.apply(
                reply_text,
                self._recent_mods,
                self._mod_history,
                self._virtual_world,
            )
            if applied_mods:
                reply_text += (
                    f"\n\n[System note: Applied changes to {', '.join(applied_mods)}]"
                )
            return AssistantResponse(reply_text)
        except ConversationError as exc:
            return AssistantResponse(str(exc), handled=False)
