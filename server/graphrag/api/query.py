"""
GraphRAG 查询 API

提供 GraphRAG 检索接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any, Optional
import logging

from server.graphrag.stages.stage7_query_service import QueryService

logger = logging.getLogger("graphrag.api.query")

router = APIRouter(prefix="/graphrag", tags=["GraphRAG"])


# 请求模型
class GraphRAGQueryRequest(BaseModel):
    """GraphRAG 查询请求"""
    
    question: str = Field(..., description="用户问题", min_length=5)
    mode: Literal["local", "global", "hybrid"] = Field(
        "hybrid",
        description="查询模式: local/global/hybrid"
    )
    top_k: int = Field(5, description="Top-K 结果数", ge=1, le=20)
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "什么是 Transformer？",
                "mode": "hybrid",
                "top_k": 5
            }
        }


# 响应模型
class GraphRAGQueryResponse(BaseModel):
    """GraphRAG 查询响应"""
    
    answer: Dict[str, Any] = Field(..., description="结构化答案")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="引用的证据 ID")
    relevant_themes: List[str] = Field(default_factory=list, description="相关主题")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": {
                    "conclusion": "Transformer 是一种基于自注意力机制的神经网络架构...",
                    "reasoning_chain": [
                        {
                            "step": 1,
                            "statement": "Transformer 的核心创新是自注意力机制",
                            "evidence_ids": [1]
                        }
                    ],
                    "confidence": 0.95,
                    "caveats": None
                },
                "cited_evidence_ids": ["chunk_001", "chunk_002"],
                "relevant_themes": ["Transformer 架构与注意力机制"]
            }
        }


# 端点
@router.post("/query", response_model=GraphRAGQueryResponse)
async def graphrag_query(request: GraphRAGQueryRequest):
    """
    GraphRAG 查询接口
    
    支持三种查询模式：
    - local: 局部图遍历
    - global: 全局社区聚合
    - hybrid: 混合模式（推荐）
    """
    try:
        logger.info(f"收到 GraphRAG 查询: question={request.question}, mode={request.mode}")
        
        # 调用查询服务
        query_service = QueryService()
        result = query_service.answer(
            question=request.question,
            mode=request.mode,
            top_k=request.top_k
        )
        
        return GraphRAGQueryResponse(**result)
    
    except Exception as e:
        logger.error(f"GraphRAG 查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/themes")
async def list_themes(doc_id: Optional[str] = None):
    """
    列出所有主题
    
    Args:
        doc_id: 可选，过滤特定文档的主题
    """
    try:
        # TODO: 查询 Neo4j，返回 Theme 列表
        return {"themes": []}
    
    except Exception as e:
        logger.error(f"查询主题失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/theme/{theme_id}")
async def get_theme_detail(theme_id: str):
    """
    获取主题详情
    
    Args:
        theme_id: 主题 ID
    """
    try:
        # TODO: 查询 Neo4j，返回主题详细信息
        return {"theme_id": theme_id}
    
    except Exception as e:
        logger.error(f"查询主题详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


__all__ = ["router"]

