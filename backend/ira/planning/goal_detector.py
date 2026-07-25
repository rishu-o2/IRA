"""
planning/goal_detector.py - Detects and formalizes goals from user intents.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .models import Goal, GoalStatus


class GoalDetector:
    """Detects whether a message contains a goal, estimating confidence, priority, and deadline."""

    def detect(self, text: str) -> Goal:
        """Parses the text and returns a structured Goal object."""
        lowered = text.lower()
        
        priority = "MEDIUM"
        confidence = 0.8
        deadline: datetime | None = None
        
        # Priority detection
        if any(w in lowered for w in ["urgent", "asap", "critical", "emergency"]):
            priority = "CRITICAL"
            confidence += 0.1
        elif any(w in lowered for w in ["important", "high priority"]):
            priority = "HIGH"
        elif any(w in lowered for w in ["low priority", "whenever", "no rush"]):
            priority = "LOW"
            
        # Basic deadline detection (deterministic regex for demo)
        if "today" in lowered:
            deadline = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
        elif "tomorrow" in lowered:
            deadline = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=23, minute=59, second=59)
        else:
            # check for "by friday" etc.
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for day in days:
                if f"by {day}" in lowered or f"on {day}" in lowered:
                    # simplistic mapping, we just set a generic future deadline for the sake of the deterministic model
                    deadline = datetime.now(timezone.utc) + timedelta(days=7)
                    break

        return Goal(
            description=text.strip(),
            priority=priority,
            deadline=deadline,
            confidence=min(confidence, 1.0),
            status=GoalStatus.PENDING,
        )
