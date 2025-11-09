# LunarInsight GraphRAG Module

**版本**: v2.0.0-alpha  
**规范文档**: `.cursor/rules/knowledge-graph-algorithm.mdc`

---

## 目录结构

```
server/graphrag/
├── __init__.py              # 模块入口
├── README.md                # 本文档
│
├── stages/                  # 8 个构建阶段
│   ├── __init__.py
│   ├── stage0_chunker.py           # 阶段 0: 篇章切分
│   ├── stage1_coref.py             # 阶段 1: 指代消解
│   ├── stage2_entity_linker.py     # 阶段 2: 实体链接
│   ├── stage3_claim_extractor.py   # 阶段 3: 论断抽取
│   ├── stage4_theme_builder.py     # 阶段 4: 主题社区
│   ├── stage5_predicate_governor.py # 阶段 5: 谓词治理
│   ├── stage6_graph_service.py     # 阶段 6: 幂等落库
│   ├── stage7_query_service.py     # 阶段 7: GraphRAG 检索
│   └── stage8_metrics_service.py   # 阶段 8: 评价与反馈
│
├── models/                  # 数据模型
│   ├── __init__.py
│   ├── chunk.py            # ChunkMetadata 模型
│   ├── claim.py            # Claim 模型
│   ├── theme.py            # Theme 模型
│   └── feedback.py         # 反馈模型
│
├── config/                  # 配置文件
│   ├── predicates.yaml     # 谓词白名单与映射
│   ├── ontology.yaml       # 本体类型约束
│   └── thresholds.yaml     # 阈值配置
│
├── prompts/                 # LLM Prompt 模板
│   ├── claim_extraction.txt
│   ├── theme_summary.txt
│   └── entity_linking.txt
│
├── utils/                   # 工具函数
│   ├── __init__.py
│   ├── text_processing.py  # 文本处理
│   ├── embedding.py        # 向量化
│   └── validation.py       # 数据校验
│
└── api/                     # API 接口
    ├── __init__.py
    ├── query.py            # GraphRAG 查询接口
    └── feedback.py         # 反馈接口
```

---

## 核心流程

### 完整构建流程

```python
from server.graphrag import (
    SemanticChunker,
    CoreferenceResolver,
    EntityLinker,
    ClaimExtractor,
    ThemeBuilder,
    PredicateGovernor,
    GraphService
)

async def build_knowledge_graph(doc_id: str, job_id: str):
    """
    完整的 GraphRAG 构建流程
    """
    build_version = f"{doc_id}_{int(time.time())}"
    
    # 阶段 0: 篇章切分
    chunker = SemanticChunker()
    doc = parser.parse(doc_id)
    chunks = chunker.split(doc)
    
    # 阶段 1: 指代消解
    coref_resolver = CoreferenceResolver()
    for chunk in chunks:
        chunk.text, aliases = coref_resolver.resolve(chunk)
    
    # 阶段 2: 实体链接（Neo4j GraphRAG）
    entity_linker = EntityLinker()
    for chunk in chunks:
        entity_linker.link_and_extract(chunk)
    
    # 阶段 3: 论断抽取
    claim_extractor = ClaimExtractor()
    for chunk in chunks:
        claims, relations = claim_extractor.extract(chunk)
    
    # 阶段 4: 主题社区
    theme_builder = ThemeBuilder()
    theme_builder.build(doc_id)
    
    # 阶段 5: 谓词治理
    predicate_governor = PredicateGovernor()
    predicate_governor.normalize_all(doc_id)
    
    # 阶段 6: 落库（带证据回溯）
    graph_service = GraphService()
    graph_service.store_with_provenance(...)
```

### GraphRAG 查询

```python
from server.graphrag import QueryService

query_service = QueryService()

# 智能问答
result = query_service.answer(
    question="什么是 Transformer？",
    mode="hybrid",  # local | global | hybrid
    top_k=5
)

# 返回结构化答案 + 论证链 + 证据锚点
```

---

## 使用指南

### 1. 环境准备

确保已安装依赖：

```bash
pip install neo4j-graphrag>=0.5.0
pip install graphdatascience>=1.9
pip install sentence-transformers>=2.2.0
```

确保 Neo4j >= 5.11，并启用 GDS 插件。

### 2. 配置

编辑 `server/infra/config.py`：

```python
# GraphRAG 开关
ENABLE_NEO4J_GRAPHRAG = True
ENABLE_VECTOR_SEARCH = True

# 模型配置
LLM_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

# 本体约束
ALLOWED_NODE_TYPES = ["Concept", "Person", "Method", "Tool", "Metric"]
ALLOWED_RELATIONS = ["USES", "IS_A", "PART_OF", "CREATES", "DERIVES_FROM"]
```

