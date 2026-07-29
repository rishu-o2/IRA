import pytest
import time

from ira.execution.retry import RetryPolicy


def test_retry_policy_safe_unsafe():
    policy = RetryPolicy()
    
    assert policy.is_safe("open_app") is True
    assert policy.is_safe("open_website") is True
    assert policy.is_safe("search_web") is True
    
    assert policy.is_safe("delete") is False
    assert policy.is_safe("shutdown_system") is False
    assert policy.is_safe("lock_screen") is False


def test_retry_policy_delays():
    policy = RetryPolicy(max_attempts=3, backoff_seconds=[0, 1, 2])
    
    assert policy.get_delay(1) == 0
    assert policy.get_delay(2) == 1
    assert policy.get_delay(3) == 2
    assert policy.get_delay(4) == 2  # caps at last element


def test_retry_policy_wait(monkeypatch):
    sleeps = []
    def mock_sleep(seconds):
        sleeps.append(seconds)
        
    monkeypatch.setattr(time, "sleep", mock_sleep)
    
    policy = RetryPolicy(backoff_seconds=[1, 2, 3])
    policy.wait(2)
    
    assert sleeps == [2]
