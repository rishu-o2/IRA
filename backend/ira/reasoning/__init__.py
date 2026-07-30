"""
ira/reasoning – Sprint 7.3 Reasoning package.

Provides:
    ReasoningResult  – the structured output of ReasoningEngine.reason()
    ReasoningEngine  – deterministic 4-priority reasoning layer
"""
from .models import ReasoningResult
from .engine import ReasoningEngine

__all__ = ["ReasoningResult", "ReasoningEngine"]
