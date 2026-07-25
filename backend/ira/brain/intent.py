from __future__ import annotations

from .models import BrainIntent, BrainRequest


class IntentClassifier:
    """Classifies incoming user text without changing current routing behavior."""

    def classify(self, request: BrainRequest) -> BrainIntent:
        normalized = " ".join(request.message.strip().split())
        return BrainIntent(
            message=request.message,
            normalized_message=normalized,
            kind="command" if normalized else "empty",
        )
