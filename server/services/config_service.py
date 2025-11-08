"""Runtime configuration service using Neo4j as storage."""
from typing import Optional, Dict, Any
from infra.neo4j_client import neo4j_client
from infra.config import settings as base_settings


class ConfigService:
    """Service for managing runtime configuration in Neo4j."""
    
    CONFIG_NODE_ID = "system_config"
    
    def get_runtime_config(self) -> Dict[str, Any]:
        """
        Get runtime configuration from Neo4j.
        
        Returns:
            Dictionary with runtime configuration values.
            Falls back to base_settings if not found in database.
        """
        query = """
        MATCH (config:RuntimeConfig {id: $config_id})
        RETURN config
        """
        result = neo4j_client.execute_query(query, {"config_id": self.CONFIG_NODE_ID})
        
        if result and result[0].get("config"):
            config_node = result[0]["config"]
            return {
                "ai_provider": config_node.get("ai_provider", base_settings.ai_provider),
                "ai_api_key": config_node.get("ai_api_key"),
                "ai_model": config_node.get("ai_model"),
                "ai_base_url": config_node.get("ai_base_url"),
                # 兼容性字段
                "openai_api_key": config_node.get("openai_api_key"),
                "openai_model": config_node.get("openai_model", base_settings.openai_model),
                "openai_base_url": config_node.get("openai_base_url"),
                "ollama_base_url": config_node.get("ollama_base_url", base_settings.ollama_base_url),
                "ollama_model": config_node.get("ollama_model", base_settings.ollama_model),
            }
        else:
            # 首次运行，从环境变量初始化
            return self._initialize_from_env()
    
    def _initialize_from_env(self) -> Dict[str, Any]:
        """Initialize runtime config from environment variables."""
        config = {
            "ai_provider": base_settings.ai_provider,
            "ai_api_key": base_settings.ai_api_key,
            "ai_model": base_settings.ai_model,
            "ai_base_url": base_settings.ai_base_url,
            "openai_api_key": base_settings.openai_api_key,
            "openai_model": base_settings.openai_model,
            "openai_base_url": base_settings.openai_base_url,
            "ollama_base_url": base_settings.ollama_base_url,
            "ollama_model": base_settings.ollama_model,
        }
        
        # 保存到数据库
        self.update_runtime_config(config)
        return config
    
    def update_runtime_config(self, config: Dict[str, Any]) -> bool:
        """
        Update runtime configuration in Neo4j.
        
        Args:
            config: Dictionary with configuration values to update.
            
        Returns:
            True if successful, False otherwise.
        """
        # 过滤掉 None 值和 "***" 占位符
        filtered_config = {
            k: v for k, v in config.items() 
            if v is not None and v != "***"
        }
        
        query = """
        MERGE (config:RuntimeConfig {id: $config_id})
        SET config += $properties,
            config.updated_at = datetime()
        RETURN config
        """
        result = neo4j_client.execute_query(query, {
            "config_id": self.CONFIG_NODE_ID,
            "properties": filtered_config
        })
        
        return len(result) > 0
    
    def get_ai_provider_config(self) -> Dict[str, Any]:
        """
        Get AI provider configuration for current provider.
        
        Returns:
            Dictionary with provider, api_key, model, base_url.
        """
        runtime_config = self.get_runtime_config()
        provider = runtime_config.get("ai_provider", "mock")
        
        # 优先使用通用配置
        api_key = runtime_config.get("ai_api_key")
        model = runtime_config.get("ai_model")
        base_url = runtime_config.get("ai_base_url")
        
        # 向后兼容：如果使用旧的 provider，回退到旧配置
        if provider == "openai" and not api_key:
            api_key = runtime_config.get("openai_api_key")
            model = model or runtime_config.get("openai_model")
            base_url = base_url or runtime_config.get("openai_base_url")
        elif provider == "ollama" and not base_url:
            base_url = runtime_config.get("ollama_base_url")
            model = model or runtime_config.get("ollama_model")
        
        return {
            "provider": provider,
            "api_key": api_key,
            "model": model,
            "base_url": base_url
        }


# Global singleton instance
config_service = ConfigService()

