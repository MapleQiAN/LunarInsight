"""
GraphRAG API 接口

FastAPI 路由与端点定义
"""

from graphrag.api.query import router as query_router
from graphrag.api.feedback import router as feedback_router

__all__ = [
    "query_router",
    "feedback_router"
]

