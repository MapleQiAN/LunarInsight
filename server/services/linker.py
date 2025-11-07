"""Entity linking and alias merging service."""
from typing import List, Dict, Optional
from models.document import Triplet
from infra.neo4j_client import neo4j_client


class EntityLinker:
    """Link entities and merge aliases."""
    
    def __init__(self):
        # Simple alias dictionary (in production, this would be more sophisticated)
        self.alias_dict: Dict[str, str] = {}
    
    def link_and_merge(self, triplets: List[Triplet]) -> List[Triplet]:
        """
        Link entities to existing concepts and merge aliases.
        
        Args:
            triplets: List of extracted triplets
            
        Returns:
            List of triplets with linked entities
        """
        linked_triplets = []
        
        for triplet in triplets:
            # Normalize subject and object
            subject_normalized = self._normalize_entity(triplet.subject)
            object_normalized = self._normalize_entity(triplet.object)
            
            # Check for existing concepts
            subject_canonical = self._find_or_create_concept(subject_normalized)
            object_canonical = self._find_or_create_concept(object_normalized)
            
            # Update triplet with canonical names
            triplet.subject = subject_canonical
            triplet.object = object_canonical
            
            linked_triplets.append(triplet)
        
        return linked_triplets
    
    def _normalize_entity(self, entity: str) -> str:
        """Normalize entity name (lowercase, strip, etc.)."""
        # Basic normalization
        normalized = entity.strip()
        
        # Check alias dictionary
        if normalized.lower() in self.alias_dict:
            return self.alias_dict[normalized.lower()]
        
        return normalized
    
    def _find_or_create_concept(self, name: str) -> str:
        """
        Find existing concept or create new one.
        Returns canonical name.
        """
        if not name:
            return name
        
        # Check if concept exists in Neo4j
        existing = neo4j_client.find_concept_by_name(name)
        if existing:
            return name
        
        # Check for similar concepts (simplified)
        similar = neo4j_client.find_similar_concepts(name)
        if similar:
            # Use the first similar concept as canonical
            canonical = similar[0]['c']['name']
            # Store alias mapping
            self.alias_dict[name.lower()] = canonical
            return canonical
        
        # Create new concept
        neo4j_client.create_concept(name)
        return name
    
    def add_alias(self, alias: str, canonical: str):
        """Add an alias mapping."""
        self.alias_dict[alias.lower()] = canonical

