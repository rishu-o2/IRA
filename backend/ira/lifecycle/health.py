"""
lifecycle/health.py - Health checks for the platform.
"""
def get_system_health(components: dict) -> dict:
    """Return health status of various platform components."""
    status = {"ok": True, "components": {}}
    
    if "device_manager" in components:
        status["components"]["device_manager"] = "up"
        
    if "session_manager" in components:
        status["components"]["session_manager"] = "up"
        
    if "event_bus" in components:
        status["components"]["event_bus"] = "up"
        
    return status
