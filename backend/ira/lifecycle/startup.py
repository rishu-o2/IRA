"""
lifecycle/startup.py - Startup orchestration.
"""
import logging
from ..device.manager import DeviceManager
from ..device.registry import DeviceRegistry
from ..session_manager.manager import SessionManager
from ..events.bus import EventBus
from ..notifications.dispatcher import NotificationDispatcher
from ..notifications.queue import NotificationQueue
from ..sync.manager import SyncManager
from ..sync.queue import SyncQueue
from ..security.trust import TrustManager

logger = logging.getLogger(__name__)

def initialize_platform():
    """Initialize all platform managers and return them."""
    logger.info("Initializing IRA Platform Components...")
    
    trust_manager = TrustManager()
    device_registry = DeviceRegistry()
    device_manager = DeviceManager(device_registry, trust_manager)
    
    session_manager = SessionManager()
    event_bus = EventBus()
    
    notification_queue = NotificationQueue()
    notification_dispatcher = NotificationDispatcher()
    
    sync_queue = SyncQueue()
    sync_manager = SyncManager(sync_queue)
    
    return {
        "trust_manager": trust_manager,
        "device_manager": device_manager,
        "session_manager": session_manager,
        "event_bus": event_bus,
        "notification_dispatcher": notification_dispatcher,
        "notification_queue": notification_queue,
        "sync_manager": sync_manager,
        "sync_queue": sync_queue,
    }
