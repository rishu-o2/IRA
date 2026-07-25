from __future__ import annotations

from datetime import datetime, timezone

from .manager import MemoryManager
from .models import MemoryRecord


class ConversationMemory:
    def __init__(self, manager: MemoryManager | None = None) -> None:
        self.manager = manager or MemoryManager()

    def remember_turn(self, role: str, text: str) -> MemoryRecord:
        clean_role = role.strip().casefold()
        if clean_role not in {"user", "assistant", "system"}:
            raise ValueError(f"Unsupported conversation role: {role}")
        timestamp = datetime.now(timezone.utc).isoformat()
        return self.manager.remember(
            f"conversation.{timestamp}.{clean_role}",
            text,
            "conversation",
        )

    def search(self, query: str) -> list[MemoryRecord]:
        return [
            record
            for record in self.manager.search(query)
            if record.category == "conversation"
        ]
