import threading
from datetime import datetime, timezone
import uuid

class Session:
    def __init__(self, device_name: str, address: str):
        self._lock = threading.RLock()
        self.session_id: str = uuid.uuid4().hex
        self.device_name: str = device_name
        self.connected_at: datetime = datetime.now(timezone.utc)
        self.last_seen: datetime = self.connected_at
        self.address: str = address
        self.active: bool = True
        
        # Phase 6 additions (Change 8)
        self.last_command: str | None = None
        self.last_response: str | None = None
        self.command_count: int = 0

    def touch(self) -> None:
        with self._lock:
            self.last_seen = datetime.now(timezone.utc)
            self.active = True

    def disconnect(self) -> None:
        with self._lock:
            self.active = False
            
    def record_command(self, command: str) -> None:
        with self._lock:
            self.last_command = command
            self.command_count += 1
            
    def record_response(self, response: str) -> None:
        with self._lock:
            self.last_response = response