### 3. 初始化 Schema

运行初始化脚本：

```bash
cd server/graphrag
python -m scripts.init_schema
```

### 4. 构建知识图谱

```python
from server.routes.ingest import process_document_v2

# 使用新流程构建
await process_document_v2(doc_id="doc123", job_id="job456")
```

### 5. GraphRAG 查询

```python
from server.graphrag.api.query import graphrag_query

result = await graphrag_query(
    question="深度学习的核心原理是什么？",
    mode="hybrid"
)

print(result.answer)        # 结构化答案
print(result.themes)        # 相关主题
print(result.evidence)      # 证据片段
print(result.reasoning_chain)  # 论证链
```

---

## 开发规范

### 代码约定

1. **服务模块**: 所有算法实现在 `stages/` 目录
2. **单测覆盖**: 每个阶段必须有对应单测（`tests/graphrag/stages/`）
3. **配置外置**: 阈值、谓词白名单、本体约束写在 `config/`，不硬编码
4. **幂等性**: 所有写入操作使用 `MERGE`，基于确定性键
5. **证据回溯**: 所有节点/关系必须记录 `doc_id`/`chunk_id`/`section_path`/`sentence_ids`

### 错误处理

```python
from server.graphrag.utils.validation import validate_chunk, validate_claim

try:
    validate_chunk(chunk)
    # 处理逻辑
except ValidationError as e:
    logger.error(f"数据校验失败: {e}")
    # 记录错误，继续处理下一个
```

### 日志规范

```python
import logging
logger = logging.getLogger("graphrag.stage2")

logger.info(f"开始实体链接: chunk_id={chunk.id}")
logger.debug(f"候选概念: {candidates}")
logger.warning(f"链接置信度低: {confidence}")
logger.error(f"链接失败: {error}")
```

---

## 实施优先级

### Phase 1: 基础设施（高优先级）
- [x] 目录结构创建
- [ ] Schema 初始化脚本
- [ ] 配置文件编写
- [ ] 数据模型定义

### Phase 2: 核心算法（高优先级）
- [ ] 阶段 0: 篇章切分
- [ ] 阶段 1: 指代消解
- [ ] 阶段 2: 实体链接
- [ ] 阶段 6: 幂等落库

### Phase 3: GraphRAG（高优先级）
- [ ] 阶段 7: GraphRAG 检索
- [ ] API 接口实现
- [ ] 前端集成

### Phase 4: 高级特性（中优先级）
- [ ] 阶段 3: 论断抽取
- [ ] 阶段 4: 主题社区
- [ ] 阶段 5: 谓词治理

### Phase 5: 治理闭环（低优先级）
- [ ] 阶段 8: 评价指标
- [ ] 反馈接口
- [ ] 指标看板

---

## 质量标准

### 量化指标

| 指标 | 目标 | 测量方式 |
|------|------|---------|
| 实体链接准确率 | > 85% | 人工标注 100 个提及 |
| 主题一致性 (NMI) | > 0.7 | 与人工分类对比 |
| 检索相关性 (NDCG@5) | > 0.8 | 标准问答集评测 |
| 答案可追溯性 | > 90% | 证据锚点复核通过率 |
| OTHER 谓词占比 | < 10% | Cypher 统计 |

### 单测覆盖率

- 核心算法模块: >= 80%
- 工具函数: >= 90%
- API 接口: >= 70%

---

## 常见问题

### Q1: 如何切换回旧流程？

设置环境变量：
```bash
export ENABLE_NEO4J_GRAPHRAG=false
```

### Q2: 如何调试某个阶段？

使用独立测试脚本：
```bash
python -m server.graphrag.stages.stage2_entity_linker --debug --doc-id=doc123
```

### Q3: 如何回滚构建结果？

通过 `build_version` 标签删除：
```cypher
MATCH (n {build_version: "doc123_1699401234"})
DETACH DELETE n
```

### Q4: LLM 成本如何控制？

1. 优先使用 `gpt-4o-mini`
2. 批量调用（减少请求次数）
3. 缓存常见结果
4. 设置每日配额

---

## 参考资源

- **规范文档**: `.cursor/rules/knowledge-graph-algorithm.mdc`
- **Neo4j GraphRAG**: https://github.com/neo4j/neo4j-graphrag-python
- **Neo4j GDS**: https://neo4j.com/docs/graph-data-science/
- **项目结构**: `.cursor/rules/project-structure.mdc`

---

**此模块遵循 LunarInsight 知识图谱构建算法规范，所有开发必须符合规范要求。**

