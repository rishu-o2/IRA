"""
knowledge/service.py - Abstraction layer coordinating extraction and storage.
"""
from __future__ import annotations

from .extractor import KnowledgeExtractor
from .graph import KnowledgeGraphBuilder
from .store import KnowledgeStore


class KnowledgeService:
    """Coordinates the extractor, store, and graph to process memory text."""

    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store
        self.extractor = KnowledgeExtractor()
        self.graph_builder = KnowledgeGraphBuilder(store)

    def process(self, text: str) -> None:
        """Extracts entities and relationships from text and stores them."""
        entities, relationships = self.extractor.extract(text)
        
        # Deduplicate and store entities
        stored_entities_by_name = {}
        for entity in entities:
            # Check if it already exists by name
            existing = self.store.find_entity_by_name(entity.name)
            if existing:
                # Merge logic could go here; for now, we just reuse the existing ID
                existing.access_count += 1
                self.store.update_entity(existing)
                stored_entities_by_name[entity.name] = existing
            else:
                self.store.create_entity(entity)
                stored_entities_by_name[entity.name] = entity

        # Store relationships ensuring correct mapped IDs
        for rel in relationships:
            # Re-map IDs based on what was actually stored
            src_name = next((e.name for e in entities if e.id == rel.source_entity), None)
            tgt_name = next((e.name for e in entities if e.id == rel.target_entity), None)
            
            if src_name and tgt_name and src_name in stored_entities_by_name and tgt_name in stored_entities_by_name:
                rel.source_entity = stored_entities_by_name[src_name].id
                rel.target_entity = stored_entities_by_name[tgt_name].id
                self.store.create_relationship(rel)
