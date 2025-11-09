"""
Claim 数据模型

论断、观点、命题
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class Claim(BaseModel):
    """
    论断模型
    
    用于阶段 3: 论断抽取
    """
    
    id: str = Field(..., description="Claim 唯一标识")
    text: str = Field(..., description="论断文本", min_length=20, max_length=500)
    
    # 来源
    doc_id: str = Field(..., description="所属文档 ID")
    chunk_id: str = Field(..., description="所属 Chunk ID")
    sentence_ids: Optional[List[str]] = Field(None, description="句子 ID 列表")
    
    # 证据定位
    evidence_span: Optional[tuple[int, int]] = Field(
        None, 
        description="证据区间（字符偏移量）[start, end]"
    )
    section_path: Optional[str] = Field(None, description="章节路径")
    
    # 类型与置信度
    claim_type: Literal["fact", "hypothesis", "conclusion"] = Field(
        ..., 
        description="论断类型"
    )
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    
    # 向量化
    embedding: Optional[List[float]] = Field(None, description="向量表示")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 构建版本
    build_version: Optional[str] = Field(None, description="构建版本标签")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "claim_001",
                "text": "Transformer 采用自注意力机制替代循环结构",
                "doc_id": "doc123",
                "chunk_id": "doc123:0",
                "sentence_ids": ["doc123:s1"],
                "evidence_span": [0, 25],
                "section_path": "1.1",
                "claim_type": "fact",
                "confidence": 0.95,
                "build_version": "doc123_1699401234"
            }
        }


class ClaimRelation(BaseModel):
    """
    论断关系模型
    
    表示论断之间的逻辑关系
    """
    
    id: str = Field(..., description="关系唯一标识")
    
    # 关系端点
    source_claim_id: str = Field(..., description="源论断 ID")
    target_claim_id: str = Field(..., description="目标论断 ID")
    
    # 关系类型
    relation_type: Literal[
        "SUPPORTS",      # 支持
        "CONTRADICTS",   # 反驳
        "CAUSES",        # 因果
        "COMPARES_WITH", # 对比
        "CONDITIONS",    # 条件
        "PURPOSE"        # 目的
    ] = Field(..., description="关系类型")
    
    # 置信度与强度
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    strength: Optional[float] = Field(None, description="关系强度", ge=0.0, le=1.0)
    
    # 证据
    evidence: Optional[str] = Field(None, description="支撑此关系的原文片段")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 构建版本
    build_version: Optional[str] = Field(None, description="构建版本标签")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "rel_001",
                "source_claim_id": "claim_001",
                "target_claim_id": "claim_002",
                "relation_type": "SUPPORTS",
                "confidence": 0.85,
                "strength": 0.9,
                "evidence": "基于自注意力机制，因此能够并行处理",
                "build_version": "doc123_1699401234"
            }
        }


__all__ = ["Claim", "ClaimRelation"]

