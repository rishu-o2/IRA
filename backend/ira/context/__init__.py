"""
ira/context – Sprint 7.3 Conversation Context package.

Provides:
    ConversationContext  – per-conversation slot state
    ContextEntity        – a named entity mentioned in conversation
    ContextDelta         – stateless update produced by ContextExtractor
    ConversationContextManager – in-memory context store
    ContextExtractor     – extracts ContextDelta from executed commands
    ReferenceResolver    – deterministic pronoun / reference resolution
"""
from .models import ConversationContext, ContextDelta, ContextEntity
from .manager import ConversationContextManager
from .extractor import ContextExtractor
from .resolver import ReferenceResolver, ResolvedRequest

__all__ = [
    "ConversationContext",
    "ContextDelta",
    "ContextEntity",
    "ConversationContextManager",
    "ContextExtractor",
    "ReferenceResolver",
    "ResolvedRequest",
]
