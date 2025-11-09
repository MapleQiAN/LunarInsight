# GraphRAG 测试快速参考

## 🚀 快速开始

### 1. 安装依赖

```bash
cd server
pip install pytest pytest-asyncio pytest-cov
```

### 2. 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个阶段测试
pytest tests/graphrag/stages/test_stage0_chunker.py -v

# 运行手动测试脚本
python tests/scripts/test_stage0_manual.py
```

---

## 📋 各阶段测试方法

### 阶段 0: 篇章切分

**测试文件**: `tests/graphrag/stages/test_stage0_chunker.py`

**手动测试**:
```bash
python tests/scripts/test_stage0_manual.py
```

**关键测试点**:
- ✅ 基本切分功能
- ✅ 滑动窗口重叠
- ✅ 空文本处理
- ✅ 短文本处理

**示例代码**:
```python
from server.graphrag.stages.stage0_chunker import SemanticChunker

chunker = SemanticChunker()
chunks = chunker.split("doc_id", "文本内容...", "build_version")
print(f"生成 {len(chunks)} 个 Chunk")
```

---

### 阶段 1: 指代消解

**测试文件**: `tests/graphrag/stages/test_stage1_coref.py`

**手动测试**:
```bash
python tests/scripts/test_stage1_manual.py
```

**关键测试点**:
- ✅ 基本指代消解
- ✅ 括号别名提取（如 "AI" → "人工智能"）
- ✅ 质量指标计算（覆盖率、冲突率）
- ✅ 决策模式（rewrite/local/alias_only/skip）

**示例代码**:
```python
from server.graphrag.stages.stage1_coref import CoreferenceResolver

resolver = CoreferenceResolver()
result = resolver.resolve(chunk)

print(f"模式: {result.mode}")
print(f"覆盖率: {result.coverage:.2%}")
print(f"别名映射: {result.alias_map}")
```

---

### 阶段 2: 实体链接

**测试文件**: `tests/graphrag/stages/test_stage2_entity_linker.py`

**关键测试点**:
- ✅ 多路召回（别名词典 + BM25 + 向量）
- ✅ 精排（6 特征融合）
- ✅ NIL 检测（新概念）
- ✅ 分类型阈值

**示例代码**:
```python
from server.graphrag.stages.stage2_entity_linker import EntityLinker

linker = EntityLinker()
entities = linker.link_and_extract(chunk)

for e in entities:
    print(f"{e['concept_name']} (置信度: {e['confidence']:.2f})")
```

---

### 阶段 3: 论断抽取

**测试文件**: `tests/graphrag/stages/test_stage3_claim_extractor.py`

**关键测试点**:
- ✅ 论断提取
- ✅ 关系识别（SUPPORTS/CONTRADICTS/CAUSES）
- ✅ 证据对齐
- ✅ NLI 验证

**示例代码**:
```python
from server.graphrag.stages.stage3_claim_extractor import ClaimExtractor

extractor = ClaimExtractor()
claims, relations = extractor.extract(chunk)

print(f"提取到 {len(claims)} 个论断, {len(relations)} 个关系")
```

---

### 阶段 4: 主题社区

**测试文件**: `tests/graphrag/stages/test_stage4_theme_builder.py`

**关键测试点**:
- ✅ 社区检测（Louvain/Leiden）
- ✅ 主题摘要生成
- ✅ 主题节点创建

**示例代码**:
```python
from server.graphrag.stages.stage4_theme_builder import ThemeBuilder

builder = ThemeBuilder()
themes = builder.build("doc_id")
print(f"生成 {len(themes)} 个主题")
```

---

### 阶段 5: 谓词治理

**测试文件**: `tests/graphrag/stages/test_stage5_predicate_governor.py`

**关键测试点**:
- ✅ 谓词归一化（"基于" → "USES"）
- ✅ 类型约束检查
- ✅ 白名单验证

**示例代码**:
```python
from server.graphrag.stages.stage5_predicate_governor import PredicateGovernor

