"""
knowledge/models.py - Core representations of the knowledge graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid


class Importance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EntityType(str, Enum):
    PERSON = "PERSON"
    PLACE = "PLACE"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"
    EVENT = "EVENT"
    DATE = "DATE"
    TIME = "TIME"
    DEVICE = "DEVICE"
    APPLICATION = "APPLICATION"
    WEBSITE = "WEBSITE"
    DOCUMENT = "DOCUMENT"
    GOAL = "GOAL"
    TASK = "TASK"
    PREFERENCE = "PREFERENCE"
    UNKNOWN = "UNKNOWN"


class RelationshipType(str, Enum):
    HAS_DATE = "HAS_DATE"
    AT_COMPANY = "AT_COMPANY"
    USES_EDITOR = "USES_EDITOR"
    LIKES = "LIKES"
    DISLIKES = "DISLIKES"
    LOCATED_IN = "LOCATED_IN"
    WORKS_AT = "WORKS_AT"
    WORKS_ON = "WORKS_ON"
    HAS_STATUS = "HAS_STATUS"
    IS_A = "IS_A"
    RELATED_TO = "RELATED_TO"


@dataclass
class Entity:
    name: str
    entity_type: EntityType = EntityType.UNKNOWN
    category: str | None = None
    importance: Importance = Importance.MEDIUM
    source: str | None = None
    confidence: float = 1.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tags: set[str] = field(default_factory=set)
    last_accessed: datetime | None = None
    access_count: int = 0
    is_archived: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Relationship:
    source_entity: str  # Entity ID
    target_entity: str  # Entity ID
    relationship_type: RelationshipType
    confidence: float = 1.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Context:
    entity_id: str
    conversation_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class KnowledgeGraph:
    """A subgraph or complete graph representation."""
    entities: dict[str, Entity] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def add_relationship(self, relationship: Relationship) -> None:
        self.relationships.append(relationship)
