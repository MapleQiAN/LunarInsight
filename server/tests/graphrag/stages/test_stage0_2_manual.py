"""
手动联调测试：Stage 0 → 1 → 2

目的：允许输入自定义测试文本，按顺序运行
- 阶段 0: 篇章切分
- 阶段 1: 指代消解
- 阶段 2: 实体链接
并在控制台详细输出每一步的中间结果，便于观察与调试。

运行方式:
1) 作为 pytest 用例（推荐观察输出）:
   pytest tests/graphrag/stages/test_stage0_2_manual.py -v -s
   # 使用环境变量传入自定义文本
   $env:STAGE_TEST_TEXT="你的长文本..."
   $env:DOC_ID="doc_test_001"
   $env:BUILD_VERSION="manual_build_001"
   $env:MAX_CHUNKS="3"
   pytest tests/graphrag/stages/test_stage0_2_manual.py -v -s

2) 作为脚本直接运行（Windows PowerShell 示例）:
   python server/tests/graphrag/stages/test_stage0_2_manual.py --text "你的长文本..." --doc-id "doc_test_001" --build-version "manual_build_001" --max-chunks 3
"""

import os
import sys
import argparse
import logging
from typing import List, Dict, Any
from pathlib import Path

# 添加项目根目录到路径（与现有单测一致）
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from graphrag.stages import SemanticChunker, CoreferenceResolver, EntityLinker  # type: ignore
from graphrag.models.chunk import ChunkMetadata  # type: ignore


# 配置日志以显示详细步骤（INFO 即可，算法内部 DEBUG 需要按需开启）
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(name)s - %(message)s",
)


def _print_section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _preview(text: str, limit: int = 200) -> str:
    return text[:limit] + ("..." if len(text) > limit else "")


def _print_stage0_output(chunks: List[ChunkMetadata]):
    _print_section("阶段 0: 篇章切分 输出")
    print(f"Chunk 数量: {len(chunks)}")
    for ch in chunks:
        print(f"\n- Chunk ID: {ch.id}")
        print(f"  文档: {ch.doc_id} | 序号: {ch.chunk_index} | 句子数: {ch.sentence_count} "
              f"| 窗口: [{ch.window_start}, {ch.window_end}]")
        print(f"  文本预览: { _preview(ch.text, 180) }")
        if ch.sentence_ids:
            print(f"  句子IDs: {', '.join(ch.sentence_ids[:6])}{' ...' if len(ch.sentence_ids) > 6 else ''}")


def _print_stage1_output(chunk: ChunkMetadata, coref_result):
    _print_section(f"阶段 1: 指代消解 输出 | Chunk {chunk.id}")
    print(f"模式: {coref_result.mode}")
    print(f"覆盖率: {coref_result.coverage:.2%} | 冲突率: {coref_result.conflict:.2%}")
    print(f"别名映射数: {len(coref_result.alias_map)} | 匹配数: {len(getattr(coref_result, 'matches', []) or [])}")
    if coref_result.alias_map:
        print("别名映射:")
        for surface, canonical in coref_result.alias_map.items():
            print(f"  '{surface}' → '{canonical}'")
    if coref_result.resolved_text:
        print(f"替换后文本预览: { _preview(coref_result.resolved_text, 200) }")


def _print_stage2_output(chunk: ChunkMetadata, entities: List[Dict[str, Any]]):
    _print_section(f"阶段 2: 实体链接 输出 | Chunk {chunk.id}")
    print(f"实体条目数: {len(entities)}")
    if not entities:
        return
    for i, ent in enumerate(entities, 1):
        # 尽量兼容可能的返回字段
        concept_id = ent.get("concept_id")
        concept_name = ent.get("concept_name") or ent.get("name") or ent.get("canonical") or ""
        mention_text = ent.get("mention_text") or ent.get("mention") or ""
        confidence = ent.get("confidence")
        is_nil = ent.get("is_nil")
        is_review = ent.get("is_review")
        match_type = ent.get("match_type")
        score = ent.get("score")
        print(f"- 实体 {i}: '{mention_text}' → '{concept_name}' "
              f"(concept_id={concept_id}, confidence={confidence}, is_nil={is_nil}, is_review={is_review}, "
              f"match_type={match_type}, score={score})")


