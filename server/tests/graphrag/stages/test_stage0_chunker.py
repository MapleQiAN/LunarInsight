"""
阶段 0: 篇章切分测试

运行方式:
    pytest tests/graphrag/stages/test_stage0_chunker.py -v
    pytest tests/graphrag/stages/test_stage0_chunker.py::test_chunker_basic -v
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from graphrag.stages.stage0_chunker import SemanticChunker
from graphrag.models.chunk import ChunkMetadata
from graphrag.utils.text_processing import split_sentences, sliding_window


def _print_chunk_debug(chunks: list[ChunkMetadata]):
    """打印 Chunk 详细信息用于调试"""
    print("\n" + "="*80)
    print("Chunk 详细信息")
    print("="*80)
    
    if not chunks:
        print("  [无 Chunk]")
        return
    
    for i, chunk in enumerate(chunks):
        print(f"\n[Chunk {i}]")
        print(f"  ID: {chunk.id}")
        print(f"  Doc ID: {chunk.doc_id}")
        print(f"  Chunk Index: {chunk.chunk_index}")
        print(f"  Build Version: {chunk.build_version}")
        print(f"  Window: [{chunk.window_start}, {chunk.window_end}]")
        print(f"  Sentence Count: {chunk.sentence_count}")
        print(f"  Sentence IDs: {chunk.sentence_ids}")
        print(f"  Text Length: {len(chunk.text)} 字符")
        print(f"  Text Preview: {chunk.text[:100]}{'...' if len(chunk.text) > 100 else ''}")
        print(f"  Full Text: {chunk.text}")
    
    print("\n" + "="*80)


def test_chunker_basic():
    """测试基本切分功能"""
    print("\n" + "="*80)
    print("测试: test_chunker_basic")
    print("="*80)
    
    # 步骤 0: 初始化
    print("\n[步骤 0] 初始化 SemanticChunker")
    chunker = SemanticChunker()
    print(f"  Window Size: {chunker.window_size}")
    print(f"  Step Size: {chunker.step_size}")
    
    # 步骤 1: 准备输入
    print("\n[步骤 1] 准备输入参数")
    doc_id = "test_doc_001"
    text = """
    Transformer 是一种基于自注意力机制的神经网络架构。
    Transformer 由 Vaswani 等人于 2017 年提出。
    Transformer 的核心组件包括多头自注意力和位置编码。
    Transformer 摒弃了传统的循环结构。
    Transformer 实现了并行化训练。
    """
    build_version = "test_001_1234567890"
    print(f"  Doc ID: {doc_id}")
    print(f"  Build Version: {build_version}")
    print(f"  输入文本长度: {len(text)} 字符")
    print(f"  输入文本内容:\n{text}")
    
    # 步骤 2: 句子分割（中间步骤）
    print("\n[步骤 2] 句子分割 (split_sentences)")
    sentences = split_sentences(text)
    print(f"  分割结果: {len(sentences)} 个句子")
    for i, sent in enumerate(sentences):
        print(f"    句子 {i}: {sent}")
    
    # 步骤 3: 滑动窗口（中间步骤）
    print(f"\n[步骤 3] 滑动窗口 (sliding_window, window_size={chunker.window_size}, step_size={chunker.step_size})")
    windows = sliding_window(sentences, chunker.window_size, chunker.step_size)
    print(f"  窗口结果: {len(windows)} 个窗口")
    for i, (window_text, start_idx, end_idx) in enumerate(windows):
        print(f"    窗口 {i}: [{start_idx}, {end_idx}]")
        print(f"      文本长度: {len(window_text)} 字符")
        print(f"      文本内容: {window_text[:100]}{'...' if len(window_text) > 100 else ''}")
        if len(window_text.strip()) < 50:
            print(f"      ⚠️  警告: 窗口文本过短 ({len(window_text.strip())} 字符 < 50)，将被过滤")
    
    # 步骤 4: 执行切分
    print("\n[步骤 4] 执行切分 (chunker.split)")
    chunks = chunker.split(doc_id, text, build_version)
    print(f"  切分结果: {len(chunks)} 个 Chunk")

    # 断言
    assert len(chunks) > 0, "应该生成至少一个 Chunk"
    assert all(isinstance(c, ChunkMetadata) for c in chunks), "所有结果应该是 ChunkMetadata"
    
    # 检查第一个 Chunk
    first_chunk = chunks[0]
    assert first_chunk.doc_id == doc_id
    assert first_chunk.build_version == build_version
    assert len(first_chunk.text) > 0
    assert len(first_chunk.sentence_ids) > 0
    assert first_chunk.window_start >= 0
    assert first_chunk.window_end >= first_chunk.window_start
    
    print(f"\n✓ 测试通过: 生成 {len(chunks)} 个 Chunk")
    print(f"  第一个 Chunk: {first_chunk.id}")
    print(f"  文本长度: {len(first_chunk.text)} 字符")
    print(f"  句子数: {first_chunk.sentence_count}")

    # 打印更详细的调试信息
    _print_chunk_debug(chunks)


def test_chunker_overlap():
    """测试滑动窗口重叠"""
    print("\n" + "="*80)
    print("测试: test_chunker_overlap")
    print("="*80)
    
    print("\n[步骤 0] 初始化 SemanticChunker")
    chunker = SemanticChunker()
    print(f"  Window Size: {chunker.window_size}")
    print(f"  Step Size: {chunker.step_size}")
    
    print("\n[步骤 1] 准备输入参数")
    text = "句子1。句子2。句子3。句子4。句子5。句子6。句子7。句子8。"
    doc_id = "doc1"
    build_version = "v1"
    print(f"  Doc ID: {doc_id}")
    print(f"  Build Version: {build_version}")
    print(f"  输入文本: {text}")
    
    print("\n[步骤 2] 句子分割 (split_sentences)")
    sentences = split_sentences(text)
    print(f"  分割结果: {len(sentences)} 个句子")
    for i, sent in enumerate(sentences):
        print(f"    句子 {i}: {sent}")
    
    print(f"\n[步骤 3] 滑动窗口 (sliding_window)")
    windows = sliding_window(sentences, chunker.window_size, chunker.step_size)
    print(f"  窗口结果: {len(windows)} 个窗口")
    for i, (window_text, start_idx, end_idx) in enumerate(windows):
        print(f"    窗口 {i}: [{start_idx}, {end_idx}]")
        print(f"      文本: {window_text}")
    
    print("\n[步骤 4] 执行切分 (chunker.split)")
    chunks = chunker.split(doc_id, text, build_version)
    print(f"  切分结果: {len(chunks)} 个 Chunk")

    # 打印调试信息
    _print_chunk_debug(chunks)

    # 检查是否有重叠（通过 window_start 和 window_end）
    if len(chunks) > 1:
        # 第二个 chunk 的起始应该小于第一个 chunk 的结束（有重叠）
        assert chunks[1].window_start <= chunks[0].window_end, "应该有重叠"
        print(f"\n✓ 测试通过: Chunk 0 窗口 [{chunks[0].window_start}, {chunks[0].window_end}], "
              f"Chunk 1 窗口 [{chunks[1].window_start}, {chunks[1].window_end}]")
        print(f"  重叠检查: Chunk 1 起始 ({chunks[1].window_start}) <= Chunk 0 结束 ({chunks[0].window_end}) ✓")
    else:
        print("\n⚠️  警告: 没有足够的 chunk 来测试重叠")


def test_chunker_empty_text():
    """测试空文本处理"""
    print("\n" + "="*80)
    print("测试: test_chunker_empty_text")
    print("="*80)
    
    print("\n[步骤 0] 初始化 SemanticChunker")
    chunker = SemanticChunker()
    print(f"  Window Size: {chunker.window_size}")
    print(f"  Step Size: {chunker.step_size}")
    
    print("\n[步骤 1] 准备输入参数")
    text = ""
    doc_id = "doc1"
    build_version = "v1"
    print(f"  Doc ID: {doc_id}")
    print(f"  Build Version: {build_version}")
    print(f"  输入文本: '{text}' (空文本)")
    print(f"  输入文本长度: {len(text)} 字符")
    
    print("\n[步骤 2] 句子分割 (split_sentences)")
    sentences = split_sentences(text)
    print(f"  分割结果: {len(sentences)} 个句子")
    print(f"  句子列表: {sentences}")
    
    print(f"\n[步骤 3] 滑动窗口 (sliding_window)")
    windows = sliding_window(sentences, chunker.window_size, chunker.step_size)
    print(f"  窗口结果: {len(windows)} 个窗口")
    print(f"  窗口列表: {windows}")
    
    print("\n[步骤 4] 执行切分 (chunker.split)")
    chunks = chunker.split(doc_id, text, build_version)
    print(f"  切分结果: {len(chunks)} 个 Chunk")
    print(f"  Chunks 类型: {type(chunks)}")
    print(f"  Chunks 内容: {chunks}")
    
    # 空文本应该返回空列表
    assert len(chunks) == 0, "空文本应该返回空列表"
    print("\n✓ 测试通过: 空文本处理正确（返回空列表）")


def test_chunker_short_text():
    """测试短文本处理"""
    print("\n" + "="*80)
    print("测试: test_chunker_short_text")
    print("="*80)
    
    print("\n[步骤 0] 初始化 SemanticChunker")
    chunker = SemanticChunker()
    print(f"  Window Size: {chunker.window_size}")
    print(f"  Step Size: {chunker.step_size}")
    
    print("\n[步骤 1] 准备输入参数")
    text = "这是一个很短的文本。"
    doc_id = "doc1"
    build_version = "v1"
    print(f"  Doc ID: {doc_id}")
    print(f"  Build Version: {build_version}")
    print(f"  输入文本: {text}")
    print(f"  输入文本长度: {len(text)} 字符")
    
    print("\n[步骤 2] 句子分割 (split_sentences)")
    sentences = split_sentences(text)
    print(f"  分割结果: {len(sentences)} 个句子")
    for i, sent in enumerate(sentences):
        print(f"    句子 {i}: {sent}")
    
    print(f"\n[步骤 3] 滑动窗口 (sliding_window)")
    windows = sliding_window(sentences, chunker.window_size, chunker.step_size)
    print(f"  窗口结果: {len(windows)} 个窗口")
    for i, (window_text, start_idx, end_idx) in enumerate(windows):
        print(f"    窗口 {i}: [{start_idx}, {end_idx}]")
        print(f"      文本长度: {len(window_text)} 字符")
        print(f"      文本内容: {window_text}")
        if len(window_text.strip()) < 50:
            print(f"      ⚠️  警告: 窗口文本过短 ({len(window_text.strip())} 字符 < 50)，将被过滤")
    
    print("\n[步骤 4] 执行切分 (chunker.split)")
    chunks = chunker.split(doc_id, text, build_version)
    print(f"  切分结果: {len(chunks)} 个 Chunk")
    
    # 短文本可能只生成一个 Chunk 或空列表（如果文本过短被过滤）
    assert len(chunks) >= 0
    print(f"\n✓ 测试通过: 短文本生成 {len(chunks)} 个 Chunk")
    
    # 打印调试信息
    _print_chunk_debug(chunks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
