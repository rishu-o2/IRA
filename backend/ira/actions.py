from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus


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
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "chrome": "chrome",
        "google chrome": "chrome",
        "browser": "chrome",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "spotify": "spotify",
        "paint": "mspaint",
        "wordpad": "write",
        "explorer": "explorer",
        "file explorer": "explorer",
        "command prompt": "cmd",
        "cmd": "cmd",
    }

    command = app_commands.get(normalized, app_name)

    try:
        subprocess.Popen(command, shell=True)
    except OSError as exc:
        raise ActionError(f"I could not open {app_name}.") from exc

    return f"Opening {app_name}"


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
