"""
sync/queue.py - SyncQueue for thread-safe synchronization records.
"""
from collections import deque
import threading
from .models import SyncRecord

class SyncQueue:
    def __init__(self):
        self._queue: deque[SyncRecord] = deque()
        self._lock = threading.Lock()

    def enqueue(self, record: SyncRecord) -> None:
        with self._lock:
            self._queue.append(record)

    def dequeue(self) -> SyncRecord | None:
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None

    def peek(self) -> SyncRecord | None:
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None

    def size(self) -> int:
        with self._lock:
            return len(self._queue)
