from .base import Skill

class SkillRegistry:
    def __init__(self) -> None:
        self._skills: list[Skill] = []
        # Maintain a list to preserve insertion order, and an index for fast lookup/deduplication
        self._skill_names: set[str] = set()

    def register(self, skill: Skill) -> None:
        if skill.name in self._skill_names:
            raise ValueError(f"Skill with name '{skill.name}' is already registered.")
        self._skills.append(skill)
        self._skill_names.add(skill.name)

    def unregister(self, name: str) -> None:
        if name in self._skill_names:
            self._skills = [s for s in self._skills if s.name != name]
            self._skill_names.remove(name)

    def get(self, name: str) -> Skill | None:
        for skill in self._skills:
            if skill.name == name:
                return skill
        return None

    def all(self) -> list[Skill]:
        return list(self._skills)

    def dispatch(self, command: str) -> Skill | None:
        """
        Iterate through registered skills in order.
        Return the first skill whose can_handle(command) returns True.
        """
        from ..pipeline_log import pipeline_log
        for skill in self._skills:
            can = skill.can_handle(command)
            pipeline_log("SkillRegistry", f"Checking {skill.name}: {can}")
            if can:
                return skill
        return None
