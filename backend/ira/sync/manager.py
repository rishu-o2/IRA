"""
sync/manager.py - SyncManager to manage synchronization operations.
"""
from typing import Iterator
from .models import SyncRecord
from .queue import SyncQueue

class SyncManager:
    def __init__(self, queue: SyncQueue):
        self._queue = queue
        self._synced_records: set[str] = set()

    def sync_all(self, target_device_id: str) -> None:
        """Process all pending records meant for target_device_id."""
        # For now, just mark all dequeued records as synced if they match
        pending = list(self.get_pending())
        for record in pending:
            if record.device_id == target_device_id or record.device_id == "*":
                self.mark_synced(record.record_id)

    def get_pending(self) -> Iterator[SyncRecord]:
        """Iterate over records that haven't been synced."""
        while (record := self._queue.dequeue()) is not None:
            if not record.synced:
                yield record

    def mark_synced(self, record_id: str) -> None:
        """Mark a record as successfully synced."""
        self._synced_records.add(record_id)
        # Note: In a real implementation we would find it and mark it synced if we persisted the queue
