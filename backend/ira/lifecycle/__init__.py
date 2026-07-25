"""
lifecycle module
"""
from .health import get_system_health
from .shutdown import shutdown_platform
from .startup import initialize_platform

__all__ = ["get_system_health", "initialize_platform", "shutdown_platform"]
