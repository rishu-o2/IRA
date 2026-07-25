from __future__ import annotations

from .manager import MemoryManager
from .models import MemoryRecord


class ProjectMemory:
    def __init__(self, manager: MemoryManager | None = None) -> None:
        self.manager = manager or MemoryManager()

    def remember_project(self, name: str, summary: str) -> MemoryRecord:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name cannot be empty.")
        return self.manager.remember(f"project.{clean_name}", summary, "project")

    def recall_project(self, name: str) -> str | None:
        clean_name = name.strip()
        if not clean_name:
            return None
        return self.manager.recall(f"project.{clean_name}")

    def search(self, query: str) -> list[MemoryRecord]:
        return [
            record
            for record in self.manager.search(query)
            if record.category == "project"
        ]
