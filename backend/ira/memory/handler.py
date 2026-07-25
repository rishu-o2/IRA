"""
memory/handler.py – Memory read/write/list/format handler for IRA.

Extracted from IRAAssistant:
  * _handle_memory_command
  * _handle_memory_statement
  * _save_memory
  * _mirror_to_persistent_memory
  * _memory_reply
  * _memory_acknowledgement
  * _answer_from_memory
  * _list_memories
  * _looks_like_memory_question
  * _format_memory_entry

Also owns the post-interaction learning call (_learn_from_long_term_memory).

Public surface area:
  handle_command(command, lowered)  -> AssistantResponse | None
  handle_statement(command)         -> AssistantResponse | None
  answer_from_context(command, lowered, context) -> AssistantResponse | None
"""
from __future__ import annotations

from ..brain.models import AssistantResponse
from ..memory.long_term import MemoryStore, MemoryType
from ..memory.manager import LegacyMemoryManager, MemoryManager
from ..memory.consolidation import MemoryConsolidator
from ..memory.retrieval import Context
from ..suggestions import ProactiveSuggestionEngine


class MemoryHandler:
    """Handles all memory operations for the assistant request lifecycle."""

    def __init__(
        self,
        memory_store: MemoryStore,
        memory_manager: LegacyMemoryManager,
        persistent_memory_manager: MemoryManager,
        memory_consolidator: MemoryConsolidator,
        suggestion_engine: ProactiveSuggestionEngine,
    ) -> None:
        self._store = memory_store
        self._manager = memory_manager
        self._persistent = persistent_memory_manager
        self._consolidator = memory_consolidator
        self._suggestion_engine = suggestion_engine

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def handle_command(
        self, command: str, lowered: str
    ) -> AssistantResponse | None:
        """Handle explicit memory commands (remember, forget, show memories).

        Returns ``None`` when the command is not a memory command.
        """
        if lowered.startswith("remember "):
            memory_text = command[len("remember "):].strip()
            save_result = self._save_memory(memory_text)
            if save_result["remembered"]:
                return AssistantResponse(self._memory_reply(save_result))
            if save_result["duplicate"]:
                return AssistantResponse("Memory updated.")
            return AssistantResponse(
                "I couldn't turn that into a personal memory.", handled=False
            )

        if lowered.startswith("forget "):
            memory_text = command[len("forget "):].strip()
            forgotten = self._manager.forget(memory_text)
            if forgotten:
                for memory in forgotten:
                    key = str(memory.metadata.get("key", "")).strip()
                    if key:
                        self._persistent.forget(key)
                self._consolidator.consolidate(self._store)
                return AssistantResponse("I've forgotten it.")
            return AssistantResponse(
                "I don't have anything stored about that yet."
            )

        if lowered in {
            "what do you remember",
            "what do you remember?",
            "what do you remember about me",
            "what do you remember about me?",
            "what do you know about me",
            "what do you know about me?",
            "show my memories",
            "show me my memories",
        }:
            return self._list_memories(
                self._store.all(), "Here's what I know about you"
            )

        if lowered in {
            "show my preferences", "show my preferences?",
            "show me my preferences", "show me my preferences?",
        }:
            return self._list_memories(
                [e for e in self._store.all() if e.type == MemoryType.PREFERENCE],
                "Here are your preferences",
                empty_text="I don't have any preferences stored yet.",
            )

        if lowered in {
            "show my goals", "show my goals?",
            "show me my goals", "show me my goals?",
        }:
            return self._list_memories(
                [e for e in self._store.all() if e.type == MemoryType.GOAL],
                "Here are your goals",
                empty_text="I don't have any goals stored yet.",
            )

        return None

    def handle_statement(self, command: str) -> AssistantResponse | None:
        """Detect and persist implicit memory statements.

        Returns ``None`` when the command is not a memory statement.
        """
        if not self._manager.should_remember(command):
            return None

        save_result = self._save_memory(command)
        if save_result["remembered"]:
            return AssistantResponse(self._memory_reply(save_result))
        if save_result["duplicate"]:
            return AssistantResponse("Memory updated.")
        return None

    def answer_from_context(
        self, command: str, lowered: str, context: Context
    ) -> AssistantResponse | None:
        """Answer a memory question from already-retrieved context."""
        if not context.memories:
            return None
        if not self._looks_like_memory_question(lowered):
            return None
        memories = context.memories[:3]
        text = "; ".join(self._format_memory_entry(e) for e in memories)
        return AssistantResponse(f"I remember that {text}.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _save_memory(self, text: str) -> dict:
        existing_by_key = {
            entry.metadata.get("key"): entry.content
            for entry in self._store.all()
            if entry.metadata.get("key")
        }
        existing_contents = {entry.content.casefold() for entry in self._store.all()}
        candidates = self._manager.extract(text)
        remembered = self._manager.remember(text)

        if remembered:
            self._mirror_to_persistent(remembered)
            self._consolidator.consolidate(self._store)

        new_memories = [
            entry
            for entry in remembered
            if (
                entry.metadata.get("key")
                and entry.metadata.get("key") not in existing_by_key
            )
            or entry.content.casefold() not in existing_contents
        ]
        updated_preference = any(
            entry.type == MemoryType.PREFERENCE
            and entry.metadata.get("key") in existing_by_key
            and existing_by_key[entry.metadata.get("key")] != entry.content
            for entry in remembered
        )
        duplicate = bool(candidates) and not remembered
        return {
            "remembered": remembered,
            "new_memories": new_memories,
            "updated_preference": updated_preference,
            "duplicate": duplicate,
        }

    def _mirror_to_persistent(self, memories: list) -> None:
        for memory in memories:
            key = str(memory.metadata.get("key", "")).strip()
            value = str(memory.metadata.get("value", "")).strip()
            category = str(memory.metadata.get("category", "")).strip()
            if not key or not value or not category:
                continue
            try:
                self._persistent.remember(key, value, category)
            except Exception as exc:
                print(f"[MEMORY] SQLite mirror failed for {key}: {exc}")

    def _memory_reply(self, save_result: dict) -> str:
        remembered = save_result["remembered"]
        new_memories = save_result["new_memories"]
        if not isinstance(remembered, list) or not remembered:
            return "Memory updated."
        if not isinstance(new_memories, list):
            new_memories = []

        if save_result["updated_preference"]:
            base = "I've updated that preference."
        else:
            base = self._memory_acknowledgement(remembered[0])

        suggestion = self._suggestion_engine.suggest(new_memories)
        if suggestion is None:
            return base
        return f"{base}\n\n{suggestion}"

    def _memory_acknowledgement(self, memory) -> str:
        category = str(memory.metadata.get("category", "")).casefold()
        key = str(memory.metadata.get("key", "")).casefold()
        value = str(memory.metadata.get("value", ""))

        if category == "exam":
            return "I've remembered your exam."
        if memory.type == MemoryType.NOTE:
            return "Understood."
        if memory.type == MemoryType.PREFERENCE:
            return "Got it."
        if memory.type == MemoryType.GOAL and key == "preparation":
            return f"I'll remember that you're preparing for {value}."
        if memory.type == MemoryType.GOAL and key == "project":
            return "I'll remember that."
        return "I'll remember that."

    def _list_memories(
        self,
        memories: list,
        prefix: str,
        empty_text: str = "I don't have any personal memories stored yet.",
    ) -> AssistantResponse:
        if not memories:
            return AssistantResponse(empty_text)
        summary = "; ".join(self._format_memory_entry(e) for e in memories)
        return AssistantResponse(f"{prefix}: {summary}.")

    def _looks_like_memory_question(self, lowered: str) -> bool:
        if not lowered.startswith(
            ("what ", "which ", "who ", "when ", "where ", "why ", "how ")
        ):
            return False
        if "about me" in lowered or "remember" in lowered or "know" in lowered:
            return True
        return any(
            term in lowered
            for term in {
                "favorite", "prefer", "use", "editor",
                "goal", "goal is", "project", "live", "work", "note",
            }
        )

    def _format_memory_entry(self, entry) -> str:
        content = entry.content.strip()
        lowered = content.casefold()
        if " = " in content:
            subject, value = content.split(" = ", 1)
            subject_lower = subject.casefold()
            if subject_lower == "goal":
                return f"your goal is {value}"
            if subject_lower == "personal fact":
                return f"you are {value}"
            if subject_lower.startswith(("favorite ", "preferred ")):
                return f"your {subject_lower} is {value}"
            return f"your {subject_lower} is {value}"
        if lowered.startswith("prefers "):
            return f"you prefer {content[len('Prefers '):]}"
        if lowered.startswith("uses "):
            return f"you use {content[len('Uses '):]}"
        if lowered.startswith("lives in "):
            return f"you live in {content[len('Lives in '):]}"
        if lowered.startswith("works as "):
            return f"you work as {content[len('Works as '):]}"
        if lowered.startswith("works at "):
            return f"you work at {content[len('Works at '):]}"
        return content
