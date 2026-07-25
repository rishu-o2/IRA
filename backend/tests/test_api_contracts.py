import pytest
import json
from dataclasses import asdict
from ira.api.v1.device import DeviceRegisterRequest, DeviceHeartbeatRequest
from ira.api.v1.session import SessionCreateRequest

def test_device_register_request_serialization():
    req = DeviceRegisterRequest(
        device_id="dev-1",
        user_id="user-1",
        device_name="Test",
        device_type="DESKTOP",
        platform="Win",
        os_version="11",
        app_version="1.0",
        capabilities=["MICROPHONE", "SPEAKER"]
    )
    data = asdict(req)
    assert data["device_id"] == "dev-1"
    assert data["capabilities"] == ["MICROPHONE", "SPEAKER"]

def test_session_create_request_serialization():
    req = SessionCreateRequest(device_id="dev-1")
    data = asdict(req)
    assert data["device_id"] == "dev-1"

def test_device_heartbeat_request_serialization():
    req = DeviceHeartbeatRequest(device_id="dev-1")
    data = asdict(req)
    assert data["device_id"] == "dev-1"
