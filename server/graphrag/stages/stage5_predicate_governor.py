"""
阶段 5: 谓词治理 (Predicate Governor)

规范化谓词，映射自然语言关系到标准谓词集
"""

import logging
from typing import Dict, Any, Optional, List
from graphrag.config import get_config, ConstraintResult, GovernanceStatus

logger = logging.getLogger("graphrag.stage5")


class PredicateGovernor:
    """
    谓词治理器
    
    将自然语言谓词映射到标准谓词集，并验证类型约束
    """
    
    def __init__(self):
        self.config = get_config()
        logger.info("PredicateGovernor initialized")
    
    def normalize(self, predicate: str, source_type: str, target_type: str) -> Dict[str, Any]:
        """
        规范化谓词并返回治理结果
        
        Args:
            predicate: 原始谓词
            source_type: 源节点类型
            target_type: 目标节点类型
        
        Returns:
            包含治理结果的字典：
            {
                'original_predicate': str,      # 原始谓词
                'normalized_predicate': str,    # 标准谓词
                'confidence': float,            # 置信度
                'constraint_result': ConstraintResult,  # 约束检查结果
                'governance_status': GovernanceStatus,   # 治理状态
                'predicate_version': str,       # 谓词配置版本
                'ontology_version': str         # 本体配置版本
            }
        """
        logger.debug(f"规范化谓词: {predicate}")
        
        # 初始化结果
        result = {
            'original_predicate': predicate,
            'normalized_predicate': f"OTHER({predicate})",
            'confidence': 0.0,
            'constraint_result': ConstraintResult.HARD_VIOLATION,
            'governance_status': GovernanceStatus.REJECTED,
            'predicate_version': self.config.predicates.version,
            'ontology_version': self.config.ontology.version
        }
        
        # 1. 检查是否为标准谓词
        if self.config.predicates.is_standard_predicate(predicate):
            # 验证类型约束
            constraint_result = self.config.predicates.validate_type_constraint(
                source_type, predicate, target_type
            )
            
            if constraint_result == ConstraintResult.PASS:
                result.update({
                    'normalized_predicate': predicate,
                    'confidence': 1.0,
                    'constraint_result': constraint_result,
                    'governance_status': GovernanceStatus.ACCEPTED
                })
                logger.debug(f"标准谓词通过验证: {predicate}")
                return result
            elif constraint_result == ConstraintResult.SOFT_VIOLATION:
                result.update({
                    'normalized_predicate': predicate,
                    'confidence': 0.7,
                    'constraint_result': constraint_result,
                    'governance_status': GovernanceStatus.ACCEPTED  # 软违规仍然接受
                })
                logger.warning(f"标准谓词软违规: {source_type} -{predicate}-> {target_type}")
                return result
            else:
                result.update({
                    'constraint_result': constraint_result,
                    'governance_status': GovernanceStatus.PENDING  # 硬违规进入待复核
                })
                logger.warning(f"标准谓词硬违规: {source_type} -{predicate}-> {target_type}")
                return result
        
        # 2. 尝试映射自然语言谓词
        normalized = self.config.predicates.normalize_predicate(predicate)
        if normalized:
            # 验证类型约束
            constraint_result = self.config.predicates.validate_type_constraint(
                source_type, normalized, target_type
            )
            
            if constraint_result == ConstraintResult.PASS:
                result.update({
                    'normalized_predicate': normalized,
                    'confidence': 0.9,  # 映射的谓词置信度稍低
                    'constraint_result': constraint_result,
                    'governance_status': GovernanceStatus.ACCEPTED
                })
                logger.debug(f"谓词映射成功: {predicate} -> {normalized}")
                return result
            elif constraint_result == ConstraintResult.SOFT_VIOLATION:
                result.update({
                    'normalized_predicate': normalized,
                    'confidence': 0.6,
                    'constraint_result': constraint_result,
                    'governance_status': GovernanceStatus.ACCEPTED
                })
                logger.warning(f"映射谓词软违规: {source_type} -{normalized}-> {target_type}")
                return result
            else:
                result.update({
                    'constraint_result': constraint_result,
                    'governance_status': GovernanceStatus.PENDING
                })
                logger.warning(f"映射谓词硬违规: {source_type} -{normalized}-> {target_type}")
                return result
        
        # 3. 未匹配谓词
        result.update({
            'confidence': 0.1,
            'governance_status': GovernanceStatus.PENDING
        })
        logger.warning(f"未匹配谓词: {predicate}, 标记为待复核")
        return result
    
    def normalize_all(self, doc_id: str):
        """
        批量规范化文档的所有关系谓词，并写入治理元数据
        
        Args:
            doc_id: 文档 ID
        """
        logger.info(f"开始批量规范化: doc_id={doc_id}")
        
        from server.infra.neo4j_client import neo4j_client
        
        # 查询文档相关的所有关系（只处理尚未治理的）
        query = """
        MATCH (d:Document {id: $doc_id})-[*1..3]-(n1)-[r]->(n2)
        WHERE type(r) <> 'CONTAINS' AND type(r) <> 'MENTIONS' 
              AND type(r) <> 'CONTAINS_CLAIM' AND type(r) <> 'EVIDENCE_FROM'
              AND (r.governance_status IS NULL OR r.governance_version <> $predicate_version)
        RETURN DISTINCT type(r) AS rel_type, 
               labels(n1)[0] AS source_type,
               labels(n2)[0] AS target_type,
               id(r) AS rel_id,
               properties(r) AS props
        """
        
        result = neo4j_client.execute_query(query, {
            "doc_id": doc_id, 
            "predicate_version": self.config.predicates.version
        })
        
        # 统计结果
        stats = {
            'accepted': 0,
            'pending': 0,
            'rejected': 0,
            'soft_violations': 0
        }
        
        for record in result:
            rel_type = record.get("rel_type")
            source_type = record.get("source_type", "Concept")
            target_type = record.get("target_type", "Concept")
            rel_id = record.get("rel_id")
            props = record.get("props", {})
            
            # 规范化谓词并获取治理结果
            governance_result = self.normalize(rel_type, source_type, target_type)
            
            # 更新统计
            status = governance_result['governance_status']
            if status == GovernanceStatus.ACCEPTED:
                stats['accepted'] += 1
            elif status == GovernanceStatus.PENDING:
                stats['pending'] += 1
            else:
                stats['rejected'] += 1
                
            if governance_result['constraint_result'] == ConstraintResult.SOFT_VIOLATION:
                stats['soft_violations'] += 1
            
            # 准备治理元数据
            governance_metadata = {
                'original_predicate': governance_result['original_predicate'],
                'confidence': governance_result['confidence'],
                'constraint_result': governance_result['constraint_result'].value,
                'governance_status': governance_result['governance_status'].value,
                'predicate_version': governance_result['predicate_version'],
                'ontology_version': governance_result['ontology_version'],
                'governed_at': None  # TODO: 添加时间戳
            }
            
            # 如果谓词需要更新，更新关系类型和治理元数据
            if governance_result['normalized_predicate'] != rel_type:
                update_query = f"""
                MATCH ()-[r]->()
                WHERE id(r) = $rel_id
                WITH r, startNode(r) AS source, endNode(r) AS target, properties(r) AS props
                DELETE r
                CREATE (source)-[r2:{governance_result['normalized_predicate']}]->(target)
                SET r2 = props, r2 += $metadata
                """
            else:
                # 只更新治理元数据
                update_query = """
                MATCH ()-[r]->()
                WHERE id(r) = $rel_id
                SET r += $metadata
                """
            
            try:
                neo4j_client.execute_query(update_query, {
                    "rel_id": rel_id,
                    "metadata": governance_metadata
                })
                
                if governance_result['governance_status'] == GovernanceStatus.ACCEPTED:
                    logger.debug(f"关系已接受: {rel_type} -> {governance_result['normalized_predicate']}")
                elif governance_result['governance_status'] == GovernanceStatus.PENDING:
                    logger.warning(f"关系待复核: {rel_type} -> {governance_result['normalized_predicate']}")
                else:
                    logger.error(f"关系被拒绝: {rel_type} -> {governance_result['normalized_predicate']}")
                    
            except Exception as e:
                logger.error(f"更新关系失败: {e}")
        
        logger.info(f"批量规范化完成: doc_id={doc_id}, accepted={stats['accepted']}, "
                   f"pending={stats['pending']}, rejected={stats['rejected']}, "
                   f"soft_violations={stats['soft_violations']}")
        
        return stats
    
    def get_governance_stats(self, doc_id: str = None) -> Dict[str, Any]:
        """
        获取治理统计信息
        
        Args:
            doc_id: 可选，指定文档ID获取该文档的统计
            
        Returns:
            统计信息字典
        """
        from server.infra.neo4j_client import neo4j_client
        
        if doc_id:
            # 获取特定文档的统计
            query = """
            MATCH (d:Document {id: $doc_id})-[*1..3]-(n1)-[r]->(n2)
            WHERE r.governance_status IS NOT NULL
            RETURN r.governance_status AS status,
                   r.constraint_result AS constraint,
                   COUNT(*) AS count
            """
            params = {"doc_id": doc_id}
        else:
            # 获取全局统计
            query = """
            MATCH ()-[r]->()
            WHERE r.governance_status IS NOT NULL
            RETURN r.governance_status AS status,
                   r.constraint_result AS constraint,
                   COUNT(*) AS count
            """
            params = {}
        
        result = neo4j_client.execute_query(query, params)
        
        stats = {
            'total': 0,
            'accepted': 0,
            'pending': 0,
            'rejected': 0,
            'soft_violations': 0,
            'hard_violations': 0,
            'by_status': {},
            'by_constraint': {}
        }
        
        for record in result:
            status = record.get("status", "unknown")
            constraint = record.get("constraint", "unknown")
            count = record.get("count", 0)
            
            stats['total'] += count
            
            # 按状态统计
            if status not in stats['by_status']:
                stats['by_status'][status] = 0
            stats['by_status'][status] += count
            
            # 按约束结果统计
            if constraint not in stats['by_constraint']:
                stats['by_constraint'][constraint] = 0
            stats['by_constraint'][constraint] += count
            
            # 累计主要指标
            if status == 'accepted':
                stats['accepted'] += count
            elif status == 'pending':
                stats['pending'] += count
            elif status == 'rejected':
                stats['rejected'] += count
                
            if constraint == 'soft':
                stats['soft_violations'] += count
            elif constraint == 'hard':
                stats['hard_violations'] += count
        
        return stats
    
    def get_pending_relations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取待复核的关系列表
        
        Args:
            limit: 返回数量限制
            
        Returns:
            待复核关系列表
        """
        from infra.neo4j_client import neo4j_client
        
        query = """
        MATCH ()-[r]->()
        WHERE r.governance_status = 'pending'
        RETURN r.original_predicate AS original,
               r.normalized_predicate AS normalized,
               r.confidence AS confidence,
               r.constraint_result AS constraint,
               startNode(r).name AS source_name,
               labels(startNode(r))[0] AS source_type,
               endNode(r).name AS target_name,
               labels(endNode(r))[0] AS target_type
        LIMIT $limit
        """
        
        result = neo4j_client.execute_query(query, {"limit": limit})
        
        return [dict(record) for record in result]


__all__ = ["PredicateGovernor"]

