from .base import Tool, ToolRequest, ToolResult
from .browser import BrowserTool, browser_tool
from .communication import CommunicationTool, communication_tool
from .desktop import DesktopTools, desktop_tools
from .filesystem import FilesystemTool, filesystem_tool
from .media import MediaTool, media_tool
from .registry import ToolRegistry
from .system import SystemTool, system_tool

tool_registry = ToolRegistry()
tool_registry.register(desktop_tools)
tool_registry.register(browser_tool)
tool_registry.register(media_tool)
tool_registry.register(system_tool)
tool_registry.register(filesystem_tool)
tool_registry.register(communication_tool)

__all__ = [
    "BrowserTool",
    "CommunicationTool",
    "DesktopTools",
    "FilesystemTool",
    "MediaTool",
    "SystemTool",
    "Tool",
    "ToolRegistry",
    "ToolRequest",
    "ToolResult",
    "browser_tool",
    "communication_tool",
    "desktop_tools",
    "filesystem_tool",
    "media_tool",
    "system_tool",
    "tool_registry",
]
