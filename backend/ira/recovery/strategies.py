from __future__ import annotations

from typing import Protocol, Any


class RecoveryStrategy(Protocol):
    def can_recover(self, tool_name: str, parameters: dict[str, Any]) -> bool:
        ...

    def generate_fallbacks(self, tool_name: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        """Returns a list of fallback parameter configurations to try in order."""
        ...


class AppRecovery:
    def can_recover(self, tool_name: str, parameters: dict[str, Any]) -> bool:
        return tool_name == "open_app" and "app_name" in parameters

    def generate_fallbacks(self, tool_name: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        app_name = parameters["app_name"].lower()
        fallbacks = []

        if "chrome" in app_name:
            fallbacks = [
                {"app_name": "google-chrome"},
                {"app_name": "chrome.exe"},
            ]
        elif "code" in app_name or "visual studio" in app_name:
            fallbacks = [
                {"app_name": "Code.exe"},
            ]
        elif "word" in app_name:
            fallbacks = [
                {"app_name": "winword.exe"},
            ]
        elif "excel" in app_name:
            fallbacks = [
                {"app_name": "excel.exe"},
            ]
        elif "powerpoint" in app_name:
            fallbacks = [
                {"app_name": "powerpnt.exe"},
            ]

        # Always add the .exe variant as a generic fallback if not present
        if not app_name.endswith(".exe"):
            generic_exe = {"app_name": f"{app_name}.exe"}
            if generic_exe not in fallbacks:
                fallbacks.append(generic_exe)

        return fallbacks


class WebsiteRecovery:
    def can_recover(self, tool_name: str, parameters: dict[str, Any]) -> bool:
        return tool_name == "open_website" and "url" in parameters

    def generate_fallbacks(self, tool_name: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        url = parameters["url"]
        fallbacks = []
        
        # If it doesn't look like a URL, try prefixing it
        if not url.startswith("http://") and not url.startswith("https://"):
            fallbacks.append({"url": f"https://{url}"})
            
            # If it also doesn't have a tld, add .com
            if "." not in url:
                fallbacks.append({"url": f"https://{url}.com"})
                
        return fallbacks


class FilesystemRecovery:
    def can_recover(self, tool_name: str, parameters: dict[str, Any]) -> bool:
        return tool_name == "open_known_folder" and "folder_name" in parameters

    def generate_fallbacks(self, tool_name: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        folder = parameters["folder_name"].lower()
        fallbacks = []
        
        # Normalize folder aliases
        if folder in ("download", "downloads"):
            fallbacks.append({"folder_name": "downloads"})
        elif folder in ("document", "documents"):
            fallbacks.append({"folder_name": "documents"})
        elif folder in ("picture", "pictures", "photos"):
            fallbacks.append({"folder_name": "pictures"})
            
        return fallbacks
