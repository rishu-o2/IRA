from __future__ import annotations

from backend.ira.memory.long_term import MemoryStore

from .context import Context
from .ranker import MemoryRanker


class ContextRetriever:
    def __init__(self, store: MemoryStore, ranker: MemoryRanker | None = None) -> None:
        self.store = store
        self.ranker = ranker or MemoryRanker()

    def retrieve(self, query: str, limit: int = 5) -> Context:
        if limit <= 0:
            return Context(())
        ranked = self.ranker.rank(query, self.store.all())
        return Context(tuple(ranked[:limit]))
