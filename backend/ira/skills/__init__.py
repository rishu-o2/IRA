"""
skills/__init__.py – Skill framework exports and registry factory.

The build_registry() function creates a fully-populated SkillRegistry
with all capability skills registered in the correct dispatch order.
"""
from .base import Skill
from .registry import SkillRegistry

__all__ = ["Skill", "SkillRegistry", "build_registry"]


def build_registry(
    *,
    virtual_world=None,
    modification_history=None,
    context_retriever=None,
) -> SkillRegistry:
    """Create and populate a SkillRegistry with all skills.

    Parameters are injected so that no circular imports arise from
    importing assistant.py or session.py at module scope.

    Dispatch order matters: preference skill is checked first so that
    "open my editor" is resolved via memory before the generic AppSkill
    matches "open <something>".
    """
    from .system import SystemSkill
    from .app import AppSkill
    from .browser import BrowserSkill
    from .media import MediaSkill
    from .filesystem import FilesystemSkill
    from .communication import CommunicationSkill
    from .virtual_world_skill import VirtualWorldSkill
    from .modification_skill import ModificationSkill
    from .preference import PreferenceSkill

    registry = SkillRegistry()

    # Preference skill MUST be registered first so it has priority over
    # the generic AppSkill for commands like "open my editor".
    if context_retriever is not None:
        registry.register(PreferenceSkill(registry, context_retriever))

    # Virtual world & modification introspection
    if virtual_world is not None:
        registry.register(VirtualWorldSkill(virtual_world))
    if modification_history is not None:
        registry.register(ModificationSkill(modification_history))

    # Capability skills
    registry.register(SystemSkill())
    registry.register(BrowserSkill())
    registry.register(AppSkill())
    registry.register(MediaSkill())
    registry.register(FilesystemSkill())
    registry.register(CommunicationSkill())

    return registry
