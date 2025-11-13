"""
阶段 4: 主题社区 (Theme Builder)

使用 Louvain 算法构建主题社区，并生成主题摘要
"""

import logging
from typing import List, Dict, Any
from graphrag.models.theme import Theme
from graphrag.config import get_config
from infra.neo4j_client import neo4j_client
from graphrag.utils.embedding import get_embedding

logger = logging.getLogger("graphrag.stage4")


class ThemeBuilder:
    """
    主题构建器
    
    使用 Neo4j GDS Louvain 算法发现社区，并用 LLM 生成摘要
    """
    
    def __init__(self):
        logger.info("ThemeBuilder initialized")
        self.config = get_config()
    
    def build(self, doc_id: str, build_version: str) -> List[Theme]:
        """
        为文档构建主题社区
        
        Args:
            doc_id: 文档 ID
            build_version: 构建版本标签
        
        Returns:
            主题列表
        """
        logger.info(f"开始构建主题: doc_id={doc_id}")

        resolution = float(self.config.thresholds.theme_building.get("louvain", {}).get("resolution", 1.0))
        max_iterations = int(self.config.thresholds.theme_building.get("louvain", {}).get("max_iterations", 100))
        tolerance = float(self.config.thresholds.theme_building.get("louvain", {}).get("tolerance", 0.0001))
        min_size = int(self.config.thresholds.theme_building.get("min_community_size", 3))

        graph_name = f"doc_theme_{doc_id}"

        project_query_nodes = """
        CALL gds.graph.project.cypher(
          $graphName,
          'MATCH (c:Concept)<-[:MENTIONS]-(ch:Chunk {doc_id: $docId}) RETURN id(c) AS id UNION MATCH (cl:Claim {doc_id: $docId}) RETURN id(cl) AS id',
          'MATCH (c1:Concept)<-[:MENTIONS]-(ch:Chunk {doc_id: $docId})-[:MENTIONS]->(c2:Concept) WHERE id(c1) < id(c2) RETURN id(c1) AS source, id(c2) AS target, count(*) AS weight UNION MATCH (cl1:Claim {doc_id: $docId})-[r:SUPPORTS|CAUSES|CONTRADICTS]->(cl2:Claim) RETURN id(cl1) AS source, id(cl2) AS target, CASE type(r) WHEN "SUPPORTS" THEN 1.0 WHEN "CAUSES" THEN 0.8 WHEN "CONTRADICTS" THEN 0.6 ELSE 0.5 END AS weight UNION MATCH (cl:Claim {doc_id: $docId})<-[:CONTAINS_CLAIM]-(ch:Chunk {doc_id: $docId})-[:MENTIONS]->(c:Concept) RETURN id(cl) AS source, id(c) AS target, 0.7 AS weight',
          {relationshipProperties: 'weight'}
        ) YIELD graphName
        RETURN graphName
        """

        try:
            neo4j_client.execute_query(project_query_nodes, {"graphName": graph_name, "docId": doc_id})
        except Exception:
            try:
                neo4j_client.execute_query("CALL gds.graph.drop($graphName, false) YIELD graphName RETURN graphName", {"graphName": graph_name})
            except Exception:
                pass
            neo4j_client.execute_query(project_query_nodes, {"graphName": graph_name, "docId": doc_id})

        louvain_query = """
        CALL gds.louvain.stream($graphName, {relationshipWeightProperty: 'weight', maxIterations: $maxIterations, tolerance: $tolerance, resolution: $resolution})
        YIELD nodeId, communityId
        RETURN nodeId, communityId
        """

        pr_query = """
        CALL gds.pageRank.stream($graphName, {relationshipWeightProperty: 'weight'})
        YIELD nodeId, score
        RETURN nodeId, score
        """

        communities = neo4j_client.execute_query(louvain_query, {"graphName": graph_name, "maxIterations": max_iterations, "tolerance": tolerance, "resolution": resolution})
        pr_scores = neo4j_client.execute_query(pr_query, {"graphName": graph_name})

        node_fetch_query = """
        UNWIND $nodeIds AS nid
        MATCH (n) WHERE id(n) = nid
        RETURN id(n) AS nodeId, labels(n) AS labels, n AS node
        """

        node_ids = [rec["nodeId"] for rec in communities]
        node_info = {}
        if node_ids:
            for batch_start in range(0, len(node_ids), 100):
                batch = node_ids[batch_start: batch_start + 100]
                records = neo4j_client.execute_query(node_fetch_query, {"nodeIds": batch})
                for r in records:
                    node_info[r["nodeId"]] = {"labels": r.get("labels", []), "node": r.get("node", {})}

        pr_map: Dict[int, float] = {r["nodeId"]: float(r.get("score", 0.0)) for r in pr_scores}

        comm_members: Dict[int, List[int]] = {}
        for rec in communities:
            cid = rec["communityId"]
            nid = rec["nodeId"]
            comm_members.setdefault(cid, []).append(nid)

        themes: List[Theme] = []
        for cid, members in comm_members.items():
            if len(members) < min_size:
                continue

            concepts: List[str] = []
            claims: List[str] = []
            for nid in members:
                info = node_info.get(nid, {})
                labels = info.get("labels", [])
                node = info.get("node", {})
                if "Concept" in labels:
                    name = node.get("name", None)
                    if name:
                        concepts.append(name)
                elif "Claim" in labels:
                    clid = node.get("id", None)
                    if clid:
                        claims.append(clid)

            member_count = len(concepts) + len(claims)
            level = 1 if member_count > 20 else 2

            ranked_members = sorted(members, key=lambda nid: pr_map.get(nid, 0.0), reverse=True)
            top_concepts = []
            top_claim_texts = []
            for nid in ranked_members:
                info = node_info.get(nid, {})
                labels = info.get("labels", [])
                node = info.get("node", {})
                if "Concept" in labels and len(top_concepts) < 5:
                    if node.get("name"):
                        top_concepts.append(node["name"])
                if "Claim" in labels and len(top_claim_texts) < 3:
                    if node.get("text"):
                        top_claim_texts.append(node["text"])

            keywords = top_concepts
            summary_text = "；".join(top_claim_texts)[:100]
            if len(summary_text) < 50:
                summary_text = "，".join(keywords)[:100] if keywords else "该主题包含多个相关概念与论断"

            theme_id = f"theme_{doc_id}_{cid}"
            theme = Theme(
                id=theme_id,
                label=(" ").join(keywords[:3]) if keywords else f"主题{cid}",
                summary=summary_text,
                level=level,
                keywords=keywords,
                community_id=str(cid),
                member_count=member_count,
                concept_ids=concepts,
                claim_ids=claims,
                key_evidence=[{"claim_text": t, "importance": 1.0} for t in top_claim_texts],
                build_version=build_version,
            )
            themes.append(theme)

        store_query_theme = """
        MERGE (t:Theme {id: $id})
        SET t.label = $label,
            t.summary = $summary,
            t.level = $level,
            t.keywords = $keywords,
            t.community_id = $community_id,
            t.member_count = $member_count,
            t.build_version = $build_version,
            t.created_at = coalesce(t.created_at, datetime()),
            t.updated_at = datetime()
        RETURN t
        """

        link_concept_query = """
        MATCH (c:Concept {name: $name}), (t:Theme {id: $tid})
        MERGE (c)-[:BELONGS_TO_THEME]->(t)
        MERGE (t)-[:HAS_MEMBER]->(c)
        RETURN t
        """

        link_claim_query = """
        MATCH (cl:Claim {id: $cid}), (t:Theme {id: $tid})
        MERGE (cl)-[:BELONGS_TO_THEME]->(t)
        MERGE (t)-[:HAS_MEMBER]->(cl)
        RETURN t
        """

        for theme in themes:
            neo4j_client.execute_query(store_query_theme, {
                "id": theme.id,
                "label": theme.label,
                "summary": theme.summary,
                "level": theme.level,
                "keywords": theme.keywords,
                "community_id": theme.community_id,
                "member_count": theme.member_count,
                "build_version": theme.build_version,
            })

            for name in theme.concept_ids:
                neo4j_client.execute_query(link_concept_query, {"name": name, "tid": theme.id})
            for cid in theme.claim_ids:
                neo4j_client.execute_query(link_claim_query, {"cid": cid, "tid": theme.id})

        try:
            neo4j_client.execute_query("CALL gds.graph.drop($graphName) YIELD graphName RETURN graphName", {"graphName": graph_name})
        except Exception:
            pass

        logger.info(f"主题构建完成: doc_id={doc_id}, themes={len(themes)}")
        return themes


__all__ = ["ThemeBuilder"]

