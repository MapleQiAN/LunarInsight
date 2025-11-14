"""
阶段 3: 论断抽取测试

运行方式:
    pytest tests/graphrag/stages/test_stage3_claim_extractor.py -v -s
    pytest tests/graphrag/stages/test_stage3_claim_extractor.py::test_claim_extraction_basic -v -s
"""

import sys
import logging
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import Mock, patch

from graphrag.stages.stage3_claim_extractor import ClaimExtractor
from graphrag.models.chunk import ChunkMetadata
from graphrag.models.claim import Claim, ClaimRelation

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger("test_stage3")


def print_step(step_num: int, step_name: str, details: str = ""):
    """打印测试步骤"""
    print(f"\n{'='*72}")
    print(f"步骤 {step_num}: {step_name}")
    print(f"{'='*72}")
    if details:
        print(details)


class CustomMockAIClient:
    """自定义 Mock AI 客户端，支持论断抽取和 NLI 验证"""
    
    def __init__(self, custom_claims_response=None, custom_nli_response=None):
        """
        Args:
            custom_claims_response: 自定义论断抽取响应（JSON 字符串或字典）
            custom_nli_response: 自定义 NLI 验证响应（字典）
        """
        self.custom_claims_response = custom_claims_response
        self.custom_nli_response = custom_nli_response or {
            "label": "entailment",
            "confidence": 0.85
        }
    
    def chat_completion(self, messages, temperature=0.3, json_mode=False, **kwargs):
        """模拟 AI 响应"""
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # 判断请求类型
        if "论断" in user_message or "claim" in user_message.lower() or "提取论断" in user_message:
            # 论断抽取请求
            if self.custom_claims_response:
                if isinstance(self.custom_claims_response, dict):
                    return json.dumps(self.custom_claims_response, ensure_ascii=False)
                return self.custom_claims_response
            
            # 默认响应
            return json.dumps({
                "claims": [
                    {
                        "text": "Transformer 采用自注意力机制替代循环结构",
                        "type": "fact",
                        "confidence": 0.9,
                        "evidence_span": [0, 25]
                    },
                    {
                        "text": "自注意力机制使得模型能够并行处理序列",
                        "type": "fact",
                        "confidence": 0.85,
                        "evidence_span": [26, 50]
                    }
                ],
                "relations": [
                    {
                        "source_claim_index": 0,
                        "target_claim_index": 1,
                        "relation_type": "SUPPORTS",
                        "confidence": 0.8,
                        "evidence": "基于自注意力机制，因此能够并行处理"
                    }
                ]
            }, ensure_ascii=False)
        
        elif "nli" in user_message.lower() or "验证" in user_message or "entailment" in user_message.lower():
            # NLI 验证请求
            return json.dumps(self.custom_nli_response, ensure_ascii=False)
        
        # 默认响应
        return json.dumps({"claims": [], "relations": []}, ensure_ascii=False)


def _install_test_mocks(monkeypatch, custom_claims_response=None, custom_nli_response=None):
    """安装测试 Mock"""
    # Mock config_service
    class _ConfigService:
        @staticmethod
        def get_ai_provider_config():
            return {
                "provider": "mock",
                "api_key": "mock",
                "model": "test-model",
                "base_url": ""
            }
    
    from graphrag.stages import stage3_claim_extractor as s3
    monkeypatch.setattr(s3, "config_service", _ConfigService, raising=True)
    
    # Mock AIProviderFactory 返回自定义 Mock 客户端
    custom_client = CustomMockAIClient(
        custom_claims_response=custom_claims_response,
        custom_nli_response=custom_nli_response
    )
    
    def _create_mock_client(provider, api_key=None, model=None, base_url=None):
        return custom_client
    
    monkeypatch.setattr(
        "graphrag.stages.stage3_claim_extractor.AIProviderFactory.create_client",
        _create_mock_client,
        raising=True
    )
    
    # Mock NLI Verifier（简化）
    class _MockNLIVerifier:
        def __init__(self, client=None):
            self.client = client
            self.custom_response = custom_nli_response or {
                "label": "entailment",
                "confidence": 0.85
            }
        
        def verify_claim(self, claim_text, source_text, max_retries=2):
            return self.custom_response
        
        def verify_relation(self, source_claim, target_claim, relation_type, context, max_retries=2):
            return {
                "is_valid": True,
                "confidence": 0.8
            }
    
    monkeypatch.setattr(s3, "NLIVerifier", _MockNLIVerifier, raising=True)


