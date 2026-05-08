from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path


class ActionError(RuntimeError):
    """Raised when IRA cannot complete a requested action."""


def open_path(target: str) -> str:
    path = Path(target).expanduser()

    if not path.exists():
        raise ActionError(f"I could not find: {path}")

    os.startfile(path)  # type: ignore[attr-defined]
    return f"Opened {path}"


def open_app(app_name: str) -> str:
    normalized = app_name.strip().lower()
    app_commands = {
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "chrome": "chrome",
        "edge": "msedge",
        "spotify": "spotify",
    }

    command = app_commands.get(normalized, app_name)

    try:
        subprocess.Popen([command], shell=True)
    except OSError as exc:
        raise ActionError(f"I could not open {app_name}.") from exc

    return f"Opening {app_name}"


def open_website(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    webbrowser.open(url)
    return f"Opening {url}"


def play_youtube_search(query: str) -> str:
    encoded = query.strip().replace(" ", "+")
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    return f"Searching YouTube for {query}"

