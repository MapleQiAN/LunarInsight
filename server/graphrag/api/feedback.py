"""
反馈 API

处理人工反馈与修正请求
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from graphrag.models.feedback import (
    MergeRequest,
    CorrectionRequest,
    UnlinkRequest
)

logger = logging.getLogger("graphrag.api.feedback")

router = APIRouter(prefix="/graphrag/feedback", tags=["Feedback"])


# 端点
@router.post("/merge", response_model=MergeRequest)
async def submit_merge_request(request: MergeRequest):
    """
    提交实体合并请求
    
    当用户发现两个概念其实是同一个实体时调用
    """
    try:
        logger.info(f"收到合并请求: {request.source_concept_id} -> {request.target_concept_id}")
        
        # TODO: 
        # 1. 验证概念是否存在
        # 2. 存储到复核队列
        # 3. 返回请求 ID
        
        return request
    
    except Exception as e:
        logger.error(f"合并请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}")


@router.post("/correction", response_model=CorrectionRequest)
async def submit_correction_request(request: CorrectionRequest):
    """
    提交数据修正请求
    
    当用户发现概念描述、关系类型等错误时调用
    """
    try:
        logger.info(f"收到修正请求: {request.object_type}.{request.object_id}.{request.field}")
        
        # TODO:
        # 1. 验证对象是否存在
        # 2. 存储到复核队列
        # 3. 返回请求 ID
        
        return request
    
    except Exception as e:
        logger.error(f"修正请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}")


@router.post("/unlink", response_model=UnlinkRequest)
async def submit_unlink_request(request: UnlinkRequest):
    """
    提交实体解链请求
    
    当用户发现提及被错误链接到概念时调用
    """
    try:
        logger.info(f"收到解链请求: {request.mention_text} -> {request.linked_concept_id}")
        
        # TODO:
        # 1. 验证链接是否存在
        # 2. 存储到复核队列
        # 3. 返回请求 ID
        
        return request
    
    except Exception as e:
        logger.error(f"解链请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"请求失败: {str(e)}")


@router.get("/pending")
async def list_pending_requests(
    feedback_type: Optional[str] = None,
    limit: int = 20
):
    """
    列出待审核的反馈请求
    
    Args:
        feedback_type: 可选，过滤类型（merge/correction/unlink）
        limit: 返回数量
    """
    try:
        # TODO: 查询待审核队列
        return {"requests": []}
    
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/review/{request_id}")
async def review_feedback(
    request_id: str,
    action: str,  # approve | reject
    comment: Optional[str] = None
):
    """
    审核反馈请求
    
    Args:
        request_id: 请求 ID
        action: 审核动作（approve/reject）
        comment: 审核意见
    """
    try:
        logger.info(f"审核反馈: request_id={request_id}, action={action}")
        
        # TODO:
        # 1. 查询请求
        # 2. 更新状态
        # 3. 如果 approve，执行对应操作（合并/修正/解链）
        # 4. 记录日志
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"审核失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"审核失败: {str(e)}")


__all__ = ["router"]

