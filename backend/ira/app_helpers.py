"""Utility helpers for opening applications.

This module provides a clean, self‑contained implementation that mirrors the
logic used in :func:`backend.ira.actions.open_app`. It is deliberately kept
separate so that the virtual snippets you saw in the IDE can be mapped to a
real, lint‑free file.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

# Import the registry helper from the existing actions module; fallback to a
# no‑op lambda if the import fails (e.g., when running on a non‑Windows system).
try:
    from .actions import _find_registered_app
except Exception:  # pragma: no cover – safe fallback
    _find_registered_app = lambda *_: None  # type: ignore[misc]

def _normalize_app_name(value: str) -> str:
    """Normalize an application name for comparison.

    Removes all non‑alphanumeric characters and lower‑cases the string, matching
    the behaviour used when searching the Windows Start‑Menu shortcuts.
    """
    return "".join(ch for ch in value.lower() if ch.isalnum())

def _find_start_menu_shortcut(app_name: str) -> Optional[str]:
    """Search the Windows Start‑Menu for a shortcut matching *app_name*.

    Looks in both the user and the system ``Programs`` directories and returns
    the absolute path to the first matching ``.lnk`` or ``.url`` shortcut, or
    ``None`` if no match is found.
    """
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

def open_app_simple(app_name: str) -> str:
    """Open *app_name* using a series of fall‑backs.

    1. Check the Windows registry for a registered executable.
    2. Look for the executable in ``PATH`` via :func:`shutil.which`.
    3. Search the Start‑Menu shortcuts.
    4. Treat *app_name* as a direct file path.
    """
    target = app_name.strip()
    # 1️⃣ Registry lookup
    registered = _find_registered_app(target)
    if registered:
        os.startfile(registered)  # type: ignore[attr-defined]
        return f"Opening {app_name}"
    # 2️⃣ Executable in PATH
    exe = shutil.which(target)
    if exe:
        os.startfile(exe)  # type: ignore[attr-defined]
        return f"Opening {app_name}"
    # 3️⃣ Start‑Menu shortcut
    shortcut = _find_start_menu_shortcut(target)
    if shortcut:
        os.startfile(shortcut)  # type: ignore[attr-defined]
        return f"Opening {app_name}"
    # 4️⃣ Direct path
    path = Path(target).expanduser()
    if path.exists():
        os.startfile(str(path))  # type: ignore[attr-defined]
        return f"Opening {app_name}"
    raise RuntimeError(
        f"I could not find {app_name}. Try the app name from the Start Menu or use its full path."
    )
