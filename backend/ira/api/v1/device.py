"""
api/v1/device.py - Device API contracts.
"""
from dataclasses import dataclass
from typing import Any

@dataclass
class DeviceRegisterRequest:
    device_id: str
    user_id: str
    device_name: str
    device_type: str
    platform: str
    os_version: str
    app_version: str
    capabilities: list[str]

@dataclass
class DeviceRegisterResponse:
    success: bool
    device_secret: str | None = None
    error: str | None = None

@dataclass
class DeviceHeartbeatRequest:
    device_id: str

@dataclass
class DeviceHeartbeatResponse:
    success: bool
    error: str | None = None
