import pytest
from ira.sync.models import SyncEventType
from ira.sync.queue import SyncQueue
from ira.sync.manager import SyncManager
from ira.sync.events import SyncEventFactory

def test_sync_queue_enqueue_dequeue():
    queue = SyncQueue()
    record1 = SyncEventFactory.create_memory_sync("dev-1", {"key": "val"}, version=1)
    record2 = SyncEventFactory.create_goal_sync("dev-1", {"goal": "id"}, version=2)
    
    queue.enqueue(record1)
    queue.enqueue(record2)
    
    assert queue.size() == 2
    assert queue.peek() == record1
    
    dequeued1 = queue.dequeue()
    assert dequeued1 == record1
    
    dequeued2 = queue.dequeue()
    assert dequeued2 == record2
    
    assert queue.dequeue() is None

def test_sync_manager_sync_all():
    queue = SyncQueue()
    record1 = SyncEventFactory.create_memory_sync("dev-1", {})
    record2 = SyncEventFactory.create_goal_sync("dev-2", {})
    
    queue.enqueue(record1)
    queue.enqueue(record2)
    
    manager = SyncManager(queue)
    manager.sync_all("dev-1")
    
    assert record1.record_id in manager._synced_records
    assert record2.record_id not in manager._synced_records
