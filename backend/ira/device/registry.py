"""
device/registry.py - In-memory registry of devices.
"""
from collections import defaultdict
from .models import Device

class DeviceRegistry:
    def __init__(self):
        self._devices: dict[str, Device] = {}
        self._users_devices: dict[str, list[Device]] = defaultdict(list)

    def register(self, device: Device) -> None:
        self._devices[device.device_id] = device
        # Ensure we don't have duplicates in the user list
        self._users_devices[device.user_id] = [
            d for d in self._users_devices[device.user_id] if d.device_id != device.device_id
        ]
        self._users_devices[device.user_id].append(device)

    def unregister(self, device_id: str) -> None:
        if device_id in self._devices:
            device = self._devices.pop(device_id)
            if device.user_id in self._users_devices:
                self._users_devices[device.user_id] = [
                    d for d in self._users_devices[device.user_id] if d.device_id != device_id
                ]

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def get_by_user(self, user_id: str) -> list[Device]:
        return self._users_devices.get(user_id, [])

    def list_all(self) -> list[Device]:
        return list(self._devices.values())
