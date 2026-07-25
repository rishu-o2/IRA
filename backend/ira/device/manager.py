"""
device/manager.py - Device manager.
"""
from datetime import datetime, timezone
from .models import Device, Capability
from .registry import DeviceRegistry
from ..security.trust import TrustManager

class DeviceManager:
    def __init__(self, registry: DeviceRegistry, trust_manager: TrustManager):
        self._registry = registry
        self._trust_manager = trust_manager

    def register_device(self, device: Device) -> None:
        device.trusted = self._trust_manager.is_trusted(device.device_id)
        self._registry.register(device)

    def update_last_seen(self, device_id: str) -> None:
        device = self._registry.get(device_id)
        if device:
            device.last_seen = datetime.now(timezone.utc)

    def is_capable(self, device_id: str, capability: Capability | str) -> bool:
        device = self._registry.get(device_id)
        if not device:
            return False
        # Convert string to enum if necessary
        if isinstance(capability, str):
            try:
                capability = Capability(capability.upper())
            except ValueError:
                return False
        return capability in device.capabilities