governor = PredicateGovernor()
normalized = governor.normalize(relation)
```

---

### 阶段 6: 幂等落库

**测试文件**: `tests/graphrag/stages/test_stage6_graph_service.py`

**关键测试点**:
- ✅ 幂等性（重复写入返回相同 ID）
- ✅ 证据回溯（四级定位）
- ✅ 版本标记

**示例代码**:
```python
from server.graphrag.stages.stage6_graph_service import GraphService

service = GraphService()
concept_id = service.store_concept(
    name="Transformer",
    description="神经网络架构",
    chunk=chunk,
    build_version="v1"
)
```

---

### 阶段 7: GraphRAG 检索

**测试文件**: `tests/graphrag/stages/test_stage7_query_service.py`

**关键测试点**:
- ✅ 主题优先召回
- ✅ 证据扩展
- ✅ 限域生成

**示例代码**:
```python
from server.graphrag.stages.stage7_query_service import QueryService

service = QueryService()
result = await service.answer(
    question="什么是 Transformer？",
    mode="hybrid"
)
print(result["answer"])
```

---

### 阶段 8: 评价指标

**测试文件**: `tests/graphrag/stages/test_stage8_metrics_service.py`

**关键测试点**:
- ✅ 实体链接准确率
- ✅ 主题一致性（NMI）
- ✅ 论证关系质量

**示例代码**:
```python
from server.graphrag.stages.stage8_metrics_service import MetricsService

service = MetricsService()
metrics = service.calculate("build_version")
print(f"实体链接准确率: {metrics['entity_link_accuracy']:.2%}")
```

---

## 🔄 完整流程测试

### 运行完整流程测试

```bash
python tests/scripts/test_full_pipeline.py
```

### 集成测试

```bash
pytest tests/integration/test_full_pipeline.py -v -m integration
```

---

## 🛠️ 测试工具

### 1. 测试覆盖率

```bash
pytest --cov=server.graphrag --cov-report=html
open htmlcov/index.html
```

### 2. 性能测试

```bash
pytest tests/performance/ -v
```

### 3. Mock 模式

设置环境变量使用 Mock AI 客户端：

```bash
export AI_PROVIDER=mock
pytest tests/ -v
```

---

## 📝 测试检查清单

### 每个阶段测试前检查：

- [ ] Neo4j 服务运行中
- [ ] 测试数据已准备
- [ ] 环境变量已配置
- [ ] 依赖已安装

### 测试后检查：

- [ ] 所有断言通过
- [ ] 日志输出正常
- [ ] 测试数据已清理
- [ ] 覆盖率达标（> 80%）

---

## 🐛 常见问题

### Q: Neo4j 连接失败

```bash
# 启动 Neo4j
docker-compose up -d neo4j

# 或检查连接
cypher-shell -u neo4j -p test1234 "RETURN 1"
```

### Q: AI API 调用失败

```bash
# 使用 Mock 模式
export AI_PROVIDER=mock

# 或设置有效的 API key
export AI_API_KEY=your-key
```

### Q: 测试数据污染

```python
# 使用独立的测试数据库
# 或在测试后清理
@pytest.fixture(autouse=True)
def cleanup():
    yield
    neo4j_client.execute_query("MATCH (n) WHERE n.build_version = 'test' DELETE n")
```

---

## 📚 更多资源

- [完整测试指南](TESTING_GUIDE.md) - 详细的测试文档
- [GraphRAG README](README.md) - 模块使用说明
- [算法规范](../../.cursor/rules/knowledge-graph-algorithm.mdc) - 算法实现规范

---

## 💡 测试最佳实践

1. **先单元测试，再集成测试**
   - 确保每个阶段功能正常
   - 再测试阶段间协作

2. **使用 Mock 模式**
   - 避免真实 API 调用
   - 提高测试速度

3. **测试数据隔离**
   - 使用独立的测试数据库
   - 测试后清理数据

4. **覆盖率目标**
   - 单元测试覆盖率 > 80%
   - 关键路径覆盖率 > 90%

---

**需要帮助？** 查看 [TESTING_GUIDE.md](TESTING_GUIDE.md) 获取详细说明。

