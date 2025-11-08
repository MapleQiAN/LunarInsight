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
        print(f"💾 [图谱构建] 开始将 {len(triplets)} 个三元组写入 Neo4j...")
        
        created_concepts = set()
        created_relationships = 0
        
        for idx, triplet in enumerate(triplets, 1):
            # Ensure concepts exist
            if triplet.subject not in created_concepts:
                neo4j_client.create_concept(triplet.subject)
                created_concepts.add(triplet.subject)
            
            if triplet.object not in created_concepts:
                neo4j_client.create_concept(triplet.object)
                created_concepts.add(triplet.object)
            
            # Create relationship between concepts
            rel_type = triplet.predicate.upper().replace(" ", "_")
            neo4j_client.create_relationship(
                source_id=triplet.subject,
                target_id=triplet.object,
                rel_type=rel_type,
                properties={
                    "confidence": triplet.confidence,
                    "evidence": triplet.evidence,
                    "doc_id": doc_id,
                    "chunk_id": triplet.chunk_id
                }
            )
            created_relationships += 1
            
            # 显示前5个三元组的详细信息
            if idx <= 5:
                print(f"   [{idx}] {triplet.subject} --[{rel_type}]--> {triplet.object} (置信度: {triplet.confidence:.2f})")
            
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
        
        if len(triplets) > 5:
            print(f"   ... 还有 {len(triplets) - 5} 个三元组")
        
        print(f"✅ [图谱构建] 完成:")
        print(f"   - 创建/更新概念数: {len(created_concepts)}")
        print(f"   - 创建关系数: {created_relationships}")

