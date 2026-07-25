"""
security/models.py - Security foundation models.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import secrets

@dataclass
class DeviceIdentity:
    device_id: str
    public_key_hint: str | None = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    device_secret: str = field(default_factory=lambda: secrets.token_hex(32))

@dataclass
class SessionToken:
    token: str
    device_id: str
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
