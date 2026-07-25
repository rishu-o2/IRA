"""
knowledge/graph.py - Operations to build, connect, traverse, and summarize the Knowledge Graph.
"""
from __future__ import annotations

from .models import Entity, KnowledgeGraph, Relationship
from .store import KnowledgeStore


class KnowledgeGraphBuilder:
    """Provides methods to build, connect, traverse, summarize, and export knowledge graphs."""

    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store

    def build_from_entity(self, entity_id: str, max_depth: int = 1) -> KnowledgeGraph:
        """Traverse the store starting from a root entity to build a subgraph."""
        graph = KnowledgeGraph()
        visited_entities: set[str] = set()
        visited_relationships: set[str] = set()

        def _traverse(current_id: str, current_depth: int) -> None:
            if current_depth > max_depth or current_id in visited_entities:
                return

            entity = self.store.find_entity(current_id)
            if not entity:
                return

            graph.add_entity(entity)
            visited_entities.add(current_id)

            if current_depth < max_depth:
                rels = self.store.find_relationships(current_id)
                for rel in rels:
                    if rel.id not in visited_relationships:
                        graph.add_relationship(rel)
                        visited_relationships.add(rel.id)
                    
                    # Traverse to the connected entity
                    next_id = rel.target_entity if rel.source_entity == current_id else rel.source_entity
                    _traverse(next_id, current_depth + 1)

        _traverse(entity_id, 0)
        return graph

    def connect(self, source: Entity, target: Entity, relationship: Relationship) -> None:
        """Connects two entities via a relationship and saves to store."""
        if not self.store.find_entity(source.id):
            self.store.create_entity(source)
        if not self.store.find_entity(target.id):
            self.store.create_entity(target)
            
        relationship.source_entity = source.id
        relationship.target_entity = target.id
        self.store.create_relationship(relationship)

    def traverse(self, start_entity_id: str) -> list[Entity]:
        """Simple breadth-first retrieval of immediate neighbours."""
        rels = self.store.find_relationships(start_entity_id)
        neighbours = []
        for rel in rels:
            neighbor_id = rel.target_entity if rel.source_entity == start_entity_id else rel.source_entity
            neighbor = self.store.find_entity(neighbor_id)
            if neighbor:
                neighbours.append(neighbor)
        return neighbours

    def summarize(self, graph: KnowledgeGraph) -> str:
        """Generates a text summary of the graph's contents for prompt injection."""
        lines = []
        for rel in graph.relationships:
            src = graph.entities.get(rel.source_entity)
            tgt = graph.entities.get(rel.target_entity)
            if src and tgt:
                lines.append(f"{src.name} [{rel.relationship_type.value}] {tgt.name}")
        
        for ent in graph.entities.values():
            if ent.category and not any(r.source_entity == ent.id or r.target_entity == ent.id for r in graph.relationships):
                lines.append(f"{ent.name} is categorized as {ent.category}")
                
        return "\n".join(lines)

    def export(self) -> dict:
        """Exports the entire store's entities and relationships as a raw dict."""
        entities = self.store.list_entities(limit=1000)
        return {
            "entities": [e.__dict__ for e in entities],
            "relationships": [] # To be implemented via a generic list_relationships method if needed
        }
