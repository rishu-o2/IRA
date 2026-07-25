"""
events/bus.py - Synchronous event bus.
"""
import logging
from collections import defaultdict
from typing import Callable, Any
from .models import IRAEvent

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        # Map event type to a set of handlers
        self._subscribers: dict[str, set[Callable[[IRAEvent], Any]]] = defaultdict(set)

    def subscribe(self, event_type: str, handler: Callable[[IRAEvent], Any]) -> None:
        """Subscribe a handler to a specific event_type, or '*' for all events."""
        event_type_str = getattr(event_type, "value", str(event_type))
        self._subscribers[event_type_str].add(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[IRAEvent], Any]) -> None:
        """Remove a handler from an event_type."""
        event_type_str = getattr(event_type, "value", str(event_type))
        if handler in self._subscribers[event_type_str]:
            self._subscribers[event_type_str].remove(handler)

    def publish(self, event: IRAEvent) -> None:
        """Publish an event to all interested subscribers."""
        event_type_str = getattr(event.event_type, "value", str(event.event_type))
        
        # Notify specific subscribers
        for handler in list(self._subscribers.get(event_type_str, [])):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type_str}: {e}")

        # Notify wildcard subscribers
        for handler in list(self._subscribers.get("*", [])):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in wildcard event handler for {event_type_str}: {e}")
