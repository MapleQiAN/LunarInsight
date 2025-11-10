"""
阶段 2: 实体链接测试（详细调试信息）

运行方式:
    pytest tests/graphrag/stages/test_stage2_entity_linker.py -v -s
    pytest tests/graphrag/stages/test_stage2_entity_linker.py::test_entity_linking_basic -v -s
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import types
import pytest

from graphrag.stages.stage2_entity_linker import EntityLinker
from graphrag.models.chunk import ChunkMetadata

# 配置日志为 DEBUG，显示 Stage2 细粒度调试日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(name)s - %(message)s"
)


def print_step(step_num: int, step_name: str, details: str = ""):
    print(f"\n{'='*72}")
    print(f"步骤 {step_num}: {step_name}")
    print(f"{'='*72}")
    if details:
        print(details)


def _install_test_mocks(monkeypatch):
    """
    安装用于稳定单测的轻量 Mock（避免依赖外部 Neo4j/Embedding 环境）。
    """
    # 1) mock settings（只提供 Stage2 用到的字段）
    class _Settings:
        enable_vector_search = False  # 关闭向量检索，简化测试
        embedding_model = "test-embedding"
        vector_search_threshold = 0.2
        allowed_node_types = ["Concept", "Person", "Organization", "Method", "Tool", "Metric"]
        allowed_relations = ["MENTIONS", "DERIVES_FROM", "SIMILAR_TO", "HAS_MEMBER"]

    from graphrag.stages import stage2_entity_linker as s2
    monkeypatch.setattr(s2, "settings", _Settings, raising=True)

    # 2) mock AI Provider 配置，强制使用 provider=mock 避免初始化第三方依赖
    class _ConfigService:
        @staticmethod
        def get_ai_provider_config():
            return {
                "provider": "mock",
                "api_key": "",
                "model": "gpt-test",
                "base_url": ""
            }

    monkeypatch.setattr(s2, "config_service", _ConfigService, raising=True)

    # 3) mock embedding 接口
    def _fake_get_embedding(text: str, model: str = "test-embedding"):
        # 返回一个非零短向量，语义不重要，只要是稳定可用即可
        return [0.1, 0.2, 0.3, 0.4]

    def _fake_cosine_similarity(vec_a, vec_b):
        # 简化余弦相似度（非关键路径，因为我们关闭了向量检索）
        # 保持在 [0,1] 之间，避免异常
        return 0.5

    monkeypatch.setattr(s2, "get_embedding", _fake_get_embedding, raising=True)
    monkeypatch.setattr(s2, "cosine_similarity", _fake_cosine_similarity, raising=True)

    # 4) mock neo4j_client.execute_query —— 根据 query 语义返回固定数据
    class _Neo4jClientMock:
        @staticmethod
        def execute_query(query: str, params: dict = None):
            q = " ".join(query.split()).lower()
            params = params or {}

            # a) 加载反馈数据时查询 UnlinkRequest —— 返回空，避免动态阈值变化
            if "match (f:unlinkrequest)" in q:
                return []

            # b) 名称/别名检索（_retrieve_by_name_or_alias）
            if "match (c:concept)" in q and "return c.id as concept_id" in q and "coalesce(c.aliases" in q:
                name = (params or {}).get("name", "").lower()
                # 准备两个概念：'人工智能'（主），'人工智慧'（相近）
                concepts = []
                if name in ("人工智能", "ai"):
                    concepts.append({
                        "concept_id": "c_ai",
                        "concept_name": "人工智能",
                        "description": "人工智能（AI）是一种模拟人类智能的技术。",
                        "domain": "ai",
                        "aliases": ["AI", "Artificial Intelligence"],
                        "labels": ["Concept"]
                    })
                if name in ("人工智慧",):
                    concepts.append({
                        "concept_id": "c_ai_alt",
                        "concept_name": "人工智慧",
                        "description": "与人工智能含义接近的术语。",
                        "domain": "ai",
                        "aliases": [],
                        "labels": ["Concept"]
                    })
                return concepts[:10]

            # c) BM25（简化 CONTAINS 检索）
            if "order by" in q and "limit $limit" in q and "contains" in q:
                mention = (params or {}).get("mention", "")
                return [
                    {
                        "concept_id": "c_ai",
                        "concept_name": "人工智能",
                        "description": "人工智能（AI）是一种模拟人类智能的技术。",
                        "domain": "ai",
                        "aliases": ["AI"],
                        "labels": ["Concept"]
                    },
                    {
                        "concept_id": "c_ai_alt",
                        "concept_name": "人工智慧",
                        "description": "与人工智能含义接近的术语。",
                        "domain": "ai",
                        "aliases": [],
                        "labels": ["Concept"]
                    },
                ]

            # d) 候选 embedding 查询（被 settings.enable_vector_search=False 绕过，一般不触发）
            if "match (c:concept {id: $concept_id})" in q and "return c.embedding as embedding" in q:
                return [{"embedding": [0.1, 0.2, 0.3, 0.4]}]

            # e) 先验频次（度）
            if "match (c:concept {name: $name})-[r]-()" in q:
                name = (params or {}).get("name", "")
                if name == "人工智能":
                    return [{"degree": 50}]  # 高频
                if name == "人工智慧":
                    return [{"degree": 10}]  # 低频
                return [{"degree": 0}]

            # f) 图一致性（主题/Chunk 主题）—— 返回空列表，走默认中等分路径
            if "match (c:concept {id: $concept_id})<-[:has_member]-(t:theme)" in q:
                return []
            if "match (chunk:chunk {id: $chunk_id})-[:mentions]->(concept:concept)" in q:
                return []

            # g) 向量索引（不会触发，因为关闭了 enable_vector_search）
            if "call db.index.vector.querynodes" in q:
                return []

            # 默认空
            return []

    monkeypatch.setattr(s2, "neo4j_client", _Neo4jClientMock, raising=True)


def test_entity_linking_basic(monkeypatch):
    """
    测试基本实体链接流程（详细输出每一步调试信息）。

    目标：验证多路召回 + 精排 + NIL 判断 + 阈值决策整体闭环；
         在关闭向量检索的情况下，依赖别名/精确/BM25 召回与规则特征完成排序。
    """
    print("\n" + "=" * 80)
    print("测试: 阶段2 实体链接（基础流程）")
    print("=" * 80)

    # 安装稳定的轻量 Mock
    _install_test_mocks(monkeypatch)

    print_step(0, "初始化 EntityLinker")
    linker = EntityLinker()

    # 放宽 Concept 类型接受阈值，确保本例能通过自动接受（而非人工复核）
    linker.type_thresholds["Concept"] = {"accept": 0.75, "review": 0.6}

    # 构造测试 Chunk
    text = "人工智能（AI）是一种模拟人类智能的技术。AI 在医疗等领域有应用。"
    chunk = ChunkMetadata(
        id="test_doc:0",
        doc_id="test_doc",
        text=text,
        resolved_text=text,           # 模拟 stage1 rewrite 后文本
        coref_mode="rewrite",
        coreference_aliases={"AI": "人工智能"},
        section_path="Introduction > AI > Healthcare",
        chunk_index=0,
        sentence_ids=["test_doc:s0", "test_doc:s1"],
        sentence_count=2,
        window_start=0,
        window_end=1,
        build_version="test_002"
    )

    print_step(1, "输入检查", f"Chunk ID: {chunk.id}\n文本: {chunk.text}\n别名映射: {chunk.coreference_aliases}")

    print_step(2, "执行 link_and_extract")
    entities = linker.link_and_extract(chunk)

    print_step(3, "输出结果检查", f"实体数: {len(entities)}\n实体明细:\n" + "\n".join([
        f"- name={e['concept_name']}, id={e['concept_id']}, conf={e['confidence']:.3f}, "
        f"mention='{e['mention_text']}', is_nil={e['is_nil']}, is_review={e['is_review']}, "
        f"evidence={e.get('evidence')}"
        for e in entities
    ]))

    # 断言
    assert isinstance(entities, list), "应该返回实体列表"
    assert len(entities) >= 1, "应该至少识别到一个实体"

    # 期待优先链接到 '人工智能'
    top = entities[0]
    assert top["concept_name"] in ("人工智能", "AI"), "Top 应链接到 '人工智能'（或同义别名）"
    assert top["is_nil"] is False, "Top 不应为 NIL"
    assert 0.0 <= top["confidence"] <= 1.0, "置信度应在 [0,1]"

    print(f"\n✓ 测试通过: 阶段2 实体链接（基础流程）正常")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


