"""
LunarInsight GraphRAG Module

基于 Neo4j GraphRAG 的知识图谱构建与检索模块
遵循 .cursor/rules/knowledge-graph-algorithm.mdc 规范

架构说明:
- stages/     - 8 个构建阶段的实现
- models/     - GraphRAG 专用数据模型
- config/     - 配置文件（谓词白名单、本体约束）
- utils/      - 工具函数
- api/        - GraphRAG API 接口
"""

__version__ = "2.0.0-alpha"

from server.graphrag.stages import (
    SemanticChunker,
    CoreferenceResolver,
    EntityLinker,
    ClaimExtractor,
    ThemeBuilder,
    PredicateGovernor,
    GraphService,
    QueryService,
    MetricsService
)

__all__ = [
    "SemanticChunker",
    "CoreferenceResolver",
    "EntityLinker",
    "ClaimExtractor",
    "ThemeBuilder",
    "PredicateGovernor",
    "GraphService",
    "QueryService",
    "MetricsService"
]

