"""
sync/events.py - SyncEventFactory.
"""
from typing import Any
from .models import SyncRecord, SyncEventType

class SyncEventFactory:
    @staticmethod
    def create_memory_sync(device_id: str, payload: dict[str, Any], version: int = 1) -> SyncRecord:
        return SyncRecord(event_type=SyncEventType.MEMORY, device_id=device_id, payload=payload, version=version)

    @staticmethod
    def create_goal_sync(device_id: str, payload: dict[str, Any], version: int = 1) -> SyncRecord:
        return SyncRecord(event_type=SyncEventType.GOAL, device_id=device_id, payload=payload, version=version)

    @staticmethod
    def create_preference_sync(device_id: str, payload: dict[str, Any], version: int = 1) -> SyncRecord:
        return SyncRecord(event_type=SyncEventType.PREFERENCE, device_id=device_id, payload=payload, version=version)

    @staticmethod
    def create_knowledge_sync(device_id: str, payload: dict[str, Any], version: int = 1) -> SyncRecord:
        return SyncRecord(event_type=SyncEventType.KNOWLEDGE, device_id=device_id, payload=payload, version=version)

    @staticmethod
    def create_task_sync(device_id: str, payload: dict[str, Any], version: int = 1) -> SyncRecord:
        return SyncRecord(event_type=SyncEventType.TASK, device_id=device_id, payload=payload, version=version)
