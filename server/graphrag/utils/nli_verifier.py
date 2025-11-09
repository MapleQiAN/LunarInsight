"""
NLI (Natural Language Inference) 验证工具

用于验证论断和关系的正确性
"""

import logging
from typing import Literal, Optional, Dict, Any
from infra.ai_providers import BaseAIClient

logger = logging.getLogger("graphrag.nli")


class NLIVerifier:
    """
    NLI 验证器
    
    使用自然语言推理验证：
    1. 论断是否可以从原文中推理出来（entailment）
    2. 关系是否正确（premise -> hypothesis）
    """
    
    def __init__(self, client: Optional[BaseAIClient] = None):
        """
        初始化 NLI 验证器
        
        Args:
            client: AI 客户端（如果为 None，则使用 mock 模式）
        """
        self.client = client
        if not self.client:
            logger.warning("NLI Verifier initialized without AI client, using mock mode")
    
    def verify_claim(
        self,
        claim_text: str,
        source_text: str,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        验证论断是否可以从原文中推理出来
        
        Args:
            claim_text: 论断文本
            source_text: 原文（premise）
            max_retries: 最大重试次数（多头验证）
        
        Returns:
            {
                "label": "entailment" | "contradiction" | "neutral",
                "confidence": float,
                "reasoning": str,
                "verification_count": int
            }
        """
        if not self.client:
            # Mock 模式：返回默认结果
            return {
                "label": "entailment",
                "confidence": 0.7,
                "reasoning": "Mock verification (no AI client)",
                "verification_count": 0
            }
        
        # 多头验证：多次调用取平均
        results = []
        for i in range(max_retries):
            try:
                result = self._single_verification(claim_text, source_text)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"NLI 验证失败 (尝试 {i+1}/{max_retries}): {e}")
        
        if not results:
            # 所有验证都失败，返回中性结果
            return {
                "label": "neutral",
                "confidence": 0.5,
                "reasoning": "所有验证尝试均失败",
                "verification_count": max_retries
            }
        
        # 聚合结果：取最常见的 label，平均 confidence
        label_counts = {}
        total_confidence = 0.0
        
        for r in results:
            label = r.get("label", "neutral")
            label_counts[label] = label_counts.get(label, 0) + 1
            total_confidence += r.get("confidence", 0.5)
        
        # 选择最常见的 label
        best_label = max(label_counts.items(), key=lambda x: x[1])[0]
        avg_confidence = total_confidence / len(results)
        
        # 合并 reasoning
        reasoning_parts = [r.get("reasoning", "") for r in results if r.get("reasoning")]
        combined_reasoning = " | ".join(reasoning_parts[:2])  # 最多保留前两个
        
        return {
            "label": best_label,
            "confidence": avg_confidence,
            "reasoning": combined_reasoning,
            "verification_count": len(results)
        }
    
    def verify_relation(
        self,
        source_claim: str,
        target_claim: str,
        relation_type: str,
        context: Optional[str] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        验证关系是否正确
        
        Args:
            source_claim: 源论断
            target_claim: 目标论断
            relation_type: 关系类型（SUPPORTS/CONTRADICTS/CAUSES等）
            context: 上下文文本（可选）
            max_retries: 最大重试次数（多头验证）
        
        Returns:
            {
                "is_valid": bool,
                "confidence": float,
                "reasoning": str,
                "verification_count": int
            }
        """
        if not self.client:
            # Mock 模式
            return {
                "is_valid": True,
                "confidence": 0.7,
                "reasoning": "Mock verification (no AI client)",
                "verification_count": 0
            }
        
        # 构建 premise 和 hypothesis
        # premise: source_claim + context
        # hypothesis: 根据 relation_type 构建
        premise = source_claim
        if context:
            premise = f"{context}\n\n{source_claim}"
        
        # 根据关系类型构建 hypothesis
        relation_hypotheses = {
            "SUPPORTS": f"{source_claim} 支持 {target_claim}",
            "CONTRADICTS": f"{source_claim} 与 {target_claim} 矛盾",
            "CAUSES": f"{source_claim} 导致 {target_claim}",
            "COMPARES_WITH": f"{source_claim} 与 {target_claim} 进行比较",
            "CONDITIONS": f"如果 {source_claim}，则 {target_claim}",
            "PURPOSE": f"{source_claim} 的目的是 {target_claim}"
        }
        
        hypothesis = relation_hypotheses.get(relation_type, f"{source_claim} 与 {target_claim} 相关")
        
        # 多头验证
        results = []
        for i in range(max_retries):
            try:
                result = self._single_verification(hypothesis, premise)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"关系验证失败 (尝试 {i+1}/{max_retries}): {e}")
        
        if not results:
            return {
                "is_valid": False,
                "confidence": 0.3,
                "reasoning": "所有验证尝试均失败",
                "verification_count": max_retries
            }
        
        # 聚合结果：如果大部分验证认为是 entailment，则关系有效
        entailment_count = sum(1 for r in results if r.get("label") == "entailment")
        avg_confidence = sum(r.get("confidence", 0.5) for r in results) / len(results)
        
        is_valid = entailment_count >= len(results) / 2  # 至少一半验证通过
        
        reasoning_parts = [r.get("reasoning", "") for r in results if r.get("reasoning")]
        combined_reasoning = " | ".join(reasoning_parts[:2])
        
        return {
            "is_valid": is_valid,
            "confidence": avg_confidence,
            "reasoning": combined_reasoning,
            "verification_count": len(results)
        }
    
    def _single_verification(
        self,
        hypothesis: str,
        premise: str
    ) -> Optional[Dict[str, Any]]:
        """
        单次 NLI 验证
        
        Args:
            hypothesis: 假设（要验证的论断或关系）
            premise: 前提（原文或源论断）
        
        Returns:
            {
                "label": "entailment" | "contradiction" | "neutral",
                "confidence": float,
                "reasoning": str
            }
        """
        prompt = f"""你是一个自然语言推理（NLI）专家。请判断前提（premise）是否蕴含假设（hypothesis）。

前提（Premise）:
{premise}

假设（Hypothesis）:
{hypothesis}

请判断前提是否蕴含假设，返回 JSON 格式：
{{
  "label": "entailment" | "contradiction" | "neutral",
  "confidence": 0.0-1.0,
  "reasoning": "简要说明判断理由"
}}

说明：
- "entailment": 前提蕴含假设（可以从前提推理出假设）
- "contradiction": 前提与假设矛盾
- "neutral": 前提与假设无关或无法确定
"""
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的自然语言推理专家，擅长判断文本间的逻辑关系。请严格按照 JSON 格式返回结果。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            raw_content = self.client.chat_completion(
                messages=messages,
                temperature=0.2,  # 低温度以获得更一致的结果
                json_mode=True
            )
            
            import json
            result = json.loads(raw_content)
            
            label = result.get("label", "neutral")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            
            # 验证 label 的有效性
            if label not in ["entailment", "contradiction", "neutral"]:
                label = "neutral"
            
            return {
                "label": label,
                "confidence": max(0.0, min(1.0, confidence)),
                "reasoning": reasoning
            }
        except Exception as e:
            logger.error(f"NLI 验证调用失败: {e}")
            return None


__all__ = ["NLIVerifier"]

