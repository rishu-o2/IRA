"""
AssistantState – lightweight dataclass for tracking the most recently
seen context values within a conversation session.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AssistantState:
    """Holds the latest contextual values produced during a session."""

    last_command: Optional[str] = None
    last_app: Optional[str] = None
    last_website: Optional[str] = None
    last_topic: Optional[str] = None
    last_action: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.now)