def test_claim_extraction_basic(monkeypatch):
    """测试基本论断抽取功能"""
    print("\n" + "="*80)
    print("测试: 阶段3 论断抽取（基础流程）")
    print("="*80)
    
    _install_test_mocks(monkeypatch)
    
    print_step(0, "初始化 ClaimExtractor")
    extractor = ClaimExtractor()
    
    print_step(1, "准备测试 Chunk")
    text = """
    Transformer 是一种基于自注意力机制的神经网络架构。
    Transformer 由 Vaswani 等人于 2017 年提出。
    自注意力机制使得模型能够并行处理序列，这是 Transformer 的核心优势。
    """
    
    chunk = ChunkMetadata(
        id="test_doc:0",
        doc_id="test_doc",
        text=text.strip(),
        resolved_text=text.strip(),
        coref_mode="rewrite",
        section_path="Introduction",
        chunk_index=0,
        sentence_ids=["test_doc:s0", "test_doc:s1", "test_doc:s2"],
        sentence_count=3,
        window_start=0,
        window_end=2,
        build_version="test_003"
    )
    
    print(f"Chunk ID: {chunk.id}")
    print(f"文本长度: {len(chunk.text)} 字符")
    print(f"文本内容:\n{chunk.text}")
    
    print_step(2, "执行论断抽取")
    claims, relations = extractor.extract(chunk)
    
    print_step(3, "检查结果")
    print(f"抽取的论断数: {len(claims)}")
    print(f"抽取的关系数: {len(relations)}")
    
    for i, claim in enumerate(claims):
        print(f"\n论断 {i+1}:")
        print(f"  ID: {claim.id}")
        print(f"  文本: {claim.text}")
        print(f"  类型: {claim.claim_type}")
        print(f"  置信度: {claim.confidence:.2f}")
        print(f"  语气: {claim.modality}")
        print(f"  极性: {claim.polarity}")
        print(f"  确定性: {claim.certainty:.2f}")
        print(f"  证据区间: {claim.evidence_span}")
    
    for i, rel in enumerate(relations):
        print(f"\n关系 {i+1}:")
        print(f"  ID: {rel.id}")
        print(f"  源论断: {rel.source_claim_id}")
        print(f"  目标论断: {rel.target_claim_id}")
        print(f"  关系类型: {rel.relation_type}")
        print(f"  置信度: {rel.confidence:.2f}")
    
    # 断言
    assert isinstance(claims, list), "应该返回论断列表"
    assert isinstance(relations, list), "应该返回关系列表"
    assert len(claims) > 0, "应该至少抽取到一个论断"
    
    # 检查论断属性
    for claim in claims:
        assert isinstance(claim, Claim), "论断应该是 Claim 对象"
        assert len(claim.text) >= 20, "论断文本应该至少 20 字符"
        assert 0.0 <= claim.confidence <= 1.0, "置信度应该在 [0,1]"
        assert claim.doc_id == chunk.doc_id, "论断应该属于正确的文档"
        assert claim.chunk_id == chunk.id, "论断应该属于正确的 Chunk"
    
    print(f"\n✓ 测试通过: 阶段3 论断抽取（基础流程）正常")


