from __future__ import annotations

import os
import shutil
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

try:
    import winreg
except ImportError:  # pragma: no cover - Windows-only module.
    winreg = None


class ActionError(RuntimeError):
    """Raised when IRA cannot complete a requested action."""


def open_path(target: str) -> str:
    path = Path(target).expanduser()

    if not path.exists():
        raise ActionError(f"I could not find: {path}")

    os.startfile(path)  # type: ignore[attr-defined]
    return f"Opened {path}"


def open_known_folder(folder_name: str) -> str:
    normalized = folder_name.strip().lower()
    folder_map = {
        "desktop": Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "download": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "document": Path.home() / "Documents",
        "pictures": Path.home() / "Pictures",
        "photos": Path.home() / "Pictures",
        "music": Path.home() / "Music",
        "videos": Path.home() / "Videos",
    }

    path = folder_map.get(normalized)
    if path is None:
        raise ActionError(f"I do not know the folder {folder_name}.")

    return open_path(str(path))


def open_app(app_name: str) -> str:
    normalized = app_name.strip().lower()
    app_commands = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "browser": "chrome.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "spotify": "spotify.exe",
        "paint": "mspaint.exe",
        "wordpad": "write.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "command prompt": "cmd.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "visual studio code": "Code.exe",
        "vs code": "Code.exe",
        "vscode": "Code.exe",
    }

    target = app_commands.get(normalized, app_name.strip())
    shortcut = _find_start_menu_shortcut(normalized)

    try:
        if shortcut:
            os.startfile(shortcut)  # type: ignore[attr-defined]
            return f"Opening {app_name}"

        registered_app = _find_registered_app(target)
        if registered_app:
            os.startfile(registered_app)  # type: ignore[attr-defined]
            return f"Opening {app_name}"

        target_path = Path(target).expanduser()
        if target_path.exists():
            os.startfile(target_path)  # type: ignore[attr-defined]
            return f"Opening {app_name}"

        executable = shutil.which(target)
        if executable:
            os.startfile(executable)  # type: ignore[attr-defined]
            return f"Opening {app_name}"

        raise ActionError(f"I could not find {app_name}. Try the app name from the Start Menu or use its full path.")
    except (OSError, ValueError) as exc:
        raise ActionError(f"I could not open {app_name}. Check that it is installed or try its full path.") from exc

    return f"Opening {app_name}"


def _find_start_menu_shortcut(app_name: str) -> str | None:
    start_menu_dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]
    normalized_app = _normalize_app_name(app_name)

    for start_menu_dir in start_menu_dirs:
        if not start_menu_dir.exists():
            continue

        shortcuts = list(start_menu_dir.rglob("*.lnk")) + list(start_menu_dir.rglob("*.url"))

        for shortcut in shortcuts:
            if _normalize_app_name(shortcut.stem) == normalized_app:
                return str(shortcut)

        for shortcut in shortcuts:
            shortcut_name = _normalize_app_name(shortcut.stem)
            if normalized_app in shortcut_name or shortcut_name in normalized_app:
                return str(shortcut)

    return None


def _normalize_app_name(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _find_registered_app(executable_name: str) -> str | None:
    if winreg is None or not executable_name.lower().endswith(".exe"):
        return None

    registry_paths = [
        (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"),
    ]

    for hive, registry_path in registry_paths:
        try:
            with winreg.OpenKey(hive, registry_path) as key:
                value, _ = winreg.QueryValueEx(key, "")
        except OSError:
            continue

        app_path = str(value).strip('"')
        if app_path and Path(app_path).exists():
            return app_path

    return None


def open_website(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    webbrowser.open(url)
    return f"Opening {url}"


def search_web(query: str) -> str:
    clean_query = query.strip()
    if not clean_query:
        raise ActionError("Tell me what you want to search for.")

    encoded = quote_plus(clean_query)
    webbrowser.open(f"https://www.google.com/search?q={encoded}")
    return f"Searching Google for {clean_query}"


def play_youtube_search(query: str) -> str:
    clean_query = query.strip()
    if not clean_query:
        raise ActionError("Tell me what you want me to play.")

    encoded = quote_plus(clean_query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    return f"Searching YouTube for {clean_query}"
