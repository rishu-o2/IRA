"""
api/v1/events.py - Events API contracts.
"""
from dataclasses import dataclass
from typing import Any

@dataclass
class EventsPollingRequest:
    device_id: str
    last_event_id: str | None = None

@dataclass
class EventsResponse:
    success: bool
    events: list[dict[str, Any]] | None = None
    error: str | None = None