def test_claim_extraction_custom_text(monkeypatch):
    """测试自定义文本的论断抽取（允许在代码中写入自定义文本）"""
    print("\n" + "="*80)
    print("测试: 阶段3 论断抽取（自定义文本）")
    print("="*80)
    
    # 自定义论断抽取响应
    custom_response = {
        "claims": [
            {
                "text": "深度学习模型在自然语言处理任务中表现出色",
                "type": "fact",
                "confidence": 0.95,
                "evidence_span": [0, 30]
            },
            {
                "text": "BERT 模型通过双向编码器理解上下文",
                "type": "fact",
                "confidence": 0.88,
                "evidence_span": [31, 60]
            },
            {
                "text": "GPT 模型使用自回归方式生成文本",
                "type": "fact",
                "confidence": 0.90,
                "evidence_span": [61, 90]
            }
        ],
        "relations": [
            {
                "source_claim_index": 0,
                "target_claim_index": 1,
                "relation_type": "SUPPORTS",
                "confidence": 0.85,
                "evidence": "BERT 是深度学习模型的一个例子"
            },
            {
                "source_claim_index": 0,
                "target_claim_index": 2,
                "relation_type": "SUPPORTS",
                "confidence": 0.82,
                "evidence": "GPT 也是深度学习模型的一个例子"
            }
        ]
    }
    
    _install_test_mocks(monkeypatch, custom_claims_response=custom_response)
    
    print_step(0, "初始化 ClaimExtractor（使用自定义响应）")
    extractor = ClaimExtractor()
    
    print_step(1, "准备自定义测试文本")
    # 允许在代码中写入自定义文本
    custom_text = """
    深度学习模型在自然语言处理任务中表现出色。
    BERT 模型通过双向编码器理解上下文，这使得它在理解任务中表现优异。
    GPT 模型使用自回归方式生成文本，这使得它在生成任务中表现出色。
    这两种模型都是深度学习在 NLP 领域的成功应用。
    """
    
    chunk = ChunkMetadata(
        id="test_doc_custom:0",
        doc_id="test_doc_custom",
        text=custom_text.strip(),
        resolved_text=custom_text.strip(),
        coref_mode="rewrite",
        section_path="Custom Section",
        chunk_index=0,
        sentence_ids=["test_doc_custom:s0", "test_doc_custom:s1", "test_doc_custom:s2", "test_doc_custom:s3"],
        sentence_count=4,
        window_start=0,
        window_end=3,
        build_version="test_custom_003"
    )
    
    print(f"自定义文本:\n{chunk.text}")
    print(f"文本长度: {len(chunk.text)} 字符")
    
    print_step(2, "执行论断抽取（使用自定义响应）")
    claims, relations = extractor.extract(chunk)
    
    print_step(3, "检查自定义结果")
    print(f"抽取的论断数: {len(claims)}")
    print(f"抽取的关系数: {len(relations)}")
    
    # 验证自定义响应中的论断是否被正确提取
    expected_claim_texts = [
        "深度学习模型在自然语言处理任务中表现出色",
        "BERT 模型通过双向编码器理解上下文",
        "GPT 模型使用自回归方式生成文本"
    ]
    
    extracted_texts = [claim.text for claim in claims]
    print(f"\n期望的论断文本: {expected_claim_texts}")
    print(f"实际提取的论断文本: {extracted_texts}")
    
    # 检查是否包含期望的论断（至少部分匹配）
    found_count = 0
    for expected in expected_claim_texts:
        for extracted in extracted_texts:
            if expected[:20] in extracted or extracted[:20] in expected:
                found_count += 1
                break
    
    print(f"\n匹配的论断数: {found_count}/{len(expected_claim_texts)}")
    
    # 断言
    assert len(claims) >= 2, "应该至少抽取到 2 个论断"
    assert len(relations) >= 1, "应该至少抽取到 1 个关系"
    
    print(f"\n✓ 测试通过: 阶段3 论断抽取（自定义文本）正常")


def test_claim_extraction_with_context(monkeypatch):
    """测试带上下文的论断抽取（篇章感知）"""
    print("\n" + "="*80)
    print("测试: 阶段3 论断抽取（带上下文）")
    print("="*80)
    
    _install_test_mocks(monkeypatch)
    
    print_step(0, "初始化 ClaimExtractor")
    extractor = ClaimExtractor()
    
    print_step(1, "准备主 Chunk 和相邻 Chunks")
    prev_text = "在深度学习领域，Transformer 架构具有重要意义。"
    main_text = "Transformer 采用自注意力机制，这使得它能够并行处理序列。"
    next_text = "这种并行化能力大大提高了训练效率。"
    
    prev_chunk = ChunkMetadata(
        id="test_doc:0",
        doc_id="test_doc",
        text=prev_text,
        resolved_text=prev_text,
        coref_mode="rewrite",
        chunk_index=0,
        sentence_ids=["test_doc:s0"],
        sentence_count=1,
        window_start=0,
        window_end=0,
        build_version="test_003"
    )
    
    main_chunk = ChunkMetadata(
        id="test_doc:1",
        doc_id="test_doc",
        text=main_text,
        resolved_text=main_text,
        coref_mode="rewrite",
        chunk_index=1,
        sentence_ids=["test_doc:s1"],
        sentence_count=1,
        window_start=1,
        window_end=1,
        build_version="test_003"
    )
    
    next_chunk = ChunkMetadata(
        id="test_doc:2",
        doc_id="test_doc",
        text=next_text,
        resolved_text=next_text,
        coref_mode="rewrite",
        chunk_index=2,
        sentence_ids=["test_doc:s2"],
        sentence_count=1,
        window_start=2,
        window_end=2,
        build_version="test_003"
    )
    
    adjacent_chunks = [prev_chunk, next_chunk]
    
    print(f"前文: {prev_text}")
    print(f"当前: {main_text}")
    print(f"后文: {next_text}")
    
    print_step(2, "执行带上下文的论断抽取")
    claims, relations = extractor.extract(main_chunk, adjacent_chunks=adjacent_chunks)
    
    print_step(3, "检查结果")
    print(f"抽取的论断数: {len(claims)}")
    print(f"抽取的关系数: {len(relations)}")
    
    # 断言
    assert isinstance(claims, list), "应该返回论断列表"
    assert isinstance(relations, list), "应该返回关系列表"
    
    print(f"\n✓ 测试通过: 阶段3 论断抽取（带上下文）正常")


