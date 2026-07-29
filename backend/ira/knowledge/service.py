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

    def remember_experience(self, experience: Any) -> None:
        """Saves successful or recovered execution details into the structured knowledge graph."""
        if not experience.success:
            return

        from .models import Entity, EntityType, Relationship, RelationshipType
        
        tool = experience.tool
        orig_params = experience.parameters
        pref_params = experience.metadata.get("recovered_parameters", orig_params)
        
        if tool == "open_app" and "app_name" in orig_params:
            orig_name = orig_params["app_name"]
            pref_name = pref_params["app_name"]
            
            # Look up or create entities
            e1 = self.store.find_entity_by_name(orig_name)
            if not e1:
                e1 = Entity(name=orig_name, entity_type=EntityType.APPLICATION, category="app")
                self.store.create_entity(e1)
            
            if orig_name != pref_name:
                e2 = self.store.find_entity_by_name(pref_name)
                if not e2:
                    e2 = Entity(name=pref_name, entity_type=EntityType.APPLICATION, category="app_path")
                    self.store.create_entity(e2)
                
                rel = Relationship(
                    source_entity=e1.id,
                    target_entity=e2.id,
                    relationship_type=RelationshipType.RELATED_TO
                )
                self.store.create_relationship(rel)

        elif tool == "open_website" and "url" in orig_params:
            orig_url = orig_params["url"]
            pref_url = pref_params["url"]
            
            e1 = self.store.find_entity_by_name(orig_url)
            if not e1:
                e1 = Entity(name=orig_url, entity_type=EntityType.WEBSITE, category="shortcut")
                self.store.create_entity(e1)
            
            if orig_url != pref_url:
                e2 = self.store.find_entity_by_name(pref_url)
                if not e2:
                    e2 = Entity(name=pref_url, entity_type=EntityType.WEBSITE, category="url")
                    self.store.create_entity(e2)
                
                rel = Relationship(
                    source_entity=e1.id,
                    target_entity=e2.id,
                    relationship_type=RelationshipType.RELATED_TO
                )
                self.store.create_relationship(rel)
