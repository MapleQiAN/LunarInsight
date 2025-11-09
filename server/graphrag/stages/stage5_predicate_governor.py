"""
阶段 5: 谓词治理 (Predicate Governor)

规范化谓词，映射自然语言关系到标准谓词集
"""

import logging
from server.graphrag.config import get_config

logger = logging.getLogger("graphrag.stage5")


class PredicateGovernor:
    """
    谓词治理器
    
    将自然语言谓词映射到标准谓词集，并验证类型约束
    """
    
    def __init__(self):
        self.config = get_config()
        logger.info("PredicateGovernor initialized")
    
    def normalize(self, predicate: str, source_type: str, target_type: str) -> str:
        """
        规范化谓词
        
        Args:
            predicate: 原始谓词
            source_type: 源节点类型
            target_type: 目标节点类型
        
        Returns:
            标准谓词（如果无法映射则返回 "OTHER(原始谓词)"）
        """
        logger.debug(f"规范化谓词: {predicate}")
        
        # 1. 检查是否为标准谓词
        if self.config.predicates.is_standard_predicate(predicate):
            # 验证类型约束
            is_valid = self.config.predicates.validate_type_constraint(
                source_type, predicate, target_type
            )
            if is_valid:
                return predicate
            else:
                logger.warning(f"类型约束违反: {source_type} -{predicate}-> {target_type}")
                return f"OTHER({predicate})"
        
        # 2. 尝试映射
        normalized = self.config.predicates.normalize_predicate(predicate)
        if normalized:
            # 验证类型约束
            is_valid = self.config.predicates.validate_type_constraint(
                source_type, normalized, target_type
            )
            if is_valid:
                logger.debug(f"谓词映射成功: {predicate} -> {normalized}")
                return normalized
        
        # 3. 未匹配
        logger.warning(f"未匹配谓词: {predicate}, 打入 OTHER")
        return f"OTHER({predicate})"
    
    def normalize_all(self, doc_id: str):
        """
        批量规范化文档的所有关系谓词
        
        Args:
            doc_id: 文档 ID
        """
        logger.info(f"开始批量规范化: doc_id={doc_id}")
        
        # TODO: 查询 Neo4j，遍历所有关系，规范化谓词
        
        logger.info(f"批量规范化完成: doc_id={doc_id}")


__all__ = ["PredicateGovernor"]

