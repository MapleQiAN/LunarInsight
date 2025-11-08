"""Configuration management for LunarInsight."""
import os
from typing import Optional
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
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    
    # File Upload Configuration
    upload_dir: str = "./uploads"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000


# Global settings instance
settings = Settings()

