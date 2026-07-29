from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RetryPolicy:
    """Configurable retry policy for the execution engine."""
    max_attempts: int = 3
    backoff_seconds: list[int] = field(default_factory=lambda: [0, 1, 2])

    _SAFE_OPERATIONS = {
        "open_app",
        "open_website",
        "open_known_folder",
        "open_path",
        "search_web",
        "get_battery_status",
    }

    _UNSAFE_OPERATIONS = {
        "delete",
        "shutdown_system",
        "sleep_system",
        "lock_screen",
        "send_email",
    }

    def is_safe(self, operation: str) -> bool:
        """Determines if an operation is idempotent and safe to retry."""
        return operation in self._SAFE_OPERATIONS

    def get_delay(self, attempt: int) -> int:
        """Returns the delay in seconds for the given retry attempt (1-indexed)."""
        idx = min(attempt - 1, len(self.backoff_seconds) - 1)
        if idx < 0:
            return 0
        return self.backoff_seconds[idx]

    def wait(self, attempt: int) -> None:
        """Blocks execution for the backoff duration of the given attempt."""
        delay = self.get_delay(attempt)
        if delay > 0:
            time.sleep(delay)
