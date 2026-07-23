import threading
from .session import Session

class SessionManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._sessions: dict[str, Session] = {}

    def add(self, session: Session) -> None:
        with self._lock:
            self._sessions[session.session_id] = session

    def remove(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def all(self) -> list[Session]:
        with self._lock:
            return list(self._sessions.values())

    def broadcast(self, message: dict) -> None:
        # In this phase, broadcast is a no-op / mock, 
        # as there is no streaming or persistent active connection protocol yet.
        pass
