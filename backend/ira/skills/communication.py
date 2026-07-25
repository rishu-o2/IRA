from .base import Skill
from ..assistant import AssistantResponse
from ..actions import ActionError
from ..router import default_tool_router
from ..tools import ToolRequest

class CommunicationSkill(Skill):
    """Skill responsible for communication actions."""

    @property
    def name(self) -> str:
        return "communication"

    @property
    def description(self) -> str:
        return "Handles communication commands like making calls."

    def can_handle(self, command: str) -> bool:
        lowered = command.lower().strip()
        if lowered.startswith(("call ", "make a call to ")):
            return True
        return False

    def execute(self, command: str) -> AssistantResponse:
        lowered = command.lower().strip()
        
        try:
            if lowered.startswith(("call ", "make a call to ")):
                res = default_tool_router.execute(ToolRequest("communication", "call", {"app_name": "skype"}))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)
                
        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        return AssistantResponse("I could not process the communication command.", handled=False)
