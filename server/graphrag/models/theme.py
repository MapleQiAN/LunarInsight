"""
Theme 数据模型

主题社区与摘要
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Theme(BaseModel):
    """
    主题模型
    
    用于阶段 4: 主题社区
    """
    
    id: str = Field(..., description="主题唯一标识")
    label: str = Field(..., description="主题标签（2-5 个词）", min_length=2, max_length=50)
    summary: str = Field(..., description="主题摘要（3-5 句话）", min_length=50, max_length=500)
    
    # 层级
    level: int = Field(..., description="层级: 1-粗粒度, 2-细粒度", ge=1, le=2)
    
    # 关键词
    keywords: List[str] = Field(default_factory=list, description="关键词列表（5-10 个）")
    
    # 社区信息
    community_id: Optional[str] = Field(None, description="GDS 社区 ID")
    member_count: int = Field(0, description="成员数量", ge=0)
    
    # 成员列表（概念 ID）
    concept_ids: List[str] = Field(default_factory=list, description="概念 ID 列表")
    claim_ids: List[str] = Field(default_factory=list, description="论断 ID 列表")
    
    # 关键证据
    key_evidence: Optional[List[dict]] = Field(
        None, 
        description="关键证据列表 [{claim_text, importance}]"
    )
    
    # 父主题（粗粒度主题的 ID，仅对细粒度主题有效）
    parent_theme_id: Optional[str] = Field(None, description="父主题 ID")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 构建版本
    build_version: Optional[str] = Field(None, description="构建版本标签")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "theme_001",
                "label": "Transformer 架构与注意力机制",
                "summary": "Transformer 是一种基于自注意力机制的神经网络架构...",
                "level": 1,
                "keywords": [
                    "Transformer",
                    "Self-Attention",
                    "Multi-Head Attention",
                    "Position Encoding",
                    "并行处理",
                    "序列建模"
                ],
                "community_id": "community_0",
                "member_count": 15,
                "concept_ids": ["concept_001", "concept_002", "concept_003"],
                "claim_ids": ["claim_001", "claim_002"],
                "key_evidence": [
                    {
                        "claim_text": "Transformer 采用自注意力机制替代循环结构",
                        "importance": 1.0
                    }
                ],
                "build_version": "doc123_1699401234"
            }
        }


class ThemeGraph(BaseModel):
    """
    主题图谱（用于可视化）
    """
    
    themes: List[Theme] = Field(default_factory=list, description="主题列表")
    
    # 主题间关系（如果有）
    theme_relations: Optional[List[dict]] = Field(
        None,
        description="主题关系列表 [{source, target, weight}]"
    )


__all__ = ["Theme", "ThemeGraph"]

