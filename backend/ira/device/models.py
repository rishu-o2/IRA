"""
device/models.py - Device data models.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

class DeviceType(str, Enum):
    DESKTOP = "DESKTOP"
    ANDROID = "ANDROID"
    WEB = "WEB"
    CLI = "CLI"
    UNKNOWN = "UNKNOWN"

class Capability(str, Enum):
    MICROPHONE = "MICROPHONE"
    SPEAKER = "SPEAKER"
    NOTIFICATIONS = "NOTIFICATIONS"
    CAMERA = "CAMERA"
    FILESYSTEM = "FILESYSTEM"
    SHELL = "SHELL"
    BROWSER = "BROWSER"
    CLIPBOARD = "CLIPBOARD"

@dataclass
class Device:
    device_id: str
    user_id: str
    device_name: str
    device_type: DeviceType
    platform: str
    os_version: str
    app_version: str
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trusted: bool = False
    capabilities: set[Capability] = field(default_factory=set)
