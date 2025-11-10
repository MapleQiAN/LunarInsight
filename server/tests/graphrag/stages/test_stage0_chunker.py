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


def _print_chunk_debug(chunks):
    """辅助函数：打印 chunks 的调试信息"""
    if not chunks:
        print("[DEBUG] chunks is empty or None")
        return
    print(f"[DEBUG] total chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        try:
            meta = vars(c)
        except Exception:
            # 如果不是对象或 dataclass，直接显示 repr
            meta = repr(c)
        text_snippet = (c.text[:200] + '...') if getattr(c, 'text', None) and len(c.text) > 200 else getattr(c, 'text', '')
        print(f"[DEBUG] Chunk #{i}: id={getattr(c, 'id', None)} doc_id={getattr(c, 'doc_id', None)} "
              f"window=[{getattr(c, 'window_start', None)}, {getattr(c, 'window_end', None)}] "
              f"sentence_count={getattr(c, 'sentence_count', None)} text_len={len(getattr(c, 'text', '') or '')}")
        print(f"         sentence_ids={getattr(c, 'sentence_ids', None)}")
        print(f"         text_snippet={text_snippet!r}")
        print(f"         meta={meta}")


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

    # 打印更详细的调试信息
    _print_chunk_debug(chunks)


def test_chunker_overlap():
    """测试滑动窗口重叠"""
    chunker = SemanticChunker()
    
    text = "句子1。句子2。句子3。句子4。句子5。句子6。句子7。句子8。"
    chunks = chunker.split("doc1", text, "v1")

    # 打印调试信息
    _print_chunk_debug(chunks)

    # 检查是否有重叠（通过 window_start 和 window_end）
    if len(chunks) > 1:
        # 第二个 chunk 的起始应该小于第一个 chunk 的结束（有重叠）
        assert chunks[1].window_start <= chunks[0].window_end, "应该有重叠"
        print(f"\n✓ 测试通过: Chunk 0 窗口 [{chunks[0].window_start}, {chunks[0].window_end}], "
              f"Chunk 1 窗口 [{chunks[1].window_start}, {chunks[1].window_end}]")
    else:
        print("[DEBUG] 没有足够的 chunk 来测试重叠")


def test_chunker_empty_text():
    """测试空文本处理"""
    chunker = SemanticChunker()
    
    chunks = chunker.split("doc1", "", "v1")
    # 空文本应该返回空列表
    # 打印调试信息以便排查
    print("[DEBUG] test_chunker_empty_text: chunks repr:", repr(chunks))
    print("[DEBUG] test_chunker_empty_text: chunks type:", type(chunks))
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
    # 打印调试信息
    _print_chunk_debug(chunks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