def run_manual(text: str, doc_id: str, build_version: str, max_chunks: int = 3):
    """运行 stage0-2 并详细打印每步输出"""
    _print_section("输入信息")
    print(f"Doc ID: {doc_id}")
    print(f"Build Version: {build_version}")
    print(f"原始文本长度: {len(text)}")
    print(f"文本预览: { _preview(text, 300) }")

    # 阶段 0: 篇章切分
    chunker = SemanticChunker()
    chunks = chunker.split(doc_id=doc_id, text=text, build_version=build_version)
    if max_chunks > 0:
        chunks = chunks[:max_chunks]
    _print_stage0_output(chunks)

    # 阶段 1 & 2
    coref = CoreferenceResolver()
    linker = EntityLinker()

    for ch in chunks:
        # Stage1: 指代消解
        coref_result = coref.resolve(ch)
        _print_stage1_output(ch, coref_result)
        # 回填到 Chunk，以便 Stage2 使用
        ch.resolved_text = coref_result.resolved_text
        ch.coreference_aliases = coref_result.alias_map
        ch.coref_mode = coref_result.mode

        # Stage2: 实体链接
        try:
            entities = linker.link_and_extract(ch)
        except Exception as e:
            # EntityLinker 依赖外部服务/配置时，避免直接中断，打印错误并继续
            logging.getLogger("test.stage0_2").error(f"Stage2 执行异常: {e}")
            entities = []
        _print_stage2_output(ch, entities)


def test_manual_input_text():
    """pytest 入口：支持环境变量输入自定义文本"""
    text = os.environ.get("STAGE_TEST_TEXT") or (
        "人工智能（Artificial Intelligence, AI）是一门研究如何让机器表现出智能行为的学科。"
        "它在自然语言处理、计算机视觉、推荐系统等领域有广泛应用。该技术正加速改变各行各业。"
        "Transformer 是一种基于自注意力机制的神经网络架构，它实现了并行化训练。"
    )
    doc_id = os.environ.get("DOC_ID", "manual_doc_001")
    build_version = os.environ.get("BUILD_VERSION", "manual_build_001")
    max_chunks_env = os.environ.get("MAX_CHUNKS", "3")
    try:
        max_chunks = int(max_chunks_env)
    except Exception:
        max_chunks = 3

    run_manual(text=text, doc_id=doc_id, build_version=build_version, max_chunks=max_chunks)


def _parse_args():
    parser = argparse.ArgumentParser(description="手动联调测试：stage0-2")
    parser.add_argument("--text", type=str, required=False, default=None, help="输入测试文本")
    parser.add_argument("--doc-id", type=str, required=False, default="manual_doc_001", help="文档ID")
    parser.add_argument("--build-version", type=str, required=False, default="manual_build_001", help="构建版本")
    parser.add_argument("--max-chunks", type=int, required=False, default=3, help="最多处理的Chunk数量（>0生效）")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    text_cli = args.text or os.environ.get("STAGE_TEST_TEXT")
    if not text_cli:
        print("未提供 --text 或环境变量 STAGE_TEST_TEXT，使用默认示例文本。")
        text_cli = (
            "人工智能（Artificial Intelligence, AI）是一门研究如何让机器表现出智能行为的学科。"
            "它在自然语言处理、计算机视觉、推荐系统等领域有广泛应用。该技术正加速改变各行各业。"
            "Transformer 是一种基于自注意力机制的神经网络架构，它实现了并行化训练。"
        )
    run_manual(
        text=text_cli,
        doc_id=args.doc_id,
        build_version=args.build_version,
        max_chunks=args.max_chunks,
    )


