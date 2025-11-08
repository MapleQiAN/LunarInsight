"""AI-powered document segmentation and knowledge extraction service."""
import json
from typing import List, Dict, Any, Optional
from infra.config import settings
from infra.ai_providers import AIProviderFactory, BaseAIClient
from models.graph import TextChunk, Triplet


class AISegmenter:
    """AI-powered document analysis and knowledge extraction."""
    
    def __init__(self):
        """Initialize AI segmenter with configured AI provider."""
        self.provider = settings.ai_provider
        self.client: Optional[BaseAIClient] = None
        self.model = None
        
        try:
            # 优先使用新的通用配置
            api_key = settings.ai_api_key
            model = settings.ai_model
            base_url = settings.ai_base_url
            
            # 向后兼容：如果使用旧的provider，尝试使用旧配置
            if self.provider == "openai" and not api_key:
                api_key = settings.openai_api_key
                model = model or settings.openai_model
                base_url = base_url or settings.openai_base_url
            elif self.provider == "ollama" and not base_url:
                base_url = settings.ollama_base_url
                model = model or settings.ollama_model
            
            # Mock 模式不需要 API key
            if self.provider == "mock":
                api_key = api_key or "mock"
            
            # 创建AI客户端
            self.client = AIProviderFactory.create_client(
                provider=self.provider,
                api_key=api_key,
                model=model,
                base_url=base_url
            )
            self.model = self.client.model
            
            # 获取提供商名称用于显示
            provider_info = AIProviderFactory.get_provider_info(self.provider)
            provider_name = provider_info.get("name", self.provider)
            print(f"✅ AI Segmenter initialized with {provider_name} (model: {self.model})")
            
        except ValueError as e:
            raise ValueError(f"Failed to initialize AI segmenter: {str(e)}")
    
    def optimize_user_prompt(self, user_prompt: str) -> str:
        """
        优化用户提供的 Prompt，使其更适合文档分析。
        
        Args:
            user_prompt: 用户原始 Prompt
            
        Returns:
            优化后的 Prompt
        """
        system_prompt = """你是一个专业的知识工程师，擅长优化文档分析提示词。

你的任务是：
1. 理解用户的分析意图和关注点
2. 将用户的需求转换为清晰、结构化的分析指令
3. 确保优化后的提示词能够引导 AI 提取高质量的知识图谱

优化原则：
- 保留用户的核心关注点和分析目标
- 补充必要的结构化要求（如概念、关系、属性等）
- 使指令更加明确和可执行
- 避免过度复杂，保持简洁有力

请直接返回优化后的提示词，不要添加额外说明。"""

        try:
            response_text = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请优化以下用户提示词：\n\n{user_prompt}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            optimized = response_text.strip()
            print(f"\n🔧 [Prompt优化]")
            print(f"   原始: {user_prompt[:100]}...")
            print(f"   优化: {optimized[:100]}...")
            
            return optimized
            
        except Exception as e:
            print(f"⚠️  Prompt优化失败，使用原始Prompt: {str(e)}")
            return user_prompt
    
    def analyze_document_structure(
        self, 
        chunks: List[TextChunk],
        user_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析文档整体结构，识别主题、关键概念等。
        
        Args:
            chunks: 文档文本块列表
            user_prompt: 用户自定义分析提示（可选）
            
        Returns:
            文档结构分析结果
        """
        # 取前3个chunk作为样本
        sample_text = "\n\n".join([c.text for c in chunks[:3]])
        
        base_prompt = """分析这段文档内容，识别其核心主题、关键概念和知识领域。

请以JSON格式返回：
{
    "themes": ["主题1", "主题2", ...],  // 文档的核心主题（3-5个）
    "domains": ["领域1", "领域2", ...],  // 涉及的知识领域
    "key_concepts": ["概念1", "概念2", ...],  // 最重要的概念（5-10个）
    "document_type": "类型",  // 如：技术文档、学术论文、教程等
    "complexity": "难度"  // 如：入门、中级、高级
}"""

        # 如果有用户Prompt，将其融入分析指令
        if user_prompt:
            analysis_prompt = f"{base_prompt}\n\n用户特别关注：{user_prompt}"
        else:
            analysis_prompt = base_prompt
        
        try:
            # 对于需要 JSON 格式的请求，使用 json_mode 参数
            response_text = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": "你是知识图谱专家，擅长分析文档结构和识别核心概念。请以JSON格式返回结果。"},
                    {"role": "user", "content": f"{analysis_prompt}\n\n文档内容：\n{sample_text}"}
                ],
                temperature=0.3,
                json_mode=True
            )
            
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            print(f"⚠️  文档结构分析失败: {str(e)}")
            return {
                "themes": [],
                "domains": [],
                "key_concepts": [],
                "document_type": "unknown",
                "complexity": "unknown"
            }
    
    def extract_rich_knowledge(
        self,
        chunk: TextChunk,
        document_context: Dict[str, Any],
        user_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从文本块中提取丰富的知识内容，包括概念、关系、属性等。
        
        Args:
            chunk: 文本块
            document_context: 文档整体上下文（主题、领域等）
            user_prompt: 用户自定义提示（可选）
            
        Returns:
            提取的知识内容
        """
        themes = ", ".join(document_context.get("themes", []))
        domains = ", ".join(document_context.get("domains", []))
        
        base_system_prompt = f"""你是一个知识图谱构建专家。当前文档主题：{themes}，涉及领域：{domains}。

你的任务是深度分析文本，提取结构化知识，而不仅仅是格式转换。

请提取：
1. **核心概念**：识别重要的实体、术语、理论等
2. **概念属性**：每个概念的定义、特征、分类等
3. **概念关系**：概念之间的语义关系（因果、包含、对比等）
4. **隐含知识**：文本暗示但未明说的知识

返回JSON格式：
{{
    "concepts": [
        {{
            "name": "概念名称",
            "description": "详细描述（用你的理解总结，不是照抄原文）",
            "domain": "所属领域",
            "category": "概念类型（如：理论/方法/工具/人物/事件等）",
            "attributes": {{"属性名": "属性值"}},
            "aliases": ["别名1", "别名2"],
            "importance": "high/medium/low"
        }}
    ],
    "triplets": [
        {{
            "subject": "主体概念",
            "predicate": "关系类型（用语义化的动词，如：导致/包含/优于/依赖等）",
            "object": "客体概念",
            "context": "关系的上下文说明"
        }}
    ],
    "insights": ["洞察1", "洞察2"]  // 你从文本中获得的深层理解
}}"""

        # 融合用户Prompt
        if user_prompt:
            system_prompt = f"{base_system_prompt}\n\n用户特别要求：{user_prompt}\n请在分析时特别关注用户的需求。"
        else:
            system_prompt = base_system_prompt
        
        try:
            # 对于需要 JSON 格式的请求，使用 json_mode 参数
            response_text = self.client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请深度分析以下文本并提取知识：\n\n{chunk.text}"}
                ],
                temperature=0.5,  # 稍高的温度以获得更有创造性的洞察
                json_mode=True
            )
            
            result = json.loads(response_text)
            
            # 转换为内部数据结构
            concepts = []
            for c in result.get("concepts", []):
                concepts.append({
                    "name": c.get("name", ""),
                    "description": c.get("description", ""),
                    "domain": c.get("domain", ""),
                    "category": c.get("category", ""),
                    "attributes": c.get("attributes", {}),
                    "aliases": c.get("aliases", []),
                    "importance": c.get("importance", "medium")
                })
            
            triplets = []
            for t in result.get("triplets", []):
                triplets.append(Triplet(
                    subject=t.get("subject", ""),
                    predicate=t.get("predicate", ""),
                    object=t.get("object", ""),
                    context=t.get("context", "")
                ))
            
            return {
                "concepts": concepts,
                "triplets": triplets,
                "insights": result.get("insights", [])
            }
            
        except Exception as e:
            print(f"⚠️  知识提取失败: {str(e)}")
            return {
                "concepts": [],
                "triplets": [],
                "insights": []
            }

