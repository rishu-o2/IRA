"""
security/trust.py - Trust Manager for device authentication.
"""

class TrustManager:
    def __init__(self):
        self._trusted_devices: set[str] = set()

    def trust(self, device_id: str) -> None:
        self._trusted_devices.add(device_id)

    def revoke(self, device_id: str) -> None:
        if device_id in self._trusted_devices:
            self._trusted_devices.remove(device_id)

    def is_trusted(self, device_id: str) -> bool:
        return device_id in self._trusted_devices
