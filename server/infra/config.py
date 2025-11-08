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
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_pass: str = "test1234"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
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


# Global settings instance
settings = Settings()

