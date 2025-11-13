"""
阶段 6: 幂等落库 (Graph Service)

将构建结果写入 Neo4j，确保幂等性与证据回溯
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("graphrag.stage6")


class GraphService:
    """
    图谱服务
    
    负责将构建结果写入 Neo4j，支持幂等性与证据回溯
    """
    
    def __init__(self):
        logger.info("GraphService initialized")
    
    def store_chunk(self, chunk: Dict[str, Any]):
        """
        存储 Chunk 节点
        
        Args:
            chunk: Chunk 数据
        """
        logger.debug(f"存储 Chunk: {chunk['id']}")
        from infra.neo4j_client import neo4j_client
        query = """
        MERGE (c:Chunk {id: $id})
        SET c.doc_id = $doc_id,
            c.section_path = $section_path,
            c.text = $text,
            c.embedding = $embedding,
            c.created_at = coalesce(c.created_at, datetime()),
            c.updated_at = datetime()
        RETURN c
        """
        neo4j_client.execute_query(query, {
            "id": chunk.get("id"),
            "doc_id": chunk.get("doc_id"),
            "section_path": chunk.get("section_path"),
            "text": chunk.get("text"),
            "embedding": chunk.get("embedding"),
        })
    
    def store_concept(self, concept: Dict[str, Any]):
        """
        存储 Concept 节点
        
        Args:
            concept: Concept 数据
        """
        logger.debug(f"存储 Concept: {concept['id']}")
        from infra.neo4j_client import neo4j_client
        query = """
        MERGE (c:Concept {name: $name})
        SET c.domain = $domain,
            c.meta = $meta,
            c.created_at = coalesce(c.created_at, datetime()),
            c.updated_at = datetime()
        RETURN c
        """
        neo4j_client.execute_query(query, {
            "name": concept.get("id") or concept.get("name"),
            "domain": concept.get("domain"),
            "meta": concept.get("meta"),
        })
    
    def store_claim(self, claim: Dict[str, Any]):
        """
        存储 Claim 节点
        
        Args:
            claim: Claim 数据
        """
        logger.debug(f"存储 Claim: {claim['id']}")
        from infra.neo4j_client import neo4j_client
        query = """
        MERGE (cl:Claim {id: $id})
        SET cl.text = $text,
            cl.doc_id = $doc_id,
            cl.chunk_id = $chunk_id,
            cl.claim_type = $claim_type,
            cl.embedding = $embedding,
            cl.confidence = $confidence,
            cl.created_at = coalesce(cl.created_at, datetime()),
            cl.updated_at = datetime()
        RETURN cl
        """
        neo4j_client.execute_query(query, {
            "id": claim.get("id"),
            "text": claim.get("text"),
            "doc_id": claim.get("doc_id"),
            "chunk_id": claim.get("chunk_id"),
            "claim_type": claim.get("claim_type"),
            "embedding": claim.get("embedding"),
            "confidence": claim.get("confidence"),
        })
    
    def store_relation(self, relation: Dict[str, Any]):
        """
        存储关系
        
        Args:
            relation: 关系数据 {source_id, target_id, type, properties}
        """
        logger.debug(f"存储关系: {relation['source_id']} -{relation['type']}-> {relation['target_id']}")
        from infra.neo4j_client import neo4j_client
        query = f"""
        MATCH (s), (t)
        WHERE (exists(s.id) AND s.id = $sid) OR (exists(s.name) AND s.name = $sid)
          AND (exists(t.id) AND t.id = $tid) OR (exists(t.name) AND t.name = $tid)
        MERGE (s)-[r:{relation.get('type')}]->(t)
        SET r += $props,
            r.created_at = coalesce(r.created_at, datetime()),
            r.updated_at = datetime()
        RETURN r
        """
        neo4j_client.execute_query(query, {
            "sid": relation.get("source_id"),
            "tid": relation.get("target_id"),
            "props": relation.get("properties", {}),
        })
    
    def store_with_provenance(
        self,
        node: Dict[str, Any],
        evidence_chunk_id: str,
        doc_id: str,
        section_path: str = None,
        sentence_ids: List[str] = None
    ):
        """
        存储节点并添加证据回溯
        
        Args:
            node: 节点数据
            evidence_chunk_id: 证据 Chunk ID
            doc_id: 文档 ID
            section_path: 章节路径
            sentence_ids: 句子 ID 列表
        """
        logger.debug(f"存储节点（带证据）: {node['id']}")
        from infra.neo4j_client import neo4j_client
        labels = node.get("labels") or node.get("label") or "Concept"
        create_query = f"""
        MERGE (n:{labels} {{id: $id}})
        SET n += $props,
            n.created_at = coalesce(n.created_at, datetime()),
            n.updated_at = datetime()
        RETURN n
        """
        neo4j_client.execute_query(create_query, {"id": node.get("id"), "props": node})

        ev_query = """
        MATCH (n {id: $nid})
        MATCH (chunk:Chunk {id: $chunk_id})
        MERGE (n)-[e:EVIDENCE_FROM]->(chunk)
        SET e.doc_id = $doc_id,
            e.section_path = $section_path,
            e.sentence_ids = $sentence_ids,
            e.created_at = coalesce(e.created_at, datetime()),
            e.updated_at = datetime()
        RETURN e
        """
        neo4j_client.execute_query(ev_query, {
            "nid": node.get("id"),
            "chunk_id": evidence_chunk_id,
            "doc_id": doc_id,
            "section_path": section_path,
            "sentence_ids": sentence_ids or [],
        })


__all__ = ["GraphService"]

