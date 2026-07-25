from .base import Skill
from ..assistant import AssistantResponse
from ..actions import ActionError
from ..router import default_tool_router
from ..tools import ToolRequest

class FilesystemSkill(Skill):
    """Skill responsible for filesystem operations like opening files and folders."""

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "Handles opening files and folders."

    def can_handle(self, command: str) -> bool:
        lowered = command.lower().strip()
        if lowered.startswith("open folder "):
            return True
        if lowered.startswith("open file "):
            return True
        if lowered in {"open downloads", "open documents", "open desktop", "open pictures", "open photos"}:
            return True
        return False

    def execute(self, command: str) -> AssistantResponse:
        lowered = command.lower().strip()
        
        try:
            if lowered.startswith("open folder "):
                target = command[len("open folder ") :].strip()
                # Use filesystem tool (open_known_folder handles known, open_path handles generic)
                known_folders = {"downloads", "documents", "desktop", "pictures", "photos", "music", "videos"}
                if target.lower() in known_folders:
                    res = default_tool_router.execute(ToolRequest("filesystem", "open_known_folder", {"folder_name": target}))
                else:
                    res = default_tool_router.execute(ToolRequest("filesystem", "open_path", {"target": target}))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)

            if lowered.startswith("open file "):
                target = command[len("open file ") :].strip()
                res = default_tool_router.execute(ToolRequest("filesystem", "open_path", {"target": target}))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)

            if lowered.startswith("open downloads"):
                res = default_tool_router.execute(ToolRequest("filesystem", "open_known_folder", {"folder_name": "downloads"}))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)

            if lowered.startswith("open documents"):
                res = default_tool_router.execute(ToolRequest("filesystem", "open_known_folder", {"folder_name": "documents"}))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)

            if lowered.startswith("open desktop"):
                res = default_tool_router.execute(ToolRequest("filesystem", "open_known_folder", {"folder_name": "desktop"}))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)

            if lowered.startswith("open pictures") or lowered.startswith("open photos"):
                res = default_tool_router.execute(ToolRequest("filesystem", "open_known_folder", {"folder_name": "pictures"}))
                if not res.handled: raise ActionError(res.text)
                return AssistantResponse(res.text)

        except ActionError as exc:
            return AssistantResponse(str(exc), handled=False)

        return AssistantResponse("I could not process the filesystem command.", handled=False)
