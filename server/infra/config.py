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
    ai_provider: Literal["openai", "ollama", "mock"] = "mock"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None  # 可自定义OpenAI API地址
    
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

