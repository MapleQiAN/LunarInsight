"""Graph service for ingesting triplets into Neo4j."""
from typing import List
from models.document import Triplet
from infra.neo4j_client import neo4j_client


class GraphService:
    """Service for graph operations."""
    
    def ingest_triplets(self, doc_id: str, triplets: List[Triplet]):
        """
        Ingest triplets into Neo4j graph.
        
        Args:
            doc_id: Document ID
            triplets: List of triplets to ingest
        """
        for triplet in triplets:
            # Ensure concepts exist
            neo4j_client.create_concept(triplet.subject)
            neo4j_client.create_concept(triplet.object)
            
            # Create relationship between concepts
            neo4j_client.create_relationship(
                source_id=triplet.subject,
                target_id=triplet.object,
                rel_type=triplet.predicate.upper().replace(" ", "_"),
                properties={
                    "confidence": triplet.confidence,
                    "evidence": triplet.evidence,
                    "doc_id": doc_id,
                    "chunk_id": triplet.chunk_id
                }
            )
            
            # Link document to concepts
            if doc_id:
                neo4j_client.link_concept_to_document(
                    concept_name=triplet.subject,
                    doc_id=doc_id,
                    page=triplet.evidence.get("page"),
                    offset=triplet.evidence.get("offset"),
                    evidence=triplet.evidence.get("text", "")[:500]
                )
                
                neo4j_client.link_concept_to_document(
                    concept_name=triplet.object,
                    doc_id=doc_id,
                    page=triplet.evidence.get("page"),
                    offset=triplet.evidence.get("offset"),
                    evidence=triplet.evidence.get("text", "")[:500]
                )

