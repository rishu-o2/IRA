from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
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


def lock_screen() -> str:
    if os.name != "nt":
        raise ActionError("Lock screen is only supported on Windows.")

    try:
        locked = bool(ctypes.windll.user32.LockWorkStation())
        if not locked:
            raise OSError("Could not lock the screen.")
    except Exception as exc:
        raise ActionError("I could not lock the screen.") from exc

    return "Locking the screen."


def shutdown_system() -> str:
    if os.name != "nt":
        raise ActionError("Shutdown is only supported on Windows.")

    try:
        subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
    except subprocess.CalledProcessError as exc:
        raise ActionError("I could not shut down the computer.") from exc

    return "Shutting down the computer."


def sleep_system() -> str:
    if os.name != "nt":
        raise ActionError("Sleep is only supported on Windows.")

    try:
        result = ctypes.windll.powrprof.SetSuspendState(False, True, False)
        if result is False:
            raise OSError("Sleep request rejected.")
    except Exception as exc:
        raise ActionError("I could not put the computer to sleep.") from exc

    return "Putting the computer to sleep."


def mute_system() -> str:
    if os.name != "nt":
        raise ActionError("Mute is only supported on Windows.")

    try:
        user32 = ctypes.windll.user32
        VK_VOLUME_MUTE = 0xAD
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as exc:
        raise ActionError("I could not mute the volume.") from exc

    return "Muting the volume."


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
        "skype": "skype.exe",
        "teams": "Teams.exe",
        "visual studio code": "Code.exe",
        "vs code": "Code.exe",
        "vscode": "Code.exe",
    }

    target = app_commands.get(normalized, app_name.strip())
    # Prioritize registered app lookup before executable search
    try:
        registered_app = _find_registered_app(target)
        if registered_app:
            os.startfile(registered_app)  # type: ignore[attr-defined]
            return f"Opening {app_name}"

        # Fallback to executable lookup via shutil.which
        executable = shutil.which(target)
        if executable:
            os.startfile(executable)  # type: ignore[attr-defined]
            return f"Opening {app_name}"

        # Check for start menu shortcut
        shortcut = _find_start_menu_shortcut(normalized)
        if shortcut:
            os.startfile(shortcut)  # type: ignore[attr-defined]
            return f"Opening {app_name}"

        # Check for direct path existence
        target_path = Path(target).expanduser()
        if target_path.exists():
            os.startfile(target_path)  # type: ignore[attr-defined]
            return f"Opening {app_name}"

        raise ActionError(f"I could not find {app_name}. Try the app name from the Start Menu or use its full path.")
    except (OSError, ValueError) as exc:
        raise ActionError(f"I could not open {app_name}. Check that it is installed or try its full path.") from exc


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


def volume_up() -> str:
    if os.name != "nt":
        raise ActionError("Volume up is only supported on Windows.")
    try:
        user32 = ctypes.windll.user32
        VK_VOLUME_UP = 0xAF
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        # Press and release volume up
        user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as exc:
        raise ActionError("I could not increase the volume.") from exc
    return "Increasing volume."


