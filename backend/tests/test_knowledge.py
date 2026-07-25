import pytest
import tempfile
import os

from ira.knowledge.models import Entity, EntityType, Importance, Relationship, RelationshipType
from ira.knowledge.store import KnowledgeStore
from ira.knowledge.extractor import KnowledgeExtractor
from ira.storage.sqlite import SQLiteStorage
from ira.storage.migrations import apply_migrations

@pytest.fixture
def knowledge_store():
    import sqlite3
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    storage = SQLiteStorage(path)
    store = KnowledgeStore(storage)
    yield store
    # Close all SQLite connections before removing (required on Windows)
    try:
        sqlite3.connect(path).close()
    except Exception:
        pass
    try:
        os.remove(path)
    except PermissionError:
        pass  # Windows may still hold the lock; temp file will be cleaned on reboot

def test_entity_creation_and_retrieval(knowledge_store):
    entity = Entity(
        name="Test Project",
        entity_type=EntityType.PROJECT,
        category="Work",
        importance=Importance.HIGH,
        tags={"test", "project"}
    )
    knowledge_store.create_entity(entity)
    
    retrieved = knowledge_store.find_entity(entity.id)
    assert retrieved is not None
    assert retrieved.name == "Test Project"
    assert retrieved.entity_type == EntityType.PROJECT
    assert retrieved.importance == Importance.HIGH
    assert "test" in retrieved.tags
    
def test_relationship_creation(knowledge_store):
    entity1 = Entity(name="User", entity_type=EntityType.PERSON)
    entity2 = Entity(name="Google", entity_type=EntityType.ORGANIZATION)
    
    knowledge_store.create_entity(entity1)
    knowledge_store.create_entity(entity2)
    
    rel = Relationship(
        source_entity=entity1.id,
        target_entity=entity2.id,
        relationship_type=RelationshipType.WORKS_AT,
        confidence=0.9
    )
    knowledge_store.create_relationship(rel)
    
    rels = knowledge_store.find_relationships(entity1.id)
    assert len(rels) == 1
    assert rels[0].target_entity == entity2.id
    assert rels[0].relationship_type == RelationshipType.WORKS_AT

def test_extractor_preference_rule():
    extractor = KnowledgeExtractor()
    entities, rels = extractor.extract("My favorite editor is VS Code")
    
    assert len(entities) == 2
    assert entities[0].name == "User"
    assert entities[0].entity_type == EntityType.PERSON
    assert entities[1].name == "VS Code"
    assert entities[1].entity_type == EntityType.PREFERENCE
    assert entities[1].category == "editor"
    
    assert len(rels) == 1
    assert rels[0].relationship_type == RelationshipType.LIKES
    
def test_extractor_work_rule():
    extractor = KnowledgeExtractor()
    entities, rels = extractor.extract("I work at Google")
    
    assert len(entities) == 2
    assert entities[0].name == "User"
    assert entities[1].name == "Google"
    assert entities[1].entity_type == EntityType.ORGANIZATION
    
    assert len(rels) == 1
    assert rels[0].relationship_type == RelationshipType.WORKS_AT
