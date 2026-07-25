import pytest
from ira.device.models import Device, DeviceType, Capability
from ira.device.registry import DeviceRegistry
from ira.device.manager import DeviceManager
from ira.security.trust import TrustManager

def test_device_registry_register_and_get():
    registry = DeviceRegistry()
    device = Device(
        device_id="dev-1",
        user_id="user-1",
        device_name="Desktop PC",
        device_type=DeviceType.DESKTOP,
        platform="Windows",
        os_version="11",
        app_version="1.0",
    )
    registry.register(device)
    
    assert registry.get("dev-1") == device
    assert registry.get_by_user("user-1") == [device]
    assert registry.list_all() == [device]

def test_device_registry_multiple_devices_for_user():
    registry = DeviceRegistry()
    dev1 = Device(device_id="d1", user_id="u1", device_name="D1", device_type=DeviceType.DESKTOP, platform="P", os_version="1", app_version="1")
    dev2 = Device(device_id="d2", user_id="u1", device_name="D2", device_type=DeviceType.ANDROID, platform="P", os_version="1", app_version="1")
    
    registry.register(dev1)
    registry.register(dev2)
    
    user_devices = registry.get_by_user("u1")
    assert len(user_devices) == 2
    assert dev1 in user_devices
    assert dev2 in user_devices

def test_device_manager_capability_check():
    registry = DeviceRegistry()
    trust_manager = TrustManager()
    manager = DeviceManager(registry, trust_manager)
    
    device = Device(
        device_id="dev-cap",
        user_id="u1",
        device_name="D1",
        device_type=DeviceType.ANDROID,
        platform="P",
        os_version="1",
        app_version="1",
        capabilities={Capability.MICROPHONE, Capability.NOTIFICATIONS}
    )
    manager.register_device(device)
    
    assert manager.is_capable("dev-cap", Capability.MICROPHONE)
    assert manager.is_capable("dev-cap", "NOTIFICATIONS")
    assert not manager.is_capable("dev-cap", Capability.BROWSER)

def test_device_manager_trust_inheritance():
    registry = DeviceRegistry()
    trust_manager = TrustManager()
    manager = DeviceManager(registry, trust_manager)
    
    trust_manager.trust("dev-trust")
    
    device = Device(
        device_id="dev-trust",
        user_id="u1",
        device_name="D1",
        device_type=DeviceType.DESKTOP,
        platform="P",
        os_version="1",
        app_version="1",
    )
    manager.register_device(device)
    
    retrieved = registry.get("dev-trust")
    assert retrieved.trusted is True
