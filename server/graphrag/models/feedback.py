"""
Feedback 数据模型

人工反馈与修正请求
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class MergeRequest(BaseModel):
    """
    实体合并请求
    
    当用户发现两个概念其实是同一个实体时发起
    """
    
    id: str = Field(..., description="请求唯一标识")
    
    # 待合并的概念
    source_concept_id: str = Field(..., description="源概念 ID（将被合并）")
    target_concept_id: str = Field(..., description="目标概念 ID（保留）")
    
    # 合并理由
    reason: str = Field(..., description="合并理由", min_length=10)
    
    # 提交者
    submitted_by: Optional[str] = Field(None, description="提交者 ID")
    
    # 状态
    status: Literal["pending", "approved", "rejected"] = Field(
        "pending", 
        description="审核状态"
    )
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    
    # 审核意见
    review_comment: Optional[str] = Field(None, description="审核意见")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "merge_001",
                "source_concept_id": "concept_002",
                "target_concept_id": "concept_001",
                "reason": "BERT 和 Bidirectional Encoder Representations from Transformers 是同一个概念",
                "submitted_by": "user_001",
                "status": "pending"
            }
        }


class CorrectionRequest(BaseModel):
    """
    数据修正请求
    
    当用户发现概念描述、关系类型等错误时发起
    """
    
    id: str = Field(..., description="请求唯一标识")
    
    # 待修正的对象
    object_type: Literal["concept", "relation", "claim"] = Field(
        ..., 
        description="对象类型"
    )
    object_id: str = Field(..., description="对象 ID")
    
    # 修正内容
    field: str = Field(..., description="待修正的字段（如 'description', 'relation_type'）")
    old_value: str = Field(..., description="旧值")
    new_value: str = Field(..., description="新值")
    
    # 修正理由
    reason: str = Field(..., description="修正理由", min_length=10)
    
    # 提交者
    submitted_by: Optional[str] = Field(None, description="提交者 ID")
    
    # 状态
    status: Literal["pending", "approved", "rejected"] = Field(
        "pending", 
        description="审核状态"
    )
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    
    # 审核意见
    review_comment: Optional[str] = Field(None, description="审核意见")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "correction_001",
                "object_type": "relation",
                "object_id": "rel_001",
                "field": "relation_type",
                "old_value": "USES",
                "new_value": "DERIVES_FROM",
                "reason": "Transformer 不是使用 Attention，而是基于 Attention 派生出的新架构",
                "submitted_by": "user_001",
                "status": "pending"
            }
        }


class UnlinkRequest(BaseModel):
    """
    实体解链请求
    
    当用户发现提及被错误链接到概念时发起
    """
    
    id: str = Field(..., description="请求唯一标识")
    
    # 错误链接
    mention_text: str = Field(..., description="提及文本")
    chunk_id: str = Field(..., description="所属 Chunk ID")
    linked_concept_id: str = Field(..., description="错误链接的概念 ID")
    
    # 正确链接（可选）
    correct_concept_id: Optional[str] = Field(None, description="正确的概念 ID（如果有）")
    
    # 理由
    reason: str = Field(..., description="解链理由", min_length=10)
    
    # 提交者
    submitted_by: Optional[str] = Field(None, description="提交者 ID")
    
    # 状态
    status: Literal["pending", "approved", "rejected"] = Field(
        "pending", 
        description="审核状态"
    )
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    
    # 审核意见
    review_comment: Optional[str] = Field(None, description="审核意见")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "unlink_001",
                "mention_text": "attention",
                "chunk_id": "doc123:5",
                "linked_concept_id": "concept_003",
                "correct_concept_id": None,
                "reason": "这里的 attention 是日常用语（pay attention），不是技术概念",
                "submitted_by": "user_001",
                "status": "pending"
            }
        }


class FeedbackLog(BaseModel):
    """
    反馈日志（用于统计与分析）
    """
    
    id: str = Field(..., description="日志 ID")
    
    # 反馈类型
    feedback_type: Literal["merge", "correction", "unlink", "other"] = Field(
        ..., 
        description="反馈类型"
    )
    
    # 引用的请求 ID
    request_id: str = Field(..., description="请求 ID")
    
    # 处理动作
    action: Literal["approved", "rejected", "auto_applied"] = Field(
        ..., 
        description="处理动作"
    )
    
    # 影响范围
    affected_nodes: int = Field(0, description="影响的节点数", ge=0)
    affected_relations: int = Field(0, description="影响的关系数", ge=0)
    
    # 时间戳
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 处理者
    processed_by: Optional[str] = Field(None, description="处理者 ID（可能是系统自动）")


__all__ = [
    "MergeRequest",
    "CorrectionRequest",
    "UnlinkRequest",
    "FeedbackLog"
]

