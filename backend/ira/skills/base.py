from abc import ABC, abstractmethod
from typing import Any

class Skill(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name of the skill."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a brief description of what the skill does."""
        pass

    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """Return True if this skill can handle the given command."""
        pass

    @abstractmethod
    def execute(self, command: str) -> Any:
        """
        Execute the command.
        Must return the same response type (AssistantResponse) expected by IRA's handlers,
        but without strictly depending on the assistant.py module imports here.
        """
        pass
