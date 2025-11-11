"""Configuration management for LunarInsight."""
import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:17687"
    neo4j_user: str = "neo4j"
    neo4j_pass: str = "test1234"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:16379/0"
    
    # AI Provider Configuration
    ai_provider: Literal[
        "openai",           # OpenAI GPT
        "anthropic",        # Anthropic Claude
        "google",           # Google Gemini
        "deepseek",         # DeepSeek
        "qwen",             # 阿里云通义千问
        "glm",              # 智谱AI (GLM)
        "moonshot",         # 月之暗面 Kimi
        "ernie",            # 百度文心一言
        "minimax",          # MiniMax
        "doubao",           # 字节豆包
        "ollama",           # Ollama 本地模型
        "mock"              # Mock 模式
    ] = "mock"
    
    # 通用 AI 配置
    ai_api_key: Optional[str] = None        # AI服务的API密钥
    ai_model: Optional[str] = None          # 模型名称（留空则使用默认）
    ai_base_url: Optional[str] = None       # 自定义API地址（留空则使用默认）
    
    # === 以下为兼容性配置（旧版本） ===
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    
    # File Upload Configuration
    upload_dir: str = "./uploads"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # ============================================
    # GraphRAG 配置 (v2.0-GraphRAG)
    # ============================================
    
    # GraphRAG 功能开关
    enable_neo4j_graphrag: bool = True
    enable_vector_search: bool = True
    
    # 模型配置
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536  # OpenAI text-embedding-3-small 维度
    
    # 本体约束配置
    # 允许的节点类型
    allowed_node_types: list[str] = [
        "Concept", "Person", "Method", "Tool", "Metric", 
        "Chunk", "Claim", "Theme", "Document", "Topic"
    ]
    
    # 允许的关系类型（标准谓词白名单）
    allowed_relations: list[str] = [
        "IS_A", "PART_OF", "USES", "IMPLEMENTED_BY", "CREATES",
        "DERIVES_FROM", "CONTAINS", "BELONGS_TO", "SUPPORTS",
        "CONTRADICTS", "CAUSES", "COMPARES_WITH", "CONDITIONS",
        "PURPOSE", "MENTIONS", "CONTAINS_CLAIM", "BELONGS_TO_THEME",
        "EVIDENCE_FROM", "SIMILAR_TO"
    ]
    
    # 阈值配置
    entity_link_accept_threshold: float = 0.85  # 实体链接接受阈值
    entity_link_review_threshold: float = 0.65   # 实体链接复核阈值
    claim_confidence_threshold: float = 0.7      # 论断置信度阈值
    
    # 向量检索配置
    vector_search_top_k: int = 5                 # 向量检索 Top-K
    vector_search_threshold: float = 0.7         # 向量相似度阈值
    
    # 社区检测配置
    community_algorithm: str = "louvain"         # 社区检测算法: louvain | leiden
    community_min_size: int = 3                  # 最小社区规模
    
    # 谓词治理配置
    predicate_governance_enabled: bool = True    # 是否启用谓词治理
    predicate_mapping_file: str = "graphrag/config/predicates.yaml"
    ontology_config_file: str = "graphrag/config/ontology.yaml"
    
    # 构建版本配置
    build_version_prefix: str = "v2.0"          # 构建版本前缀


# Global settings instance
settings = Settings()

