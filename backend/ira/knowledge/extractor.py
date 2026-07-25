"""
knowledge/extractor.py - Deterministic rules-based knowledge extraction.
"""
from __future__ import annotations

import re

from .models import Entity, EntityType, Importance, Relationship, RelationshipType


class KnowledgeExtractor:
    """Uses deterministic rules to extract entities and relationships from text."""

    def extract(self, text: str) -> tuple[list[Entity], list[Relationship]]:
        entities: list[Entity] = []
        relationships: list[Relationship] = []

        # Rule 1: "My X is Y" or "My X are Y" -> Preference or Fact
        match = re.search(r"my\s+([\w\s]+)\s+(?:is|are)\s+([\w\s]+)", text, re.IGNORECASE)
        if match:
            subject = match.group(1).strip()
            target = match.group(2).strip()
            
            # If it's a known preference
            if "favorite" in subject.lower() or "favourite" in subject.lower() or "prefer" in subject.lower():
                pref_entity = Entity(
                    name="User",
                    entity_type=EntityType.PERSON,
                    importance=Importance.HIGH,
                    confidence=1.0,
                )
                target_entity = Entity(
                    name=target,
                    entity_type=EntityType.PREFERENCE,
                    category=subject.lower().replace("favorite ", "").replace("favourite ", ""),
                    importance=Importance.MEDIUM,
                    confidence=0.9,
                )
                rel = Relationship(
                    source_entity=pref_entity.id,
                    target_entity=target_entity.id,
                    relationship_type=RelationshipType.LIKES,
                    confidence=0.95,
                )
                entities.extend([pref_entity, target_entity])
                relationships.append(rel)

        # Rule 2: "Interview is Friday" or similar date assignments
        match = re.search(r"([\w\s]+)\s+(?:is|is on)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)", text, re.IGNORECASE)
        if match:
            event_name = match.group(1).strip()
            if event_name.lower().startswith("my "):
                event_name = event_name[3:]
            date_val = match.group(2).strip()
            
            event_ent = Entity(
                name=event_name,
                entity_type=EntityType.EVENT,
                category="Schedule",
                importance=Importance.HIGH,
                confidence=0.85,
            )
            date_ent = Entity(
                name=date_val,
                entity_type=EntityType.DATE,
                importance=Importance.MEDIUM,
                confidence=0.95,
            )
            rel = Relationship(
                source_entity=event_ent.id,
                target_entity=date_ent.id,
                relationship_type=RelationshipType.HAS_DATE,
                confidence=0.9,
            )
            entities.extend([event_ent, date_ent])
            relationships.append(rel)

        # Rule 3: "I work at [Company]"
        match = re.search(r"i work at\s+([\w\s]+)", text, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            user_ent = Entity(
                name="User",
                entity_type=EntityType.PERSON,
                importance=Importance.CRITICAL,
                confidence=1.0,
            )
            company_ent = Entity(
                name=company,
                entity_type=EntityType.ORGANIZATION,
                importance=Importance.HIGH,
                confidence=0.9,
            )
            rel = Relationship(
                source_entity=user_ent.id,
                target_entity=company_ent.id,
                relationship_type=RelationshipType.WORKS_AT,
                confidence=0.95,
            )
            entities.extend([user_ent, company_ent])
            relationships.append(rel)

        # Basic fallback if no rules match but we want to capture the raw text as a generic note
        if not entities:
            pass
            
        return entities, relationships
