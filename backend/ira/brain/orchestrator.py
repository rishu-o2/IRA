from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .intent import IntentClassifier
from .models import AssistantResponse, BrainRequest, BrainResult
from .planner import BrainPlanner

SingleStepHandler = Callable[[str], AssistantResponse]
MultiStepHandler = Callable[[str, object], AssistantResponse]


class MemoryReader(Protocol):
    def recall(self, key: str) -> str | None:
        ...


class BrainOrchestrator:
    """Coordinates intent and planning while legacy handlers execute behavior."""

    def __init__(
        self,
        planner: BrainPlanner,
        intent_classifier: IntentClassifier | None = None,
        memory: MemoryReader | None = None,
    ) -> None:
        self._planner = planner
        self._intent_classifier = intent_classifier or IntentClassifier()
        self._memory = memory

    def process(
        self,
        request: BrainRequest,
        run_single_step: SingleStepHandler,
        run_multi_step: MultiStepHandler,
    ) -> BrainResult:
        request = self._resolve_memory_references(request)
        intent = self._intent_classifier.classify(request)
        plan = self._planner.plan(intent)

        if plan.is_multi_step:
            response = run_multi_step(request.message, plan.raw_plan)
        else:
            response = run_single_step(request.message)

        return BrainResult(response=response, intent=intent, plan=plan)

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