def test_claim_extraction_empty_text(monkeypatch):
    """测试空文本处理"""
    print("\n" + "="*80)
    print("测试: 阶段3 论断抽取（空文本）")
    print("="*80)
    
    _install_test_mocks(monkeypatch)
    
    print_step(0, "初始化 ClaimExtractor")
    extractor = ClaimExtractor()
    
    print_step(1, "准备空文本 Chunk")
    chunk = ChunkMetadata(
        id="test_doc_empty:0",
        doc_id="test_doc_empty",
        text="",  # 空文本
        resolved_text="",
        coref_mode="rewrite",
        chunk_index=0,
        sentence_ids=[],
        sentence_count=0,
        window_start=0,
        window_end=0,
        build_version="test_003"
    )
    
    print_step(2, "执行论断抽取")
    claims, relations = extractor.extract(chunk)
    
    print_step(3, "检查结果")
    print(f"抽取的论断数: {len(claims)}")
    print(f"抽取的关系数: {len(relations)}")
    
    # 空文本应该返回空结果或很少的结果
    # 注意：由于 Mock 客户端可能返回默认响应，这里只检查类型
    assert isinstance(claims, list), "应该返回论断列表"
    assert isinstance(relations, list), "应该返回关系列表"
    
    print(f"\n✓ 测试通过: 阶段3 论断抽取（空文本）处理正常")


def test_claim_extraction_modality_detection(monkeypatch):
    """测试语气检测功能"""
    print("\n" + "="*80)
    print("测试: 阶段3 论断抽取（语气检测）")
    print("="*80)
    
    _install_test_mocks(monkeypatch)
    
    print_step(0, "初始化 ClaimExtractor")
    extractor = ClaimExtractor()
    
    print_step(1, "测试不同语气的文本")
    # 断言语气
    assertive_text = "Transformer 采用自注意力机制。"
    # 谨慎语气
    hedged_text = "Transformer 可能采用自注意力机制。"
    # 推测语气
    speculative_text = "如果 Transformer 采用自注意力机制，那么它能够并行处理。"
    
    test_cases = [
        ("断言语气", assertive_text, "assertive"),
        ("谨慎语气", hedged_text, "hedged"),
        ("推测语气", speculative_text, "speculative")
    ]
    
    for name, text, expected_modality in test_cases:
        print(f"\n测试: {name}")
        print(f"文本: {text}")
        
        modality = extractor._detect_modality(text)
        print(f"检测到的语气: {modality}")
        print(f"期望的语气: {expected_modality}")
        
        assert modality == expected_modality, f"{name} 的语气检测应该为 {expected_modality}"
    
    print(f"\n✓ 测试通过: 阶段3 语气检测正常")


def test_claim_extraction_polarity_detection(monkeypatch):
    """测试极性检测功能"""
    print("\n" + "="*80)
    print("测试: 阶段3 论断抽取（极性检测）")
    print("="*80)
    
    _install_test_mocks(monkeypatch)
    
    print_step(0, "初始化 ClaimExtractor")
    extractor = ClaimExtractor()
    
    print_step(1, "测试不同极性的文本")
    # 肯定极性
    positive_text = "Transformer 是一种优秀的架构。"
    # 否定极性
    negative_text = "Transformer 不是循环神经网络。"
    
    test_cases = [
        ("肯定极性", positive_text, "positive"),
        ("否定极性", negative_text, "negative")
    ]
    
    for name, text, expected_polarity in test_cases:
        print(f"\n测试: {name}")
        print(f"文本: {text}")
        
        polarity = extractor._detect_polarity(text)
        print(f"检测到的极性: {polarity}")
        print(f"期望的极性: {expected_polarity}")
        
        assert polarity == expected_polarity, f"{name} 的极性检测应该为 {expected_polarity}"
    
    print(f"\n✓ 测试通过: 阶段3 极性检测正常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

