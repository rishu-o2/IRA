from __future__ import annotations

from datetime import datetime
from uuid import UUID

from backend.ira.memory.long_term import MemoryEntry, MemoryStore, MemoryType


def test_add_memory_and_retrieve_it() -> None:
    store = MemoryStore()
    entry = MemoryEntry(type=MemoryType.FACT, content="IRA remembers Python.")

    store.add(entry)

    assert store.get(entry.id) == entry


def test_search_by_keyword() -> None:
    store = MemoryStore()
    entry = MemoryEntry(type=MemoryType.NOTE, content="The keyboard shortcut is ctrl+k.")
    store.add(entry)

    assert store.search("keyboard") == [entry]


def test_remove_memory() -> None:
    store = MemoryStore()
    entry = MemoryEntry(type=MemoryType.GOAL, content="Finish Phase 9.")
    store.add(entry)

    store.remove(entry.id)

    assert store.get(entry.id) is None
    assert store.all() == []


def test_clear_store() -> None:
    store = MemoryStore()
    store.add(MemoryEntry(type=MemoryType.FACT, content="One"))
    store.add(MemoryEntry(type=MemoryType.FACT, content="Two"))

    store.clear()

    assert store.all() == []


def test_uuid_uniqueness() -> None:
    first = MemoryEntry(type=MemoryType.NOTE, content="First")
    second = MemoryEntry(type=MemoryType.NOTE, content="Second")

    assert first.id != second.id
    UUID(first.id)
    UUID(second.id)


def test_timestamp_creation() -> None:
    entry = MemoryEntry(type=MemoryType.CONVERSATION, content="Hello.")

    assert isinstance(entry.created_at, datetime)
    assert isinstance(entry.updated_at, datetime)
    assert entry.created_at.tzinfo is not None
    assert entry.updated_at.tzinfo is not None


def test_search_returns_multiple_matches() -> None:
    store = MemoryStore()
    first = MemoryEntry(type=MemoryType.PREFERENCE, content="Prefers concise answers.")
    second = MemoryEntry(type=MemoryType.NOTE, content="Concise summaries help.")
    miss = MemoryEntry(type=MemoryType.FACT, content="Uses Windows.")
    store.add(first)
    store.add(second)
    store.add(miss)

    assert store.search("concise") == [first, second]


def test_missing_memory_returns_none() -> None:
    store = MemoryStore()

    assert store.get("missing") is None
