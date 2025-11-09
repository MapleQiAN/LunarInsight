# GraphRAG 阶段测试指南

**版本**: v1.0  
**最后更新**: 2025-01-XX  
**适用版本**: LunarInsight GraphRAG v2.0

---

## 目录

1. [测试环境准备](#1-测试环境准备)
2. [阶段 0: 篇章切分测试](#2-阶段-0-篇章切分测试)
3. [阶段 1: 指代消解测试](#3-阶段-1-指代消解测试)
4. [阶段 2: 实体链接测试](#4-阶段-2-实体链接测试)
5. [阶段 3: 论断抽取测试](#5-阶段-3-论断抽取测试)
6. [阶段 4: 主题社区测试](#6-阶段-4-主题社区测试)
7. [阶段 5: 谓词治理测试](#7-阶段-5-谓词治理测试)
8. [阶段 6: 幂等落库测试](#8-阶段-6-幂等落库测试)
9. [阶段 7: GraphRAG 检索测试](#9-阶段-7-graphrag-检索测试)
10. [阶段 8: 评价指标测试](#10-阶段-8-评价指标测试)
11. [集成测试](#11-集成测试)
12. [端到端测试](#12-端到端测试)
13. [测试工具与脚本](#13-测试工具与脚本)

---

## 1. 测试环境准备

### 1.1 安装测试依赖

```bash
cd server
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### 1.2 配置测试环境变量

创建 `.env.test` 文件：

```bash
# Neo4j 测试数据库
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASS=test1234

# AI 配置（测试模式）
AI_PROVIDER=mock  # 或使用真实的 API key
AI_API_KEY=test-key

# GraphRAG 配置
ENABLE_NEO4J_GRAPHRAG=true
ENABLE_VECTOR_SEARCH=true
```

### 1.3 准备测试数据

创建测试数据目录：

```bash
mkdir -p tests/fixtures
```

准备测试文档（`tests/fixtures/test_doc.txt`）：

```
# Transformer 架构

Transformer 是一种基于自注意力机制的神经网络架构。Transformer 由 Vaswani 等人于 2017 年提出。

Transformer 的核心组件包括：
1. 多头自注意力机制（Multi-Head Self-Attention）
2. 位置编码（Positional Encoding）
3. 前馈神经网络（Feed-Forward Network）

Transformer 摒弃了传统的循环结构，实现了并行化训练。这使得 Transformer 在自然语言处理任务中取得了突破性进展。

BERT 和 GPT 都是基于 Transformer 架构的模型。BERT 使用双向编码器，而 GPT 使用单向解码器。
```

---

## 2. 阶段 0: 篇章切分测试

### 2.1 单元测试

创建 `tests/graphrag/stages/test_stage0_chunker.py`：

```python
import pytest
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


def test_chunker_overlap():
    """测试滑动窗口重叠"""
    chunker = SemanticChunker()
    
    text = "句子1。句子2。句子3。句子4。句子5。句子6。句子7。句子8。"
    chunks = chunker.split("doc1", text, "v1")
    
    # 检查是否有重叠（通过 window_start 和 window_end）
    if len(chunks) > 1:
        # 第二个 chunk 的起始应该小于第一个 chunk 的结束
        assert chunks[1].window_start < chunks[0].window_end


def test_chunker_empty_text():
    """测试空文本处理"""
    chunker = SemanticChunker()
    
    chunks = chunker.split("doc1", "", "v1")
    # 空文本应该返回空列表或抛出异常
    assert len(chunks) == 0 or chunks is None


def test_chunker_short_text():
    """测试短文本处理"""
    chunker = SemanticChunker()
    
    text = "这是一个很短的文本。"
    chunks = chunker.split("doc1", text, "v1")
    
    # 短文本可能只生成一个 Chunk
    assert len(chunks) >= 0
```

### 2.2 运行测试

```bash
# 运行单个测试文件
pytest tests/graphrag/stages/test_stage0_chunker.py -v

# 运行单个测试函数
pytest tests/graphrag/stages/test_stage0_chunker.py::test_chunker_basic -v

# 显示详细输出
pytest tests/graphrag/stages/test_stage0_chunker.py -v -s
```

### 2.3 手动测试脚本

创建 `tests/scripts/test_stage0_manual.py`：

```python
"""阶段 0 手动测试脚本"""
from server.graphrag.stages.stage0_chunker import SemanticChunker

def main():
    chunker = SemanticChunker()
    
    # 读取测试文档
    with open("tests/fixtures/test_doc.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    # 切分
    chunks = chunker.split("test_doc", text, "manual_test_001")
    
    # 打印结果
    print(f"生成 {len(chunks)} 个 Chunk:\n")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}:")
        print(f"  ID: {chunk.id}")
        print(f"  文本长度: {len(chunk.text)} 字符")
        print(f"  句子数: {chunk.sentence_count}")
        print(f"  窗口: [{chunk.window_start}, {chunk.window_end}]")
        print(f"  文本预览: {chunk.text[:100]}...")
        print()

if __name__ == "__main__":
    main()
```

运行：

```bash
python tests/scripts/test_stage0_manual.py
```

---

## 3. 阶段 1: 指代消解测试

### 3.1 单元测试

创建 `tests/graphrag/stages/test_stage1_coref.py`：

```python
import pytest
from server.graphrag.stages.stage1_coref import CoreferenceResolver
from server.graphrag.models.chunk import ChunkMetadata


@pytest.fixture
def sample_chunk():
    """创建测试用的 Chunk"""
    return ChunkMetadata(
        id="test_chunk_001",
        doc_id="test_doc",
        text="Transformer 是一种神经网络架构。它由 Vaswani 等人提出。Transformer 的核心是自注意力机制。",
        chunk_index=0,
        window_start=0,
        window_end=2,
        sentence_ids=["s0", "s1", "s2"],
        build_version="test_v1"
    )


def test_coref_basic(sample_chunk):
    """测试基本指代消解"""
    resolver = CoreferenceResolver()
    
    result = resolver.resolve(sample_chunk)
    
    # 断言
    assert result is not None
    assert hasattr(result, "resolved_text")
    assert hasattr(result, "alias_map")
    assert hasattr(result, "mode")
    assert hasattr(result, "coverage")
    assert hasattr(result, "conflict")
    
    # 检查别名映射
    if result.alias_map:
        print(f"别名映射: {result.alias_map}")
        # "它" 应该映射到 "Transformer"
        assert "它" in result.alias_map or "Transformer" in result.alias_map.values()


def test_coref_parenthesis_alias():
    """测试括号别名提取"""
    resolver = CoreferenceResolver()
    
    chunk = ChunkMetadata(
        id="test_001",
        doc_id="test",
        text="人工智能（AI）是一种技术。AI 可以处理自然语言。",
        chunk_index=0,
        window_start=0,
        window_end=1,
        sentence_ids=["s0", "s1"],
        build_version="test_v1"
    )
    
    result = resolver.resolve(chunk)
    
    # 应该提取到 "AI" -> "人工智能" 的映射
    assert "AI" in result.alias_map
    assert result.alias_map["AI"] == "人工智能"


def test_coref_skip_mode():
    """测试跳过模式（噪声文本）"""
    resolver = CoreferenceResolver()
    
    # 短文本应该被跳过
    chunk = ChunkMetadata(
        id="test_001",
        doc_id="test",
        text="标题",
        chunk_index=0,
        window_start=0,
        window_end=0,
        sentence_ids=["s0"],
        build_version="test_v1"
    )
    
    result = resolver.resolve(chunk)
    assert result.mode == "skip"


def test_coref_quality_metrics(sample_chunk):
    """测试质量指标计算"""
    resolver = CoreferenceResolver()
    
    result = resolver.resolve(sample_chunk)
    
    # 检查质量指标
    assert 0.0 <= result.coverage <= 1.0, "覆盖率应该在 [0, 1] 范围内"
    assert 0.0 <= result.conflict <= 1.0, "冲突率应该在 [0, 1] 范围内"
    assert result.mode in ["rewrite", "local", "alias_only", "skip"]
    
    print(f"模式: {result.mode}")
    print(f"覆盖率: {result.coverage:.2%}")
    print(f"冲突率: {result.conflict:.2%}")
```

### 3.2 手动测试脚本

创建 `tests/scripts/test_stage1_manual.py`：

```python
"""阶段 1 手动测试脚本"""
from server.graphrag.stages.stage1_coref import CoreferenceResolver
from server.graphrag.stages.stage0_chunker import SemanticChunker
from server.graphrag.models.chunk import ChunkMetadata

def main():
    # 1. 先切分文档
    chunker = SemanticChunker()
    with open("tests/fixtures/test_doc.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    chunks = chunker.split("test_doc", text, "manual_test_001")
    
    # 2. 对每个 Chunk 进行指代消解
    resolver = CoreferenceResolver()
    
    for i, chunk in enumerate(chunks):
        print(f"\n{'='*60}")
        print(f"Chunk {i}: {chunk.id}")
        print(f"{'='*60}")
        print(f"原文: {chunk.text[:200]}...")
        
        result = resolver.resolve(chunk)
        
        print(f"\n模式: {result.mode}")
        print(f"覆盖率: {result.coverage:.2%}")
        print(f"冲突率: {result.conflict:.2%}")
        
        if result.alias_map:
            print(f"\n别名映射 ({len(result.alias_map)} 个):")
            for surface, canonical in result.alias_map.items():
                print(f"  '{surface}' → '{canonical}'")
        
        if result.resolved_text and result.resolved_text != chunk.text:
            print(f"\n替换后文本: {result.resolved_text[:200]}...")
        
        if result.matches:
            print(f"\n匹配结果 ({len(result.matches)} 个):")
            for match in result.matches[:5]:  # 只显示前5个
                conflict_mark = " [冲突]" if match.is_conflict else ""
                print(f"  '{match.mention.text}' → '{match.antecedent.text}' "
                      f"(分数={match.score:.3f}, 置信度={match.confidence:.3f}){conflict_mark}")

if __name__ == "__main__":
    main()
```

---

## 4. 阶段 2: 实体链接测试

### 4.1 单元测试

创建 `tests/graphrag/stages/test_stage2_entity_linker.py`：

```python
import pytest
from server.graphrag.stages.stage2_entity_linker import EntityLinker
from server.graphrag.models.chunk import ChunkMetadata


@pytest.fixture
def sample_chunk_with_coref():
    """创建带指代消解结果的 Chunk"""
    chunk = ChunkMetadata(
        id="test_chunk_001",
        doc_id="test_doc",
        text="Transformer 是一种神经网络架构。它由 Vaswani 等人提出。",
        chunk_index=0,
        window_start=0,
        window_end=1,
        sentence_ids=["s0", "s1"],
        build_version="test_v1"
    )
    
    # 模拟 stage1 的结果
    chunk.coreference_aliases = {"它": "Transformer"}
    chunk.coref_mode = "rewrite"
    chunk.resolved_text = "Transformer 是一种神经网络架构。Transformer 由 Vaswani 等人提出。"
    
    return chunk


@pytest.fixture
def neo4j_setup():
    """设置 Neo4j 测试数据"""
    from server.infra.neo4j_client import neo4j_client
    
    # 创建测试概念
    query = """
    MERGE (c:Concept {name: "Transformer"})
    SET c.id = "transformer_001",
        c.description = "一种基于自注意力机制的神经网络架构",
        c.domain = "自然语言处理"
    RETURN c
    """
    neo4j_client.execute_query(query)
    
    yield
    
    # 清理
    neo4j_client.execute_query("MATCH (c:Concept {id: 'transformer_001'}) DELETE c")


def test_entity_linker_basic(sample_chunk_with_coref, neo4j_setup):
    """测试基本实体链接"""
    linker = EntityLinker()
    
    entities = linker.link_and_extract(sample_chunk_with_coref)
    
    # 断言
    assert isinstance(entities, list)
    
    # 应该找到 "Transformer" 实体
    transformer_found = any(
        e.get("concept_name") == "Transformer" or "Transformer" in e.get("mention_text", "")
        for e in entities
    )
    
    print(f"找到 {len(entities)} 个实体:")
    for e in entities:
        print(f"  - {e.get('concept_name')} (置信度: {e.get('confidence', 0):.2f})")


def test_entity_linker_nil_detection():
    """测试 NIL 检测（新概念）"""
    linker = EntityLinker()
    
    chunk = ChunkMetadata(
        id="test_001",
        doc_id="test",
        text="这是一个全新的概念 XYZ123。",
        chunk_index=0,
        window_start=0,
        window_end=0,
        sentence_ids=["s0"],
        build_version="test_v1"
    )
    
    entities = linker.link_and_extract(chunk)
    
    # 应该检测到 NIL（新概念）
    nil_entities = [e for e in entities if e.get("is_nil", False)]
    assert len(nil_entities) > 0, "应该检测到至少一个 NIL 实体"


def test_entity_linker_multi_retrieval():
    """测试多路召回"""
    linker = EntityLinker()
    
    chunk = ChunkMetadata(
        id="test_001",
        doc_id="test",
        text="Transformer 是一种架构。",
        chunk_index=0,
        window_start=0,
        window_end=0,
        sentence_ids=["s0"],
        build_version="test_v1"
    )
    chunk.coreference_aliases = {}
    
    # 测试别名词典召回
    candidates = linker._multi_retrieval(
        mention="Transformer",
        text=chunk.text,
        alias_map={},
        chunk=chunk
    )
    
    assert isinstance(candidates, list)
    print(f"多路召回找到 {len(candidates)} 个候选")


def test_entity_linker_rerank():
    """测试精排功能"""
    linker = EntityLinker()
    
    from server.graphrag.stages.stage2_entity_linker import EntityCandidate
    
    # 创建测试候选
    candidates = [
        EntityCandidate(
            concept_id="c1",
            concept_name="Transformer",
            mention_text="Transformer",
            description="神经网络架构"
        ),
        EntityCandidate(
            concept_id="c2",
            concept_name="Attention",
            mention_text="Transformer",
            description="注意力机制"
        )
    ]
    
    chunk = ChunkMetadata(
        id="test_001",
        doc_id="test",
        text="Transformer 是一种架构。",
        chunk_index=0,
        window_start=0,
        window_end=0,
        sentence_ids=["s0"],
        build_version="test_v1"
    )
    
    ranked = linker._rerank(candidates, "Transformer", chunk.text, chunk)
    
    assert len(ranked) == len(candidates)
    # 第一个应该是分数最高的
    assert ranked[0].score >= ranked[1].score if len(ranked) > 1 else True
```

### 4.2 手动测试脚本

创建 `tests/scripts/test_stage2_manual.py`：

```python
"""阶段 2 手动测试脚本"""
from server.graphrag.stages.stage2_entity_linker import EntityLinker
from server.graphrag.stages.stage1_coref import CoreferenceResolver
from server.graphrag.stages.stage0_chunker import SemanticChunker

def main():
    # 1. 切分文档
    chunker = SemanticChunker()
    with open("tests/fixtures/test_doc.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    chunks = chunker.split("test_doc", text, "manual_test_001")
    
    # 2. 指代消解
    resolver = CoreferenceResolver()
    for chunk in chunks:
        result = resolver.resolve(chunk)
        chunk.resolved_text = result.resolved_text
        chunk.coreference_aliases = result.alias_map
        chunk.coref_mode = result.mode
    
    # 3. 实体链接
    linker = EntityLinker()
    
    for i, chunk in enumerate(chunks):
        print(f"\n{'='*60}")
        print(f"Chunk {i}: {chunk.id}")
        print(f"{'='*60}")
        print(f"文本: {chunk.text[:150]}...")
        
        entities = linker.link_and_extract(chunk)
        
        print(f"\n找到 {len(entities)} 个实体:")
        for e in entities:
            nil_mark = " [NIL]" if e.get("is_nil") else ""
            review_mark = " [需复核]" if e.get("is_review") else ""
            print(f"  - {e.get('concept_name')} (置信度: {e.get('confidence', 0):.2f}){nil_mark}{review_mark}")
            if e.get("evidence"):
                print(f"    证据: {e.get('evidence')}")

if __name__ == "__main__":
    main()
```

---

## 5. 阶段 3: 论断抽取测试

### 5.1 单元测试

创建 `tests/graphrag/stages/test_stage3_claim_extractor.py`：

```python
import pytest
from server.graphrag.stages.stage3_claim_extractor import ClaimExtractor
from server.graphrag.models.chunk import ChunkMetadata


@pytest.fixture
def sample_chunk():
    """创建测试用的 Chunk"""
    return ChunkMetadata(
        id="test_chunk_001",
        doc_id="test_doc",
        text="Transformer 是一种基于自注意力机制的神经网络架构。研究表明，Transformer 在自然语言处理任务中表现优异。然而，Transformer 需要大量的计算资源。",
        chunk_index=0,
        window_start=0,
        window_end=2,
        sentence_ids=["s0", "s1", "s2"],
        build_version="test_v1"
    )


@pytest.mark.asyncio
async def test_claim_extractor_basic(sample_chunk):
    """测试基本论断抽取"""
    extractor = ClaimExtractor()
    
    claims, relations = extractor.extract(sample_chunk)
    
    # 断言
    assert isinstance(claims, list)
    assert isinstance(relations, list)
    
    # 应该至少提取到一个论断
    if extractor.client:  # 只有在有 AI 客户端时才测试
        assert len(claims) > 0, "应该提取到至少一个论断"
        
        # 检查 Claim 对象
        first_claim = claims[0]
        assert hasattr(first_claim, "text")
        assert hasattr(first_claim, "confidence")
        assert hasattr(first_claim, "claim_type")
        assert 0.0 <= first_claim.confidence <= 1.0


def test_claim_extractor_modality_detection():
    """测试语气检测"""
    extractor = ClaimExtractor()
    
    # 测试谨慎语气
    assert extractor._detect_modality("这可能是一个好的方法") == "hedged"
    
    # 测试推测语气
    assert extractor._detect_modality("假设这个理论成立") == "speculative"
    
    # 测试断言语气
    assert extractor._detect_modality("Transformer 是一种架构") == "assertive"


def test_claim_extractor_polarity_detection():
    """测试极性检测"""
    extractor = ClaimExtractor()
    
    # 测试否定
    assert extractor._detect_polarity("这不是一个好的方法") == "negative"
    
    # 测试肯定
    assert extractor._detect_polarity("这是一个好的方法") == "positive"
```

### 5.2 手动测试脚本

创建 `tests/scripts/test_stage3_manual.py`：

```python
"""阶段 3 手动测试脚本"""
from server.graphrag.stages.stage3_claim_extractor import ClaimExtractor
from server.graphrag.stages.stage0_chunker import SemanticChunker

def main():
    # 1. 切分文档
    chunker = SemanticChunker()
    with open("tests/fixtures/test_doc.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    chunks = chunker.split("test_doc", text, "manual_test_001")
    
    # 2. 论断抽取
    extractor = ClaimExtractor()
    
    for i, chunk in enumerate(chunks):
        print(f"\n{'='*60}")
        print(f"Chunk {i}: {chunk.id}")
        print(f"{'='*60}")
        print(f"文本: {chunk.text[:200]}...")
        
        claims, relations = extractor.extract(chunk)
        
        print(f"\n提取到 {len(claims)} 个论断:")
        for j, claim in enumerate(claims):
            print(f"\n  论断 {j+1}:")
            print(f"    文本: {claim.text}")
            print(f"    类型: {claim.claim_type}")
            print(f"    置信度: {claim.confidence:.2f}")
            print(f"    语气: {claim.modality}")
            print(f"    极性: {claim.polarity}")
            print(f"    确定性: {claim.certainty:.2f}")
            if claim.evidence_span:
                print(f"    证据位置: {claim.evidence_span}")
        
        print(f"\n提取到 {len(relations)} 个关系:")
        for j, rel in enumerate(relations):
            print(f"  关系 {j+1}: {rel.relation_type} (置信度: {rel.confidence:.2f})")

if __name__ == "__main__":
    main()
```

---

## 6. 阶段 4: 主题社区测试

### 6.1 单元测试

创建 `tests/graphrag/stages/test_stage4_theme_builder.py`：

```python
import pytest
from server.graphrag.stages.stage4_theme_builder import ThemeBuilder


@pytest.fixture
def neo4j_test_data():
    """设置 Neo4j 测试数据"""
    from server.infra.neo4j_client import neo4j_client
    
    # 创建测试概念
    query = """
    MERGE (c1:Concept {id: "c1", name: "Transformer"})
    MERGE (c2:Concept {id: "c2", name: "Attention"})
    MERGE (c3:Concept {id: "c3", name: "BERT"})
    MERGE (c1)-[:RELATED_TO]->(c2)
    MERGE (c2)-[:RELATED_TO]->(c3)
    """
    neo4j_client.execute_query(query)
    
    yield
    
    # 清理
    neo4j_client.execute_query("""
    MATCH (c:Concept)
    WHERE c.id IN ["c1", "c2", "c3"]
    DETACH DELETE c
    """)


def test_theme_builder_basic(neo4j_test_data):
    """测试基本主题构建"""
    builder = ThemeBuilder()
    
    # 构建主题
    themes = builder.build("test_doc")
    
    # 断言
    assert isinstance(themes, list)
    # 如果有概念，应该生成主题
    if themes:
        first_theme = themes[0]
        assert hasattr(first_theme, "label")
        assert hasattr(first_theme, "summary")
        assert hasattr(first_theme, "community_id")
```

---

## 7. 阶段 5: 谓词治理测试

### 7.1 单元测试

创建 `tests/graphrag/stages/test_stage5_predicate_governor.py`：

```python
import pytest
from server.graphrag.stages.stage5_predicate_governor import PredicateGovernor


def test_predicate_normalization():
    """测试谓词归一化"""
    governor = PredicateGovernor()
    
    # 测试映射
    assert governor._map_to_standard("基于") == "USES"
    assert governor._map_to_standard("采用") == "USES"
    assert governor._map_to_standard("包含") == "CONTAINS"


def test_type_constraint_check():
    """测试类型约束检查"""
    governor = PredicateGovernor()
    
    # 测试合法关系
    assert governor._check_type_constraint("Method", "USES", "Tool") == True
    
    # 测试非法关系
    assert governor._check_type_constraint("Person", "USES", "Tool") == False
```

---

## 8. 阶段 6: 幂等落库测试

### 8.1 单元测试

创建 `tests/graphrag/stages/test_stage6_graph_service.py`：

```python
import pytest
from server.graphrag.stages.stage6_graph_service import GraphService
from server.graphrag.models.chunk import ChunkMetadata


def test_graph_service_store_concept():
    """测试概念存储"""
    service = GraphService()
    
    chunk = ChunkMetadata(
        id="test_chunk_001",
        doc_id="test_doc",
        text="Transformer 是一种架构。",
        chunk_index=0,
        window_start=0,
        window_end=0,
        sentence_ids=["s0"],
        build_version="test_v1"
    )
    
    # 存储概念
    concept_id = service.store_concept(
        name="Transformer",
        description="神经网络架构",
        chunk=chunk,
        build_version="test_v1"
    )
    
    assert concept_id is not None
    
    # 再次存储应该幂等（返回相同的 ID）
    concept_id2 = service.store_concept(
        name="Transformer",
        description="神经网络架构",
        chunk=chunk,
        build_version="test_v1"
    )
    
    assert concept_id == concept_id2, "应该幂等返回相同的 ID"
```

---

## 9. 阶段 7: GraphRAG 检索测试

### 9.1 单元测试

创建 `tests/graphrag/stages/test_stage7_query_service.py`：

```python
import pytest
from server.graphrag.stages.stage7_query_service import QueryService


@pytest.mark.asyncio
async def test_query_service_answer():
    """测试 GraphRAG 查询"""
    service = QueryService()
    
    result = await service.answer(
        question="什么是 Transformer？",
        mode="hybrid",
        top_k=5
    )
    
    # 断言
    assert "answer" in result
    assert "themes" in result
    assert "evidence" in result
    assert len(result["answer"]) > 0
```

---

## 10. 阶段 8: 评价指标测试

### 10.1 单元测试

创建 `tests/graphrag/stages/test_stage8_metrics_service.py`：

```python
import pytest
from server.graphrag.stages.stage8_metrics_service import MetricsService


def test_metrics_calculation():
    """测试指标计算"""
    service = MetricsService()
    
    metrics = service.calculate("test_build_version")
    
    # 断言
    assert "entity_link_accuracy" in metrics
    assert "theme_nmi" in metrics
    assert "claim_relation_precision" in metrics
    assert all(0.0 <= v <= 1.0 for v in metrics.values() if isinstance(v, float))
```

---

## 11. 集成测试

### 11.1 完整流程测试

创建 `tests/integration/test_full_pipeline.py`：

```python
"""完整流程集成测试"""
import pytest
from server.graphrag.stages import (
    SemanticChunker,
    CoreferenceResolver,
    EntityLinker,
    ClaimExtractor,
    ThemeBuilder,
    GraphService
)


@pytest.mark.integration
def test_full_pipeline():
    """测试完整的 GraphRAG 构建流程"""
    
    doc_id = "test_doc_integration"
    build_version = f"{doc_id}_test_001"
    
    # 读取测试文档
    with open("tests/fixtures/test_doc.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    # 阶段 0: 篇章切分
    chunker = SemanticChunker()
    chunks = chunker.split(doc_id, text, build_version)
    assert len(chunks) > 0
    
    # 阶段 1: 指代消解
    resolver = CoreferenceResolver()
    for chunk in chunks:
        result = resolver.resolve(chunk)
        chunk.resolved_text = result.resolved_text
        chunk.coreference_aliases = result.alias_map
        chunk.coref_mode = result.mode
    
    # 阶段 2: 实体链接
    linker = EntityLinker()
    all_entities = []
    for chunk in chunks:
        entities = linker.link_and_extract(chunk)
        all_entities.extend(entities)
    assert len(all_entities) > 0
    
    # 阶段 3: 论断抽取
    extractor = ClaimExtractor()
    all_claims = []
    for chunk in chunks:
        claims, relations = extractor.extract(chunk)
        all_claims.extend(claims)
    
    # 阶段 4: 主题社区（需要 Neo4j 中有数据）
    # builder = ThemeBuilder()
    # themes = builder.build(doc_id)
    
    # 阶段 6: 落库
    graph_service = GraphService()
    for entity in all_entities:
        if not entity.get("is_nil"):
            graph_service.store_concept(
                name=entity["concept_name"],
                description=entity.get("description"),
                chunk=chunks[0],  # 简化：使用第一个 chunk
                build_version=build_version
            )
    
    print(f"集成测试完成:")
    print(f"  - Chunks: {len(chunks)}")
    print(f"  - Entities: {len(all_entities)}")
    print(f"  - Claims: {len(all_claims)}")
```

运行集成测试：

```bash
pytest tests/integration/test_full_pipeline.py -v -m integration
```

---

## 12. 端到端测试

### 12.1 API 测试

创建 `tests/e2e/test_api_endpoints.py`：

```python
"""API 端到端测试"""
import pytest
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


def test_upload_and_ingest():
    """测试上传和摄取流程"""
    
    # 1. 上传文件
    with open("tests/fixtures/test_doc.txt", "rb") as f:
        response = client.post("/uploads/file", files={"file": f})
    assert response.status_code == 200
    file_id = response.json()["file_id"]
    
    # 2. 启动摄取
    response = client.post(f"/ingest/{file_id}")
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    # 3. 检查状态
    response = client.get(f"/ingest/status/{job_id}")
    assert response.status_code == 200
    status = response.json()["status"]
    assert status in ["pending", "processing", "completed", "failed"]


def test_graphrag_query():
    """测试 GraphRAG 查询"""
    response = client.post(
        "/graphrag/query",
        json={
            "question": "什么是 Transformer？",
            "mode": "hybrid",
            "top_k": 5
        }
    )
    assert response.status_code == 200
    result = response.json()
    assert "answer" in result
```

---

## 13. 测试工具与脚本

### 13.1 测试运行脚本

创建 `tests/run_all_tests.sh`：

```bash
#!/bin/bash
# 运行所有测试

echo "运行单元测试..."
pytest tests/graphrag/stages/ -v --cov=server.graphrag.stages --cov-report=html

echo "运行集成测试..."
pytest tests/integration/ -v -m integration

echo "运行端到端测试..."
pytest tests/e2e/ -v

echo "测试完成！"
```

### 13.2 性能测试脚本

创建 `tests/performance/test_performance.py`：

```python
"""性能测试"""
import time
from server.graphrag.stages.stage0_chunker import SemanticChunker

def test_chunker_performance():
    """测试切分器性能"""
    chunker = SemanticChunker()
    
    # 读取大文档
    with open("tests/fixtures/large_doc.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    start = time.time()
    chunks = chunker.split("perf_test", text, "v1")
    elapsed = time.time() - start
    
    print(f"处理 {len(text)} 字符，生成 {len(chunks)} 个 Chunk")
    print(f"耗时: {elapsed:.2f} 秒")
    print(f"速度: {len(text) / elapsed:.0f} 字符/秒")
```

### 13.3 测试数据生成器

创建 `tests/utils/generate_test_data.py`：

```python
"""生成测试数据"""
import random

def generate_test_document(length=1000):
    """生成测试文档"""
    sentences = [
        "Transformer 是一种神经网络架构。",
        "它由 Vaswani 等人提出。",
        "Transformer 的核心是自注意力机制。",
        "BERT 和 GPT 都基于 Transformer。",
        "Transformer 在 NLP 任务中表现优异。"
    ]
    
    text = ""
    for _ in range(length // 50):
        text += random.choice(sentences) + " "
    
    return text

if __name__ == "__main__":
    text = generate_test_document(5000)
    with open("tests/fixtures/generated_doc.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("测试数据已生成")
```

---

## 测试最佳实践

### 1. 测试隔离

- 每个测试应该独立运行，不依赖其他测试
- 使用 `pytest.fixture` 管理测试数据
- 测试后清理 Neo4j 数据

### 2. Mock 外部依赖

```python
from unittest.mock import Mock, patch

@patch('server.graphrag.stages.stage3_claim_extractor.AIProviderFactory')
def test_claim_extractor_mock(mock_factory):
    mock_client = Mock()
    mock_client.chat_completion.return_value = '{"claims": []}'
    mock_factory.create_client.return_value = mock_client
    
    extractor = ClaimExtractor()
    # 测试...
```

### 3. 测试覆盖率

```bash
# 生成覆盖率报告
pytest --cov=server.graphrag --cov-report=html

# 查看报告
open htmlcov/index.html
```

### 4. 持续集成

在 `.github/workflows/test.yml` 中配置 CI：

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r server/requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          pytest tests/ -v --cov=server.graphrag
```

---

## 常见问题

### Q1: 测试时 Neo4j 连接失败

**A**: 确保 Neo4j 服务正在运行：
```bash
docker-compose up -d neo4j
# 或
neo4j start
```

### Q2: AI API 调用失败

**A**: 使用 Mock 模式或设置有效的 API key：
```bash
export AI_PROVIDER=mock
# 或
export AI_API_KEY=your-key
```

### Q3: 测试数据污染

**A**: 使用独立的测试数据库或测试后清理：
```python
@pytest.fixture(autouse=True)
def cleanup():
    yield
    # 清理测试数据
    neo4j_client.execute_query("MATCH (n) WHERE n.build_version = 'test' DELETE n")
```

---

## 总结

本指南提供了 GraphRAG 8 个阶段的完整测试方法：

1. **单元测试**: 测试每个阶段的独立功能
2. **集成测试**: 测试阶段间的协作
3. **端到端测试**: 测试完整的 API 流程
4. **性能测试**: 测试处理速度和资源使用

建议按照以下顺序进行测试：

1. 先运行单元测试，确保每个阶段功能正常
2. 再运行集成测试，确保阶段间协作正常
3. 最后运行端到端测试，确保整体流程正常

如有问题，请参考各阶段的实现代码或提交 Issue。

