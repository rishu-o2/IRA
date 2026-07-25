"""
session_manager/manager.py - Session manager.
"""
from datetime import datetime, timezone
from .models import IRASession, SessionStatus

class SessionManager:
    def __init__(self):
        self._sessions: dict[str, IRASession] = {}
        # Mapping from device_id to the currently active session
        self._device_sessions: dict[str, str] = {}

    def create(self, device_id: str) -> IRASession:
        session = IRASession(device_id=device_id)
        self._sessions[session.session_id] = session
        
        # Mark previous session for this device as expired
        if device_id in self._device_sessions:
            prev_session_id = self._device_sessions[device_id]
            if prev_session_id in self._sessions:
                self._sessions[prev_session_id].status = SessionStatus.EXPIRED
                
        self._device_sessions[device_id] = session.session_id
        return session

    def restore(self, session_id: str) -> IRASession | None:
        session = self._sessions.get(session_id)
        if session and session.status != SessionStatus.EXPIRED:
            session.last_active = datetime.now(timezone.utc)
            session.status = SessionStatus.ACTIVE
            self._device_sessions[session.device_id] = session_id
            return session
        return None

    def end(self, session_id: str) -> None:
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.status = SessionStatus.EXPIRED
            if self._device_sessions.get(session.device_id) == session_id:
                del self._device_sessions[session.device_id]

    def get_by_device(self, device_id: str) -> IRASession | None:
        session_id = self._device_sessions.get(device_id)
        if session_id:
            return self.restore(session_id)
        return None
