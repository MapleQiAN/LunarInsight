"""AI Provider configuration and unified interface."""
from typing import Optional, Literal, List, Dict, Any
from openai import OpenAI
import anthropic
import json


# 支持的AI提供商类型
AIProviderType = Literal[
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
    "mock"              # Mock 模式（测试用）
]


class BaseAIClient:
    """Base AI client interface."""
    
    def __init__(self, model: str, **kwargs):
        self.model = model
        self.kwargs = kwargs
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        """
        Send chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            extra_params: Additional provider-specific parameters
            
        Returns:
            Response text content
        """
        raise NotImplementedError


class OpenAIClient(BaseAIClient):
    """OpenAI GPT client."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"} if extra_params.get("json_mode") else None,
            **{k: v for k, v in extra_params.items() if k != "json_mode"}
        )
        return response.choices[0].message.content


class AnthropicClient(BaseAIClient):
    """Anthropic Claude client."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic.Anthropic(**kwargs)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        # Anthropic 的 messages 格式稍有不同，需要分离 system 消息
        system_msg = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        # 如果请求 JSON 模式，在 system prompt 中添加要求
        if extra_params.get("json_mode"):
            json_instruction = "\n\n重要：请确保返回的内容是有效的 JSON 格式，不要包含任何额外的文本或说明。"
            if system_msg:
                system_msg = system_msg + json_instruction
            else:
                system_msg = json_instruction.strip()
        
        kwargs = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": extra_params.get("max_tokens", 4096)
        }
        
        # 过滤掉 json_mode 参数
        kwargs = {k: v for k, v in kwargs.items() if k != "json_mode"}
        
        if system_msg:
            kwargs["system"] = system_msg
        
        response = self.client.messages.create(**kwargs)
        return response.content[0].text


