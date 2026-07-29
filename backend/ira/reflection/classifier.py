from __future__ import annotations

from enum import Enum
import builtins


class FailureCategory(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    PERMISSION = "PERMISSION"
    NETWORK = "NETWORK"
    TIMEOUT = "TIMEOUT"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    TOOL_ERROR = "TOOL_ERROR"
    UNKNOWN = "UNKNOWN"


class FailureClassifier:
    """Classifies Python exceptions into deterministic FailureCategory enums."""

    @classmethod
    def classify(cls, exception: Exception) -> FailureCategory:
        # Check standard python exceptions explicitly as requested
        if isinstance(exception, FileNotFoundError):
            return FailureCategory.NOT_FOUND
        if isinstance(exception, PermissionError):
            return FailureCategory.PERMISSION
        if isinstance(exception, TimeoutError):
            return FailureCategory.TIMEOUT
        if isinstance(exception, ConnectionError):
            return FailureCategory.NETWORK
        
        # ActionError maps to TOOL_ERROR unless message gives it away
        if type(exception).__name__ == "ActionError":
            # Some internal errors might contain 'could not find' in message
            if "could not find" in str(exception).lower():
                return FailureCategory.NOT_FOUND
            return FailureCategory.TOOL_ERROR

        if isinstance(exception, ValueError) or isinstance(exception, TypeError):
            return FailureCategory.INVALID_ARGUMENT
        
        # Generic fallback
        if isinstance(exception, OSError):
            return FailureCategory.TOOL_ERROR
            
        return FailureCategory.UNKNOWN
