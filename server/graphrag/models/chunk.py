"""
Chunk 数据模型

语义块及其元数据
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChunkMetadata(BaseModel):
    """
    语义块元数据
    
    用于阶段 0: 篇章切分
    """
    
    id: str = Field(..., description="Chunk 唯一标识（doc_id:chunk_index）")
    doc_id: str = Field(..., description="所属文档 ID")
    
    # 内容
    text: str = Field(..., description="Chunk 文本内容", min_length=50)
    resolved_text: Optional[str] = Field(None, description="指代消解后的文本")
    
    # 位置信息
    chunk_index: int = Field(..., description="在文档中的序号（从 0 开始）", ge=0)
    section_path: Optional[str] = Field(None, description="章节路径（如 '1.2.3'）")
    page_num: Optional[int] = Field(None, description="起始页码", ge=1)
    
    # 句子信息
    sentence_ids: List[str] = Field(default_factory=list, description="句子 ID 列表")
    sentence_count: int = Field(0, description="句子数量", ge=0)
    
    # 滑动窗口信息
    window_start: int = Field(..., description="窗口起始句子索引（文档级）", ge=0)
    window_end: int = Field(..., description="窗口结束句子索引（文档级）", ge=0)
    
    # 向量化
    embedding: Optional[List[float]] = Field(None, description="向量表示（1536 维）")
    
    # 指代消解
    coreference_aliases: Optional[dict] = Field(
        None, 
        description="指代消解产生的别名映射 {代词: 实体名}"
    )
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 构建版本
    build_version: Optional[str] = Field(None, description="构建版本标签")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc123:0",
                "doc_id": "doc123",
                "text": "Transformer 是一种基于自注意力机制的神经网络架构...",
                "resolved_text": "Transformer 是一种基于自注意力机制的神经网络架构。Transformer 摒弃了传统的循环结构...",
                "chunk_index": 0,
                "section_path": "1.1",
                "page_num": 2,
                "sentence_ids": ["doc123:s0", "doc123:s1", "doc123:s2", "doc123:s3"],
                "sentence_count": 4,
                "window_start": 0,
                "window_end": 3,
                "coreference_aliases": {"它": "Transformer"},
                "build_version": "doc123_1699401234"
            }
        }


class ChunkWithRelations(ChunkMetadata):
    """
    带关系的 Chunk（用于图谱查询返回）
    """
    
    concepts: List[str] = Field(default_factory=list, description="提及的概念列表")
    claims: List[str] = Field(default_factory=list, description="包含的论断列表")
    themes: List[str] = Field(default_factory=list, description="归属的主题列表")


__all__ = ["ChunkMetadata", "ChunkWithRelations"]

