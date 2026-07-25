import pytest
from ira.notifications.models import Notification, NotificationPriority
from ira.notifications.queue import NotificationQueue
from ira.notifications.dispatcher import NotificationDispatcher
from ira.device.models import DeviceType

def test_notification_queue_priority_ordering():
    queue = NotificationQueue()
    n1 = Notification(title="Low", body="low", priority=NotificationPriority.LOW)
    n2 = Notification(title="Critical", body="critical", priority=NotificationPriority.CRITICAL)
    n3 = Notification(title="High", body="high", priority=NotificationPriority.HIGH)
    
    queue.enqueue(n1)
    queue.enqueue(n2)
    queue.enqueue(n3)
    
    # CRITICAL should be first
    assert queue.dequeue_next() == n2
    # HIGH should be second
    assert queue.dequeue_next() == n3
    # LOW should be last
    assert queue.dequeue_next() == n1
    assert queue.dequeue_next() is None

class DummyHandler:
    def __init__(self):
        self.handled_notifications = []

    def handle(self, notification: Notification) -> bool:
        self.handled_notifications.append(notification)
        return True

def test_notification_dispatcher():
    dispatcher = NotificationDispatcher()
    handler = DummyHandler()
    
    dispatcher.register_handler(DeviceType.DESKTOP, handler)
    
    n = Notification(title="Test", body="body", priority=NotificationPriority.NORMAL)
    dispatcher.dispatch(n, DeviceType.DESKTOP)
    
    assert len(handler.handled_notifications) == 1
    assert n.delivered is True
    
    # Dispatching to unregistered device type shouldn't crash
    n2 = Notification(title="Test2", body="body", priority=NotificationPriority.NORMAL)
    dispatcher.dispatch(n2, DeviceType.ANDROID)
    assert len(handler.handled_notifications) == 1
    assert n2.delivered is False
