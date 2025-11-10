"""
阶段 0: 篇章切分 (Semantic Chunker)

将文档切分为语义块，为后续处理做准备
"""

import logging
from typing import List
from graphrag.models.chunk import ChunkMetadata
from graphrag.utils.text_processing import split_sentences, sliding_window
from graphrag.config import get_config

logger = logging.getLogger("graphrag.stage0")


class SemanticChunker:
    """
    语义块切分器
    
    使用滑动窗口算法将文档切分为重叠的语义块
    """
    
    def __init__(self):
        config = get_config()
        self.window_size = config.thresholds.get("chunking", "window_size", 4)
        self.step_size = config.thresholds.get("chunking", "step_size", 2)
        logger.info(f"SemanticChunker initialized: window_size={self.window_size}, step_size={self.step_size}")
    
    def split(self, doc_id: str, text: str, build_version: str) -> List[ChunkMetadata]:
        """
        切分文档为语义块
        
        Args:
            doc_id: 文档 ID
            text: 文档文本
            build_version: 构建版本标签
        
        Returns:
            Chunk 列表
        """
        logger.info(f"开始切分文档: doc_id={doc_id}, text_length={len(text)}")
        
        # 1. 句子分割
        sentences = split_sentences(text)
        logger.debug(f"句子分割完成: {len(sentences)} 个句子")
        
        # 2. 滑动窗口
        windows = sliding_window(sentences, self.window_size, self.step_size)
        logger.debug(f"滑动窗口完成: {len(windows)} 个窗口")
        
        # 3. 构建 Chunk 对象
        chunks = []
        chunk_index = 0
        for window_text, start_idx, end_idx in windows:
            # 过滤过短的窗口（ChunkMetadata 要求 text 至少 50 个字符）
            if len(window_text.strip()) < 50:
                logger.debug(f"跳过过短的窗口: length={len(window_text)}, text={window_text[:50]}...")
                continue
            
            # 生成句子 ID
            sentence_ids = [f"{doc_id}:s{j}" for j in range(start_idx, end_idx + 1)]
            
            chunk = ChunkMetadata(
                id=f"{doc_id}:{chunk_index}",
                doc_id=doc_id,
                text=window_text,
                chunk_index=chunk_index,
                sentence_ids=sentence_ids,
                sentence_count=len(sentence_ids),
                window_start=start_idx,
                window_end=end_idx,
                build_version=build_version
            )
            chunks.append(chunk)
            chunk_index += 1
        
        logger.info(f"切分完成: 生成 {len(chunks)} 个 Chunk")
        return chunks


__all__ = ["SemanticChunker"]

