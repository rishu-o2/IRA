"""
notifications/dispatcher.py - Notification Dispatcher.
"""
import logging
from typing import Protocol
from .models import Notification
from ..device.models import DeviceType

logger = logging.getLogger(__name__)

class NotificationHandler(Protocol):
    def handle(self, notification: Notification) -> bool:
        ...

class NotificationDispatcher:
    def __init__(self):
        self._handlers: dict[DeviceType, NotificationHandler] = {}

    def register_handler(self, device_type: DeviceType, handler: NotificationHandler) -> None:
        self._handlers[device_type] = handler

    def dispatch(self, notification: Notification, target_device_type: DeviceType = DeviceType.DESKTOP) -> None:
        handler = self._handlers.get(target_device_type)
        if handler:
            try:
                success = handler.handle(notification)
                if success:
                    notification.delivered = True
            except Exception as e:
                logger.error(f"Failed to dispatch notification to {target_device_type}: {e}")
        else:
            logger.warning(f"No notification handler registered for {target_device_type}")
