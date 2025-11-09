"""
阶段 2: 实体链接 (Entity Linking)

使用 Neo4j GraphRAG 进行实体抽取与链接
"""

import logging
from typing import List, Dict, Any
from server.graphrag.models.chunk import ChunkMetadata

logger = logging.getLogger("graphrag.stage2")


class EntityLinker:
    """
    实体链接器
    
    基于 Neo4j GraphRAG 的 KG Builder 实现
    """
    
    def __init__(self):
        logger.info("EntityLinker initialized")
        # TODO: 初始化 Neo4j GraphRAG KG Builder
    
    def link_and_extract(self, chunk: ChunkMetadata) -> List[Dict[str, Any]]:
        """
        链接并抽取实体
        
        Args:
            chunk: 输入 Chunk
        
        Returns:
            实体列表 [{concept_id, concept_name, confidence, mention_text}]
        """
        logger.debug(f"开始实体链接: chunk_id={chunk.id}")
        
        # TODO: 调用 Neo4j GraphRAG
        # 1. 候选生成（BM25 + Vector）
        # 2. LLM 精排
        # 3. 返回链接结果
        
        # 占位符
        entities = []
        
        logger.info(f"实体链接完成: chunk_id={chunk.id}, entities={len(entities)}")
        return entities


__all__ = ["EntityLinker"]

