"""
阶段 3: 论断抽取 (Claim Extraction)

从 Chunk 中抽取作者的论断与观点，并识别论断间关系
"""

import logging
from typing import List, Tuple
from server.graphrag.models.chunk import ChunkMetadata
from server.graphrag.models.claim import Claim, ClaimRelation

logger = logging.getLogger("graphrag.stage3")


class ClaimExtractor:
    """
    论断抽取器
    
    使用 LLM 提取论断与关系
    """
    
    def __init__(self):
        logger.info("ClaimExtractor initialized")
        # TODO: 加载 Prompt 模板
    
    def extract(self, chunk: ChunkMetadata) -> Tuple[List[Claim], List[ClaimRelation]]:
        """
        从 Chunk 中抽取论断与关系
        
        Args:
            chunk: 输入 Chunk
        
        Returns:
            (claims, relations)
        """
        logger.debug(f"开始论断抽取: chunk_id={chunk.id}")
        
        # TODO: 调用 LLM
        # 1. 构造 Prompt（使用 prompts/claim_extraction.txt）
        # 2. 调用 LLM
        # 3. 解析 JSON 响应
        # 4. 构造 Claim 和 ClaimRelation 对象
        
        # 占位符
        claims = []
        relations = []
        
        logger.info(f"论断抽取完成: chunk_id={chunk.id}, claims={len(claims)}, relations={len(relations)}")
        return claims, relations


__all__ = ["ClaimExtractor"]

