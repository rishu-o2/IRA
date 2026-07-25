import pytest
from ira.session_manager.manager import SessionManager
from ira.session_manager.models import SessionStatus

def test_session_manager_create():
    manager = SessionManager()
    session = manager.create("dev-1")
    
    assert session.device_id == "dev-1"
    assert session.status == SessionStatus.ACTIVE
    
    # Getting by device should return the session
    retrieved = manager.get_by_device("dev-1")
    assert retrieved == session

def test_session_manager_restore():
    manager = SessionManager()
    session = manager.create("dev-1")
    
    session.status = SessionStatus.IDLE
    
    restored = manager.restore(session.session_id)
    assert restored == session
    assert restored.status == SessionStatus.ACTIVE

def test_session_manager_end():
    manager = SessionManager()
    session = manager.create("dev-1")
    
    manager.end(session.session_id)
    assert session.status == SessionStatus.EXPIRED
    
    assert manager.get_by_device("dev-1") is None

def test_session_manager_create_expires_previous():
    manager = SessionManager()
    session1 = manager.create("dev-1")
    session2 = manager.create("dev-1")
    
    assert session1.status == SessionStatus.EXPIRED
    assert session2.status == SessionStatus.ACTIVE
    assert manager.get_by_device("dev-1") == session2