class GoogleGeminiClient(BaseAIClient):
    """Google Gemini client (via OpenAI-compatible API)."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        # Google Gemini 可以通过 OpenAI 兼容接口访问
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        # 处理 json_mode 参数
        params = {k: v for k, v in extra_params.items() if k != "json_mode"}
        if extra_params.get("json_mode"):
            params["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            **params
        )
        return response.choices[0].message.content


class OpenAICompatibleClient(BaseAIClient):
    """
    Generic OpenAI-compatible client for providers like:
    - DeepSeek
    - 通义千问 (Qwen)
    - 智谱AI (GLM)
    - Moonshot (Kimi)
    - 文心一言 (ERNIE)
    - MiniMax
    - 豆包 (Doubao)
    - Ollama
    """
    
    def __init__(self, api_key: str, model: str, base_url: str):
        super().__init__(model)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        # 处理 json_mode 参数
        params = {k: v for k, v in extra_params.items() if k != "json_mode"}
        if extra_params.get("json_mode"):
            params["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            **params
        )
        return response.choices[0].message.content


class MockClient(BaseAIClient):
    """Mock client for testing."""
    
    def __init__(self):
        super().__init__("mock")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        # 返回一个简单的mock响应
        return json.dumps({
            "triplets": [
                {
                    "subject": "示例主体",
                    "predicate": "relates_to",
                    "object": "示例客体",
                    "confidence": 0.5,
                    "language": "zh"
                }
            ]
        })


class AIProviderFactory:
    """Factory for creating AI clients."""
    
    # 默认的 base_url 配置
    DEFAULT_BASE_URLS = {
        "openai": None,  # 使用默认
        "anthropic": None,
        "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "deepseek": "https://api.deepseek.com/v1",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "glm": "https://open.bigmodel.cn/api/paas/v4",
        "moonshot": "https://api.moonshot.cn/v1",
        "ernie": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
        "minimax": "https://api.minimax.chat/v1",
        "doubao": "https://ark.cn-beijing.volces.com/api/v3",
        "ollama": "http://localhost:11434/v1"
    }
    
    # 默认模型配置
    DEFAULT_MODELS = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-sonnet-20241022",
        "google": "gemini-2.0-flash-exp",
        "deepseek": "deepseek-chat",
        "qwen": "qwen-plus",
        "glm": "glm-4-flash",
        "moonshot": "moonshot-v1-8k",
        "ernie": "ernie-4.0-8k-latest",
        "minimax": "abab6.5s-chat",
        "doubao": "doubao-pro-4k",
        "ollama": "llama3",
        "mock": "mock"
    }
    
    @classmethod
    def create_client(
        cls,
        provider: AIProviderType,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> BaseAIClient:
        """
        Create AI client based on provider type.
        
        Args:
            provider: AI provider type
            api_key: API key (not needed for mock/ollama)
            model: Model name (use default if not provided)
            base_url: Custom base URL (use default if not provided)
            
        Returns:
            AI client instance
            
        Raises:
            ValueError: If provider is not supported or missing required config
        """
        # 使用默认模型和base_url（如果未提供）
        model = model or cls.DEFAULT_MODELS.get(provider)
        base_url = base_url or cls.DEFAULT_BASE_URLS.get(provider)
        
        if provider == "mock":
            return MockClient()
        
        if provider == "openai":
            if not api_key:
                raise ValueError("OpenAI API key is required")
            return OpenAIClient(api_key, model, base_url)
        
        if provider == "anthropic":
            if not api_key:
                raise ValueError("Anthropic API key is required")
            return AnthropicClient(api_key, model, base_url)
        
        if provider == "google":
            if not api_key:
                raise ValueError("Google API key is required")
            return GoogleGeminiClient(api_key, model, base_url)
        
        # 其他所有 OpenAI 兼容的提供商
        if provider in ["deepseek", "qwen", "glm", "moonshot", "ernie", "minimax", "doubao", "ollama"]:
            # Ollama 不需要真实的 API key
            if provider == "ollama":
                api_key = api_key or "ollama"
            elif not api_key:
                raise ValueError(f"{provider} API key is required")
            
            return OpenAICompatibleClient(api_key, model, base_url)
        
        raise ValueError(f"Unsupported AI provider: {provider}")
    
    @classmethod
    def get_provider_info(cls, provider: AIProviderType) -> Dict[str, Any]:
        """Get provider information including default model and base URL."""
        return {
            "provider": provider,
            "default_model": cls.DEFAULT_MODELS.get(provider),
            "default_base_url": cls.DEFAULT_BASE_URLS.get(provider)
        }
    
    @classmethod
    def list_providers(cls) -> List[Dict[str, Any]]:
        """List all supported providers with their default configurations."""
        return [
            {
                "id": "openai",
                "name": "OpenAI GPT",
                "default_model": cls.DEFAULT_MODELS["openai"],
                "requires_api_key": True
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "default_model": cls.DEFAULT_MODELS["anthropic"],
                "requires_api_key": True
            },
            {
                "id": "google",
                "name": "Google Gemini",
                "default_model": cls.DEFAULT_MODELS["google"],
                "requires_api_key": True
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "default_model": cls.DEFAULT_MODELS["deepseek"],
                "requires_api_key": True
            },
            {
                "id": "qwen",
                "name": "阿里云通义千问",
                "default_model": cls.DEFAULT_MODELS["qwen"],
                "requires_api_key": True
            },
            {
                "id": "glm",
                "name": "智谱AI (GLM)",
                "default_model": cls.DEFAULT_MODELS["glm"],
                "requires_api_key": True
            },
            {
                "id": "moonshot",
                "name": "月之暗面 Kimi",
                "default_model": cls.DEFAULT_MODELS["moonshot"],
                "requires_api_key": True
            },
            {
                "id": "ernie",
                "name": "百度文心一言",
                "default_model": cls.DEFAULT_MODELS["ernie"],
                "requires_api_key": True
            },
            {
                "id": "minimax",
                "name": "MiniMax",
                "default_model": cls.DEFAULT_MODELS["minimax"],
                "requires_api_key": True
            },
            {
                "id": "doubao",
                "name": "字节豆包",
                "default_model": cls.DEFAULT_MODELS["doubao"],
                "requires_api_key": True
            },
            {
                "id": "ollama",
                "name": "Ollama",
                "default_model": cls.DEFAULT_MODELS["ollama"],
                "requires_api_key": False
            },
            {
                "id": "mock",
                "name": "Mock (测试模式)",
                "default_model": "mock",
                "requires_api_key": False
            }
        ]

