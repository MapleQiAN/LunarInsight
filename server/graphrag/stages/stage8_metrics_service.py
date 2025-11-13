"""
阶段 8: 评价与反馈 (Metrics Service)

计算评价指标，收集反馈，形成治理闭环
"""

import logging
from typing import Dict, Any, List
from graphrag.config import get_config

logger = logging.getLogger("graphrag.stage8")


class MetricsService:
    """
    评价指标服务
    
    计算量化指标，支持系统改进
    """
    
    def __init__(self):
        logger.info("MetricsService initialized")
        self.config = get_config()
    
    def compute_metrics(self, doc_id: str) -> Dict[str, Any]:
        """
        计算文档的评价指标
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            指标字典
        """
        logger.info(f"开始计算指标: doc_id={doc_id}")

        from infra.neo4j_client import neo4j_client

        isolated_query = """
        MATCH (cl:Claim {doc_id: $doc_id})
        OPTIONAL MATCH (cl)-[r]-()
        WITH cl, count(r) AS deg
        RETURN sum(CASE WHEN deg = 0 THEN 1 ELSE 0 END) * 1.0 / count(cl) AS ratio,
               avg(deg) AS avgdeg
        """
        iso_res = neo4j_client.execute_query(isolated_query, {"doc_id": doc_id})
        isolated_node_ratio = float(iso_res[0].get("ratio", 0.0)) if iso_res else 0.0
        avg_degree = float(iso_res[0].get("avgdeg", 0.0)) if iso_res else 0.0

        other_query = """
        MATCH (:Claim {doc_id: $doc_id})-[r]->(:Claim)
        WITH collect(r) AS rels
        RETURN size([x IN rels WHERE toString(x.normalized_predicate) STARTS WITH 'OTHER(']) * 1.0 / size(rels) AS ratio
        """
        other_res = neo4j_client.execute_query(other_query, {"doc_id": doc_id})
        other_ratio = float(other_res[0].get("ratio", 0.0)) if other_res else 0.0

        alias_query = """
        MATCH (c:Concept)<-[:MENTIONS]-(:Chunk {doc_id: $doc_id})
        RETURN reduce(s = 0, a IN coalesce(c.aliases, []) | s + 1) AS alias_count
        """
        alias_res = neo4j_client.execute_query(alias_query, {"doc_id": doc_id})
        alias_count = sum(int(r.get("alias_count", 0)) for r in alias_res) if alias_res else 0

        graph_name = f"metrics_claim_graph_{doc_id}"
        project_query = """
        CALL gds.graph.project.cypher(
          $graphName,
          'MATCH (cl:Claim {doc_id: $docId}) RETURN id(cl) AS id',
          'MATCH (cl1:Claim {doc_id: $docId})-[r:SUPPORTS|CAUSES|CONTRADICTS]->(cl2:Claim {doc_id: $docId}) RETURN id(cl1) AS source, id(cl2) AS target, 1.0 AS weight',
          {relationshipProperties: 'weight'}
        ) YIELD graphName
        RETURN graphName
        """
        try:
            neo4j_client.execute_query(project_query, {"graphName": graph_name, "docId": doc_id})
        except Exception:
            try:
                neo4j_client.execute_query("CALL gds.graph.drop($graphName, false) YIELD graphName RETURN graphName", {"graphName": graph_name})
            except Exception:
                pass
            neo4j_client.execute_query(project_query, {"graphName": graph_name, "docId": doc_id})

        stats_query = """
        CALL gds.louvain.stats($graphName, {relationshipWeightProperty: 'weight'})
        YIELD modularity
        RETURN modularity
        """
        stats_res = neo4j_client.execute_query(stats_query, {"graphName": graph_name})
        modularity = float(stats_res[0].get("modularity", 0.0)) if stats_res else 0.0
        try:
            neo4j_client.execute_query("CALL gds.graph.drop($graphName) YIELD graphName RETURN graphName", {"graphName": graph_name})
        except Exception:
            pass

        metrics = {
            "isolated_node_ratio": isolated_node_ratio,
            "avg_degree": avg_degree,
            "other_predicate_ratio": other_ratio,
            "alias_count": alias_count,
            "modularity": modularity
        }

        logger.info(f"指标计算完成: {metrics}")
        return metrics
    
    def check_alerts(self, metrics: Dict[str, Any]) -> List[str]:
        """
        检查告警
        
        Args:
            metrics: 指标字典
        
        Returns:
            告警列表
        """
        alerts = []
        threshold_isolated = float(self.config.thresholds.metrics.get("isolated_node_warning_ratio", 0.05))
        if metrics.get("isolated_node_ratio", 0.0) > threshold_isolated:
            alerts.append("孤立节点比例偏高")
        threshold_other = float(self.config.thresholds.predicate_governance.get("other_predicate_warning_ratio", 0.1))
        if metrics.get("other_predicate_ratio", 0.0) > threshold_other:
            alerts.append("OTHER 谓词占比告警")
        return alerts


__all__ = ["MetricsService"]

