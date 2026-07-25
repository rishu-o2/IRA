"""
notifications/queue.py - Notification queue.
"""
import threading
from typing import Iterator
from .models import Notification

class NotificationQueue:
    def __init__(self):
        # We'll use a simple list and sort it for priority if needed, or just append.
        self._queue: list[Notification] = []
        self._lock = threading.Lock()

    def enqueue(self, notification: Notification) -> None:
        with self._lock:
            self._queue.append(notification)
            # A simple sort based on enum value isn't straightforward because LOW/NORMAL/HIGH/CRITICAL are strings.
            # We'll rely on the dispatcher to sort or just process in order for now.

    def dequeue_next(self) -> Notification | None:
        with self._lock:
            if not self._queue:
                return None
            
            # Simple priority mapping
            priority_map = {"CRITICAL": 4, "HIGH": 3, "NORMAL": 2, "LOW": 1}
            self._queue.sort(key=lambda n: priority_map.get(n.priority, 0), reverse=True)
            return self._queue.pop(0)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._queue)
