import pytest
from ira.events.models import IRAEvent, EventType
from ira.events.bus import EventBus

def test_event_bus_subscribe_publish():
    bus = EventBus()
    received = []

    def handler(event: IRAEvent):
        received.append(event)

    bus.subscribe(EventType.GOAL_CREATED, handler)
    
    event = IRAEvent(event_type=EventType.GOAL_CREATED, payload={"foo": "bar"})
    bus.publish(event)
    
    assert len(received) == 1
    assert received[0].payload["foo"] == "bar"

def test_event_bus_unsubscribe():
    bus = EventBus()
    received = []

    def handler(event: IRAEvent):
        received.append(event)

    bus.subscribe(EventType.GOAL_CREATED, handler)
    bus.unsubscribe(EventType.GOAL_CREATED, handler)
    
    event = IRAEvent(event_type=EventType.GOAL_CREATED, payload={"foo": "bar"})
    bus.publish(event)
    
    assert len(received) == 0

def test_event_bus_wildcard_subscribe():
    bus = EventBus()
    received = []

    def wildcard_handler(event: IRAEvent):
        received.append(event)

    bus.subscribe("*", wildcard_handler)
    
    event1 = IRAEvent(event_type=EventType.GOAL_CREATED, payload={})
    event2 = IRAEvent(event_type=EventType.TASK_STARTED, payload={})
    
    bus.publish(event1)
    bus.publish(event2)
    
    assert len(received) == 2
    assert received[0].event_type == EventType.GOAL_CREATED
    assert received[1].event_type == EventType.TASK_STARTED
