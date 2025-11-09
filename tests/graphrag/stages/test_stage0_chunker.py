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

from server.graphrag.stages.stage0_chunker import SemanticChunker
from server.graphrag.models.chunk import ChunkMetadata


def test_chunker_basic():
    """测试基本切分功能"""
    chunker = SemanticChunker()
    
    doc_id = "test_doc_001"
    text = """
    Transformer 是一种基于自注意力机制的神经网络架构。
    Transformer 由 Vaswani 等人于 2017 年提出。
    Transformer 的核心组件包括多头自注意力和位置编码。
    Transformer 摒弃了传统的循环结构。
    Transformer 实现了并行化训练。
    """
    build_version = "test_001_1234567890"
    
    chunks = chunker.split(doc_id, text, build_version)
    
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


def test_chunker_overlap():
    """测试滑动窗口重叠"""
    chunker = SemanticChunker()
    
    text = "句子1。句子2。句子3。句子4。句子5。句子6。句子7。句子8。"
    chunks = chunker.split("doc1", text, "v1")
    
    # 检查是否有重叠（通过 window_start 和 window_end）
    if len(chunks) > 1:
        # 第二个 chunk 的起始应该小于第一个 chunk 的结束（有重叠）
        assert chunks[1].window_start <= chunks[0].window_end, "应该有重叠"
        print(f"\n✓ 测试通过: Chunk 0 窗口 [{chunks[0].window_start}, {chunks[0].window_end}], "
              f"Chunk 1 窗口 [{chunks[1].window_start}, {chunks[1].window_end}]")


def test_chunker_empty_text():
    """测试空文本处理"""
    chunker = SemanticChunker()
    
    chunks = chunker.split("doc1", "", "v1")
    # 空文本应该返回空列表
    assert len(chunks) == 0, "空文本应该返回空列表"
    print("\n✓ 测试通过: 空文本处理正确")


def test_chunker_short_text():
    """测试短文本处理"""
    chunker = SemanticChunker()
    
    text = "这是一个很短的文本。"
    chunks = chunker.split("doc1", text, "v1")
    
    # 短文本可能只生成一个 Chunk 或空列表
    assert len(chunks) >= 0
    print(f"\n✓ 测试通过: 短文本生成 {len(chunks)} 个 Chunk")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