def volume_down() -> str:
    if os.name != "nt":
        raise ActionError("Volume down is only supported on Windows.")
    try:
        user32 = ctypes.windll.user32
        VK_VOLUME_DOWN = 0xAE
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        # Press and release volume down
        user32.keybd_event(VK_VOLUME_DOWN, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(VK_VOLUME_DOWN, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as exc:
        raise ActionError("I could not decrease the volume.") from exc
    return "Decreasing volume."


def set_brightness(level: int) -> str:
    if os.name != "nt":
        raise ActionError("Brightness control is only supported on Windows.")
    if not (0 <= level <= 100):
        raise ActionError("Brightness level must be between 0 and 100.")
    try:
        # Use CIM/WMI WmiMonitorBrightnessMethods via powershell to set brightness
        # Wrap cmdlet parameters securely
        cmd = f'Powershell -Command "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(0, {level})"'
        subprocess.run(cmd, shell=True, check=True)
    except Exception as exc:
        raise ActionError("I could not set screen brightness. Your monitor might not support this control.") from exc
    return f"Screen brightness set to {level}%."


def get_battery_status() -> str:
    if os.name != "nt":
        raise ActionError("Battery status is only supported on Windows.")

    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_byte),
            ("BatteryFlag", ctypes.c_byte),
            ("BatteryLifePercent", ctypes.c_byte),
            ("Reserved1", ctypes.c_byte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = SYSTEM_POWER_STATUS()
    if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        percent = status.BatteryLifePercent
        if percent == 255:
            return "Battery status is unknown."
        charging = "charging" if status.ACLineStatus == 1 else "not charging"
        return f"Battery is at {percent}%, and is currently {charging}."
    raise ActionError("Could not retrieve system power or battery status.")


def get_system_stats() -> str:
    import psutil
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    battery_info = ""
    try:
        battery_info = " " + get_battery_status()
    except Exception:
        pass
    return f"CPU usage is at {cpu}%, and RAM memory usage is at {ram}%.{battery_info}"


# ---------------------------------------------------------------------------
# Browser and Media Keyboard Actions (Migrated from Skills)
# ---------------------------------------------------------------------------

_KEYEVENTF_EXTENDEDKEY: int = 0x0001
_KEYEVENTF_KEYUP:       int = 0x0002

_VK = {
    "F5":       0x74,
    "BROWSER_BACK":    0xA6,
    "BROWSER_FORWARD": 0xA7,
    "t":        0x54,
    "w":        0x57,
    "T":        0x54,
    "MEDIA_PLAY_PAUSE": 0xB3,
    "MEDIA_NEXT_TRACK": 0xB0,
    "MEDIA_PREV_TRACK": 0xB1,
    "MEDIA_STOP":       0xB2,
}

def _key_down(vk: int, extended: bool = False) -> None:
    flags = _KEYEVENTF_EXTENDEDKEY if extended else 0
    ctypes.windll.user32.keybd_event(vk, 0, flags, 0)

def _key_up(vk: int, extended: bool = False) -> None:
    flags = (_KEYEVENTF_EXTENDEDKEY if extended else 0) | _KEYEVENTF_KEYUP
    ctypes.windll.user32.keybd_event(vk, 0, flags, 0)

def _send_key(vk: int, ctrl: bool = False, shift: bool = False, extended: bool = False) -> None:
    VK_CONTROL = 0x11
    VK_SHIFT   = 0x10
    if ctrl:
        _key_down(VK_CONTROL)
    if shift:
        _key_down(VK_SHIFT)
    _key_down(vk, extended)
    _key_up(vk, extended)
    if shift:
        _key_up(VK_SHIFT)
    if ctrl:
        _key_up(VK_CONTROL)

def refresh_browser() -> str:
    if os.name != "nt":
        raise ActionError("Browser refresh is only supported on Windows.")
    try:
        _send_key(_VK["F5"])
    except Exception as exc:
        raise ActionError("I could not refresh the browser.") from exc
    return "Refreshing the browser."

def go_back() -> str:
    if os.name != "nt":
        raise ActionError("Browser back is only supported on Windows.")
    try:
        _send_key(_VK["BROWSER_BACK"], extended=True)
    except Exception as exc:
        raise ActionError("I could not go back in the browser.") from exc
    return "Going back."

def go_forward() -> str:
    if os.name != "nt":
        raise ActionError("Browser forward is only supported on Windows.")
    try:
        _send_key(_VK["BROWSER_FORWARD"], extended=True)
    except Exception as exc:
        raise ActionError("I could not go forward in the browser.") from exc
    return "Going forward."

def open_new_tab() -> str:
    if os.name != "nt":
        raise ActionError("Open new tab is only supported on Windows.")
    try:
        _send_key(_VK["t"], ctrl=True)
    except Exception as exc:
        raise ActionError("I could not open a new tab.") from exc
    return "Opening a new tab."

def close_tab() -> str:
    if os.name != "nt":
        raise ActionError("Close tab is only supported on Windows.")
    try:
        _send_key(_VK["w"], ctrl=True)
    except Exception as exc:
        raise ActionError("I could not close the tab.") from exc
    return "Closing the current tab."

def reopen_tab() -> str:
    if os.name != "nt":
        raise ActionError("Reopen tab is only supported on Windows.")
    try:
        _send_key(_VK["T"], ctrl=True, shift=True)
    except Exception as exc:
        raise ActionError("I could not reopen the last closed tab.") from exc
    return "Reopening the last closed tab."

def play_pause_media() -> str:
    if os.name != "nt":
        raise ActionError("Media play/pause is only supported on Windows.")
    try:
        _send_key(_VK["MEDIA_PLAY_PAUSE"], extended=True)
    except Exception as exc:
        raise ActionError("I could not toggle media playback.") from exc
    return "Toggling media playback."

def next_track() -> str:
    if os.name != "nt":
        raise ActionError("Next track is only supported on Windows.")
    try:
        _send_key(_VK["MEDIA_NEXT_TRACK"], extended=True)
    except Exception as exc:
        raise ActionError("I could not skip to the next track.") from exc
    return "Skipping to the next track."

def previous_track() -> str:
    if os.name != "nt":
        raise ActionError("Previous track is only supported on Windows.")
    try:
        _send_key(_VK["MEDIA_PREV_TRACK"], extended=True)
    except Exception as exc:
        raise ActionError("I could not go to the previous track.") from exc
    return "Going to the previous track."

def stop_media() -> str:
    if os.name != "nt":
        raise ActionError("Media stop is only supported on Windows.")
    try:
        _send_key(_VK["MEDIA_STOP"], extended=True)
    except Exception as exc:
        raise ActionError("I could not stop media playback.") from exc
    return "Stopping media playback."
