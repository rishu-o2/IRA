"""
api/v1/sync.py - Sync API contracts.
"""
from dataclasses import dataclass
from typing import Any

@dataclass
class SyncPullRequest:
    device_id: str

@dataclass
class SyncPushRequest:
    device_id: str
    records: list[dict[str, Any]]

@dataclass
class SyncResponse:
    success: bool
    records: list[dict[str, Any]] | None = None
    error: str | None = None
