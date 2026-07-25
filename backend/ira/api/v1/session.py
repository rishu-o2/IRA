"""
api/v1/session.py - Session API contracts.
"""
from dataclasses import dataclass

@dataclass
class SessionCreateRequest:
    device_id: str

@dataclass
class SessionResponse:
    success: bool
    session_id: str | None = None
    status: str | None = None
    error: str | None = None
