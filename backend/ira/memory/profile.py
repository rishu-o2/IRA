from __future__ import annotations

from dataclasses import dataclass, field

from .manager import MemoryManager


PROFILE_FIELDS = {
    "name",
    "preferred_name",
    "language",
    "timezone",
    "preferred_editor",
    "preferred_browser",
    "preferred_terminal",
    "preferred_music_player",
    "university",
}


@dataclass
class UserProfile:
    manager: MemoryManager = field(default_factory=MemoryManager)

    def set(self, field_name: str, value: str) -> None:
        if field_name not in PROFILE_FIELDS and field_name != "current_projects":
            raise ValueError(f"Unsupported profile field: {field_name}")
        self.manager.remember(field_name, value, "profile")

    def get(self, field_name: str) -> str | None:
        if field_name not in PROFILE_FIELDS and field_name != "current_projects":
            raise ValueError(f"Unsupported profile field: {field_name}")
        return self.manager.recall(field_name)

    @property
    def name(self) -> str | None:
        return self.get("name")

    @property
    def preferred_name(self) -> str | None:
        return self.get("preferred_name")

    @property
    def language(self) -> str | None:
        return self.get("language")

    @property
    def timezone(self) -> str | None:
        return self.get("timezone")

    @property
    def preferred_editor(self) -> str | None:
        return self.get("preferred_editor")

    @property
    def preferred_browser(self) -> str | None:
        return self.get("preferred_browser")

    @property
    def preferred_terminal(self) -> str | None:
        return self.get("preferred_terminal")

    @property
    def preferred_music_player(self) -> str | None:
        return self.get("preferred_music_player")

    @property
    def university(self) -> str | None:
        return self.get("university")

    @property
    def current_projects(self) -> list[str]:
        value = self.get("current_projects")
        if value is None:
            return []
        return [project for project in value.splitlines() if project]

    def set_current_projects(self, projects: list[str]) -> None:
        clean_projects = [project.strip() for project in projects if project.strip()]
        self.set("current_projects", "\n".join(clean_projects))
