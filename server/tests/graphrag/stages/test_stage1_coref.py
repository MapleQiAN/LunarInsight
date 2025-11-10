"""
阶段 1: 指代消解测试

运行方式:
    pytest tests/graphrag/stages/test_stage1_coref.py -v -s
    pytest tests/graphrag/stages/test_stage1_coref.py::test_coref_basic -v -s
"""

import pytest
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from graphrag.stages.stage1_coref import CoreferenceResolver, CorefResult
from graphrag.models.chunk import ChunkMetadata

# 配置日志以显示详细步骤
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)


def print_step(step_num: int, step_name: str, details: str = ""):
    """打印处理步骤"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {step_name}")
    print(f"{'='*60}")
    if details:
        print(details)


def print_result(result: CorefResult):
    """打印指代消解结果"""
    print(f"\n{'='*60}")
    print("最终结果")
    print(f"{'='*60}")
    print(f"模式: {result.mode}")
    print(f"覆盖率: {result.coverage:.2%}")
    print(f"冲突率: {result.conflict:.2%}")
    print(f"别名映射数: {len(result.alias_map)}")
    print(f"证据链数: {len(result.provenance)}")
    print(f"匹配数: {len(result.matches)}")
    
    if result.alias_map:
        print(f"\n别名映射:")
        for surface, canonical in result.alias_map.items():
            print(f"  '{surface}' → '{canonical}'")
    
    if result.resolved_text and result.resolved_text != result.alias_map:
        print(f"\n文本替换:")
        print(f"  原文长度: {len(result.resolved_text) if result.resolved_text else 0} 字符")
        if result.resolved_text:
            preview = result.resolved_text[:100] + "..." if len(result.resolved_text) > 100 else result.resolved_text
            print(f"  替换后预览: {preview}")
    
    if result.metrics:
        print(f"\n质量指标:")
        for key, value in result.metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2%}" if 'coverage' in key.lower() or 'rate' in key.lower() else f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    
    if result.matches:
        print(f"\n匹配详情:")
        for i, match in enumerate(result.matches, 1):
            conflict_mark = " [冲突]" if match.is_conflict else ""
            print(f"  匹配 {i}: '{match.mention.text}' → '{match.antecedent.text}' "
                  f"(分数={match.score:.3f}, 置信度={match.confidence:.3f}, "
                  f"句距={match.sentence_distance}, 证据={match.evidence_type}){conflict_mark}")


def test_coref_basic():
    """测试基本指代消解功能（输出每一步）"""
    print("\n" + "="*80)
    print("测试: 基本指代消解功能")
    print("="*80)
    
    resolver = CoreferenceResolver()
    
    # 创建测试 Chunk
    chunk = ChunkMetadata(
        id="test_doc:0",
        doc_id="test_doc",
        text="人工智能（AI）是一种模拟人类智能的技术。它能够处理复杂的任务。AI 在多个领域都有应用，包括医疗、金融、教育等行业。",
        chunk_index=0,
        sentence_ids=["test_doc:s0", "test_doc:s1", "test_doc:s2"],
        sentence_count=3,
        window_start=0,
        window_end=2,
        build_version="test_001"
    )
    
    print_step(0, "输入检查", f"Chunk ID: {chunk.id}\n文本: {chunk.text}\n文本长度: {len(chunk.text)} 字符")
    
    # 执行指代消解
    result = resolver.resolve(chunk)
    
    # 打印结果
    print_result(result)
    
    # 断言
    assert isinstance(result, CorefResult), "应该返回 CorefResult"
    assert result.mode in ["rewrite", "local", "alias_only", "skip"], "模式应该是有效值"
    assert 0.0 <= result.coverage <= 1.0, "覆盖率应该在 [0, 1] 范围内"
    assert 0.0 <= result.conflict <= 1.0, "冲突率应该在 [0, 1] 范围内"
    assert isinstance(result.alias_map, dict), "alias_map 应该是字典"
    
    print(f"\n✓ 测试通过: 基本指代消解功能正常")


def test_coref_parenthesis_alias():
    """测试括号别名提取（输出每一步）"""
    print("\n" + "="*80)
    print("测试: 括号别名提取")
    print("="*80)
    
    resolver = CoreferenceResolver()
    
    chunk = ChunkMetadata(
        id="test_doc:1",
        doc_id="test_doc",
        text="自然语言处理（Natural Language Processing, NLP）是人工智能的重要分支。NLP 技术可以帮助计算机理解人类语言。该技术已经广泛应用于多个领域。",
        chunk_index=1,
        sentence_ids=["test_doc:s0", "test_doc:s1", "test_doc:s2"],
        sentence_count=3,
        window_start=0,
        window_end=2,
        build_version="test_001"
    )
    
    print_step(0, "输入检查", f"Chunk ID: {chunk.id}\n文本: {chunk.text}")
    
    result = resolver.resolve(chunk)
    
    print_result(result)
    
    # 断言：应该检测到括号别名
    assert "NLP" in result.alias_map or "自然语言处理" in result.alias_map.values(), "应该提取到括号别名"
    
    print(f"\n✓ 测试通过: 括号别名提取正常")


def test_coref_pronoun_resolution():
    """测试代词消解（输出每一步）"""
    print("\n" + "="*80)
    print("测试: 代词消解")
    print("="*80)
    
    resolver = CoreferenceResolver()
    
    chunk = ChunkMetadata(
        id="test_doc:2",
        doc_id="test_doc",
        text="Transformer 是一种基于自注意力机制的神经网络架构。它由 Vaswani 等人于 2017 年提出。该架构摒弃了传统的循环结构。它实现了并行化训练。",
        chunk_index=2,
        sentence_ids=["test_doc:s0", "test_doc:s1", "test_doc:s2", "test_doc:s3"],
        sentence_count=4,
        window_start=0,
        window_end=3,
        build_version="test_001"
    )
    
    print_step(0, "输入检查", f"Chunk ID: {chunk.id}\n文本: {chunk.text}")
    
    result = resolver.resolve(chunk)
    
    print_result(result)
    
    # 断言：应该检测到代词
    assert result.metrics.get("total_mentions", 0) > 0, "应该检测到提及"
    
    print(f"\n✓ 测试通过: 代词消解正常")


def test_coref_decision_modes():
    """测试不同决策模式（输出每一步）"""
    print("\n" + "="*80)
    print("测试: 决策模式（rewrite/local/alias_only/skip）")
    print("="*80)
    
    resolver = CoreferenceResolver()
    
    # 测试文本：高覆盖率、低冲突率（应该触发 rewrite 模式）
    chunk_rewrite = ChunkMetadata(
        id="test_doc:3",
        doc_id="test_doc",
        text="深度学习（Deep Learning, DL）是机器学习的一个分支。DL 使用多层神经网络来学习数据表示。该技术已经在图像识别、自然语言处理等领域取得了突破。它能够自动提取特征。",
        chunk_index=3,
        sentence_ids=["test_doc:s0", "test_doc:s1", "test_doc:s2", "test_doc:s3"],
        sentence_count=4,
        window_start=0,
        window_end=3,
        build_version="test_001"
    )
    
    print_step(0, "测试 rewrite 模式", f"文本: {chunk_rewrite.text}")
    result_rewrite = resolver.resolve(chunk_rewrite)
    print_result(result_rewrite)
    print(f"\n模式: {result_rewrite.mode} (覆盖率={result_rewrite.coverage:.2%}, 冲突率={result_rewrite.conflict:.2%})")
    
    # 测试文本：低覆盖率（可能触发 alias_only 或 skip 模式）
    chunk_low = ChunkMetadata(
        id="test_doc:4",
        doc_id="test_doc",
        text="这是一个简单的测试文本。它包含一些基本内容。文本内容相对简单，没有复杂的指代关系。这种情况通常不会触发重写模式。",
        chunk_index=4,
        sentence_ids=["test_doc:s0", "test_doc:s1"],
        sentence_count=2,
        window_start=0,
        window_end=1,
        build_version="test_001"
    )
    
    print_step(0, "测试低覆盖率场景", f"文本: {chunk_low.text}")
    result_low = resolver.resolve(chunk_low)
    print_result(result_low)
    print(f"\n模式: {result_low.mode} (覆盖率={result_low.coverage:.2%}, 冲突率={result_low.conflict:.2%})")
    
    print(f"\n✓ 测试通过: 决策模式测试完成")


def test_coref_no_mentions():
    """测试无提及场景（输出每一步）"""
    print("\n" + "="*80)
    print("测试: 无提及场景")
    print("="*80)
    
    resolver = CoreferenceResolver()
    
    chunk = ChunkMetadata(
        id="test_doc:5",
        doc_id="test_doc",
        text="这是一个没有代词和指代的测试文本。文本内容直接描述了主题。没有需要消解的指代关系。",
        chunk_index=5,
        sentence_ids=["test_doc:s0", "test_doc:s1", "test_doc:s2"],
        sentence_count=3,
        window_start=0,
        window_end=2,
        build_version="test_001"
    )
    
    print_step(0, "输入检查", f"Chunk ID: {chunk.id}\n文本: {chunk.text}")
    
    result = resolver.resolve(chunk)
    
    print_result(result)
    
    # 断言：应该返回 skip 模式
    assert result.mode == "skip", "无提及应该返回 skip 模式"
    assert result.coverage == 0.0, "无提及时覆盖率应该为 0"
    assert len(result.alias_map) == 0, "无提及时别名映射应该为空"
    
    print(f"\n✓ 测试通过: 无提及场景处理正确")


def test_coref_skip_noise():
    """测试噪声过滤（输出每一步）"""
    print("\n" + "="*80)
    print("测试: 噪声过滤（短文本、表格、代码块）")
    print("="*80)
    
    resolver = CoreferenceResolver()
    
    # 测试短文本（使用 model_construct 绕过验证，因为这是测试边界情况）
    chunk_short = ChunkMetadata.model_construct(
        id="test_doc:6",
        doc_id="test_doc",
        text="短文本。",
        chunk_index=6,
        sentence_ids=["test_doc:s0"],
        sentence_count=1,
        window_start=0,
        window_end=0,
        build_version="test_001"
    )
    
    print_step(0, "测试短文本过滤", f"文本: {chunk_short.text}")
    result_short = resolver.resolve(chunk_short)
    print_result(result_short)
    assert result_short.mode == "skip", "短文本应该被跳过"
    
    # 测试表格标记
    chunk_table = ChunkMetadata(
        id="test_doc:7",
        doc_id="test_doc",
        text="| 列1 | 列2 | 列3 | 列4 | 列5 |\n|-----|-----|-----|-----|-----|\n| 值1 | 值2 | 值3 | 值4 | 值5 |",
        chunk_index=7,
        sentence_ids=["test_doc:s0"],
        sentence_count=1,
        window_start=0,
        window_end=0,
        build_version="test_001"
    )
    
    print_step(0, "测试表格过滤", f"文本: {chunk_table.text[:50]}...")
    result_table = resolver.resolve(chunk_table)
    print_result(result_table)
    assert result_table.mode == "skip", "表格应该被跳过"
    
    # 测试代码块
    chunk_code = ChunkMetadata(
        id="test_doc:8",
        doc_id="test_doc",
        text="这是一个代码示例：```python\ndef hello():\n    print('Hello')\n```",
        chunk_index=8,
        sentence_ids=["test_doc:s0"],
        sentence_count=1,
        window_start=0,
        window_end=0,
        build_version="test_001"
    )
    
    print_step(0, "测试代码块过滤", f"文本: {chunk_code.text[:50]}...")
    result_code = resolver.resolve(chunk_code)
    print_result(result_code)
    assert result_code.mode == "skip", "代码块应该被跳过"
    
    print(f"\n✓ 测试通过: 噪声过滤正常")


def test_coref_demonstrative():
    """测试指示词消解（该、此、其等）"""
    print("\n" + "="*80)
    print("测试: 指示词消解")
    print("="*80)
    
    resolver = CoreferenceResolver()
    
    chunk = ChunkMetadata(
        id="test_doc:9",
        doc_id="test_doc",
        text="机器学习是人工智能的核心技术。该方法通过算法从数据中学习模式。此技术已经在多个领域得到应用，其发展前景非常广阔。",
        chunk_index=9,
        sentence_ids=["test_doc:s0", "test_doc:s1", "test_doc:s2", "test_doc:s3"],
        sentence_count=4,
        window_start=0,
        window_end=3,
        build_version="test_001"
    )
    
    print_step(0, "输入检查", f"Chunk ID: {chunk.id}\n文本: {chunk.text}")
    
    result = resolver.resolve(chunk)
    
    print_result(result)
    
    # 断言：应该检测到指示词
    demonstrative_mentions = [m for m in result.matches if m.mention.type.value == "demonstrative"]
    assert len(demonstrative_mentions) > 0 or result.metrics.get("total_mentions", 0) > 0, "应该检测到指示词或提及"
    
    print(f"\n✓ 测试通过: 指示词消解正常")


def test_coref_complex_scenario():
    """测试复杂场景（多种指代类型混合）"""
    print("\n" + "="*80)
    print("测试: 复杂场景（多种指代类型）")
    print("="*80)
    
    resolver = CoreferenceResolver()
    
    chunk = ChunkMetadata(
        id="test_doc:10",
        doc_id="test_doc",
        text="图神经网络（Graph Neural Network, GNN）是一种处理图结构数据的深度学习模型。GNN 通过消息传递机制学习节点表示。该模型在社交网络分析、推荐系统等领域有广泛应用。它能够捕捉节点之间的复杂关系。",
        chunk_index=10,
        sentence_ids=["test_doc:s0", "test_doc:s1", "test_doc:s2", "test_doc:s3"],
        sentence_count=4,
        window_start=0,
        window_end=3,
        build_version="test_001"
    )
    
    print_step(0, "输入检查", f"Chunk ID: {chunk.id}\n文本: {chunk.text}")
    
    result = resolver.resolve(chunk)
    
    print_result(result)
    
    # 断言：应该检测到多种类型的提及
    assert result.metrics.get("total_mentions", 0) > 0, "应该检测到提及"
    
    print(f"\n✓ 测试通过: 复杂场景处理正常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

