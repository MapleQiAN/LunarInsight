"""Settings API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from infra.config import settings
from infra.ai_providers import AIProviderFactory
from services.config_service import config_service

router = APIRouter(prefix="/settings", tags=["settings"])


class AISettings(BaseModel):
    """AI configuration settings."""
    ai_provider: Literal[
        "openai", "anthropic", "google", "deepseek", "qwen", 
        "glm", "moonshot", "ernie", "minimax", "doubao", 
        "ollama", "mock"
    ]
    # 通用配置
    ai_api_key: Optional[str] = None
    ai_model: Optional[str] = None
    ai_base_url: Optional[str] = None
    # 向后兼容的旧配置
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"


class DatabaseSettings(BaseModel):
    """Database configuration settings."""
    neo4j_uri: str
    neo4j_user: str
    redis_url: str


class AllSettings(BaseModel):
    """All application settings."""
    ai_provider: Literal[
        "openai", "anthropic", "google", "deepseek", "qwen", 
        "glm", "moonshot", "ernie", "minimax", "doubao", 
        "ollama", "mock"
    ]
    ai_api_key: Optional[str] = None
    ai_model: Optional[str] = None
    ai_base_url: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: str
    openai_base_url: Optional[str] = None
    ollama_base_url: str
    ollama_model: str
    neo4j_uri: str
    neo4j_user: str
    redis_url: str


@router.get("/ai-providers")
async def list_ai_providers():
    """List all supported AI providers."""
    return {
        "providers": AIProviderFactory.list_providers()
    }


@router.get("/")
async def get_settings():
    """Get current settings."""
    # Read from database for runtime config
    runtime_config = config_service.get_runtime_config()
    
    # Mask API keys for security
    return {
        "ai_provider": runtime_config.get("ai_provider"),
        "ai_api_key": "***" if runtime_config.get("ai_api_key") else None,
        "ai_model": runtime_config.get("ai_model"),
        "ai_base_url": runtime_config.get("ai_base_url"),
        "openai_api_key": "***" if runtime_config.get("openai_api_key") else None,
        "openai_model": runtime_config.get("openai_model"),
        "openai_base_url": runtime_config.get("openai_base_url"),
        "ollama_base_url": runtime_config.get("ollama_base_url"),
        "ollama_model": runtime_config.get("ollama_model"),
        # 基础设施配置仍从环境变量读取（只读）
        "neo4j_uri": settings.neo4j_uri,
        "neo4j_user": settings.neo4j_user,
        "redis_url": settings.redis_url,
    }


@router.post("/ai")
async def update_ai_settings(ai_settings: AISettings):
    """Update AI provider settings."""
    try:
        # 准备要更新的配置
        config_update = {
            "ai_provider": ai_settings.ai_provider,
        }
        
        # 更新通用配置
        if ai_settings.ai_api_key and ai_settings.ai_api_key != "***":
            config_update['ai_api_key'] = ai_settings.ai_api_key
        if ai_settings.ai_model:
            config_update['ai_model'] = ai_settings.ai_model
        else:
            # 如果模型为空，清空数据库中的值
            config_update['ai_model'] = None
        if ai_settings.ai_base_url:
            config_update['ai_base_url'] = ai_settings.ai_base_url
        else:
            config_update['ai_base_url'] = None
        
        # 更新兼容性配置
        if ai_settings.openai_api_key and ai_settings.openai_api_key != "***":
            config_update['openai_api_key'] = ai_settings.openai_api_key
        config_update['openai_model'] = ai_settings.openai_model
        if ai_settings.openai_base_url:
            config_update['openai_base_url'] = ai_settings.openai_base_url
        else:
            config_update['openai_base_url'] = None
        
        config_update['ollama_base_url'] = ai_settings.ollama_base_url
        config_update['ollama_model'] = ai_settings.ollama_model
        
        # 保存到数据库
        success = config_service.update_runtime_config(config_update)
        
        if success:
            return {
                "success": True,
                "message": "AI 配置已成功更新，立即生效"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration to database")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.post("/test-connection")
async def test_ai_connection(ai_settings: AISettings):
    """Test AI provider connection."""
    try:
        if ai_settings.ai_provider == "mock":
            return {
                "success": True,
                "message": "Mock 模式 - 无需连接测试"
            }
        
        # 使用 AIProviderFactory 创建客户端进行测试
        try:
            # 优先使用通用配置
            api_key = ai_settings.ai_api_key
            model = ai_settings.ai_model
            base_url = ai_settings.ai_base_url
            
            # 向后兼容：如果使用旧的provider，尝试使用旧配置
            if ai_settings.ai_provider == "openai" and not api_key:
                api_key = ai_settings.openai_api_key
                model = model or ai_settings.openai_model
                base_url = base_url or ai_settings.openai_base_url
            elif ai_settings.ai_provider == "ollama" and not base_url:
                base_url = ai_settings.ollama_base_url
                model = model or ai_settings.ollama_model
            
            # 过滤掉 "***" 占位符
            if api_key == "***":
                api_key = None
            
            client = AIProviderFactory.create_client(
                provider=ai_settings.ai_provider,
                api_key=api_key,
                model=model,
                base_url=base_url
            )
            
            # 简单的测试调用
            response = client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.3,
                max_tokens=5
            )
            
            provider_names = {
                "openai": "OpenAI GPT",
                "anthropic": "Anthropic Claude",
                "google": "Google Gemini",
                "deepseek": "DeepSeek",
                "qwen": "阿里云通义千问",
                "glm": "智谱AI (GLM)",
                "moonshot": "月之暗面 Kimi",
                "ernie": "百度文心一言",
                "minimax": "MiniMax",
                "doubao": "字节豆包",
                "ollama": "Ollama"
            }
            provider_name = provider_names.get(ai_settings.ai_provider, ai_settings.ai_provider)
            
            return {
                "success": True,
                "message": f"成功连接到 {provider_name} (模型: {client.model})"
            }
            
        except ValueError as e:
            return {
                "success": False,
                "message": f"配置错误: {str(e)}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}"
        }


@router.get("/ollama/models")
async def get_ollama_models():
    """Get available Ollama models."""
    try:
        import httpx
        # 从数据库读取当前配置的 Ollama 地址
        runtime_config = config_service.get_runtime_config()
        ollama_url = runtime_config.get("ollama_base_url", settings.ollama_base_url)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                return {
                    "success": True,
                    "models": models
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to fetch Ollama models"
                }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to connect to Ollama: {str(e)}"
        }

