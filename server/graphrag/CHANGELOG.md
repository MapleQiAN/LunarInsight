# GraphRAG Module Changelog

---

## [Unreleased] - 2025-11-08

### Added - 初始骨架创建

#### 目录结构
- ✅ 创建 `server/graphrag/` 模块根目录
- ✅ 创建子目录：`stages/`, `models/`, `config/`, `prompts/`, `utils/`, `api/`
- ✅ 创建 `__init__.py` 模块入口文件
- ✅ 创建 `README.md` 使用文档

#### 配置文件
- ✅ `config/predicates.yaml` - 谓词白名单与映射配置
- ✅ `config/ontology.yaml` - 本体类型约束配置
- ✅ `config/thresholds.yaml` - 阈值配置
- ✅ `config/__init__.py` - 配置加载器（支持单例访问）

#### Prompt 模板
- ✅ `prompts/claim_extraction.txt` - 论断抽取 Prompt
- ✅ `prompts/theme_summary.txt` - 主题摘要 Prompt
- ✅ `prompts/entity_linking.txt` - 实体链接 Prompt
- ✅ `prompts/graphrag_query.txt` - GraphRAG 查询 Prompt

#### 数据模型 (Pydantic v2)
- ✅ `models/chunk.py` - ChunkMetadata, ChunkWithRelations
- ✅ `models/claim.py` - Claim, ClaimRelation
- ✅ `models/theme.py` - Theme, ThemeGraph
- ✅ `models/feedback.py` - MergeRequest, CorrectionRequest, UnlinkRequest, FeedbackLog

#### 工具函数
- ✅ `utils/text_processing.py` - 文本处理（句子分割、章节提取、滑动窗口）
- ✅ `utils/embedding.py` - 向量化（文本嵌入、相似度计算）
- ✅ `utils/validation.py` - 数据校验（Chunk/Claim/Concept/Relation 验证）

#### 阶段实现（Stub）
- ✅ `stages/stage0_chunker.py` - SemanticChunker（篇章切分）
- ✅ `stages/stage1_coref.py` - CoreferenceResolver（指代消解）
- ✅ `stages/stage2_entity_linker.py` - EntityLinker（实体链接）
- ✅ `stages/stage3_claim_extractor.py` - ClaimExtractor（论断抽取）
- ✅ `stages/stage4_theme_builder.py` - ThemeBuilder（主题社区）
- ✅ `stages/stage5_predicate_governor.py` - PredicateGovernor（谓词治理）
- ✅ `stages/stage6_graph_service.py` - GraphService（幂等落库）
- ✅ `stages/stage7_query_service.py` - QueryService（GraphRAG 检索）
- ✅ `stages/stage8_metrics_service.py` - MetricsService（评价与反馈）

#### API 接口（FastAPI）
- ✅ `api/query.py` - GraphRAG 查询接口（/graphrag/query, /graphrag/themes）
- ✅ `api/feedback.py` - 反馈接口（/graphrag/feedback/merge, /correction, /unlink）

---

## 实现状态

### 已完成 ✅
- 目录结构与模块初始化
- 配置文件编写（YAML）
- 数据模型定义（Pydantic）
- Prompt 模板编写
- 工具函数骨架
- 8 个阶段的骨架实现
- API 接口骨架

### 待实现 🚧
- Neo4j GraphRAG 集成（阶段 2）
- LLM 调用实现（阶段 3, 4, 7）
- Neo4j GDS 集成（阶段 4）
- 数据库写入逻辑（阶段 6）
- GraphRAG 检索实现（阶段 7）
- 评价指标计算（阶段 8）
- 反馈审核流程（API）

### 需要填充的占位符 📝
- `utils/embedding.py`: OpenAI API 调用
- `stages/stage1_coref.py`: Coref 模型集成
- `stages/stage2_entity_linker.py`: Neo4j GraphRAG KG Builder
- `stages/stage3_claim_extractor.py`: LLM Prompt 调用
- `stages/stage4_theme_builder.py`: Louvain 社区发现
- `stages/stage6_graph_service.py`: Cypher 查询实现
- `stages/stage7_query_service.py`: GraphRAG Retriever 实现
- `api/query.py`: 主题查询实现
- `api/feedback.py`: 反馈队列实现

---

## 下一步行动

### 优先级 P0（高优先级）
1. **环境准备**
   - 安装依赖：`neo4j-graphrag>=0.5.0`, `graphdatascience>=1.9`, `sentence-transformers>=2.2.0`
   - 配置 Neo4j（版本 >= 5.11，启用 GDS 插件）
   - 配置 OpenAI API Key

2. **基础设施**
   - 实现 `utils/embedding.py` 的 OpenAI API 调用
   - 创建 Schema 初始化脚本（创建索引与约束）
   - 集成 Neo4j 客户端到 `stages/stage6_graph_service.py`

3. **核心算法**
   - 完成阶段 0: 篇章切分（已基本完成）
   - 完成阶段 2: 实体链接（集成 Neo4j GraphRAG）
   - 完成阶段 6: 幂等落库（实现 Cypher 查询）

### 优先级 P1（中优先级）
4. **GraphRAG 功能**
   - 完成阶段 7: GraphRAG 检索
   - 测试 Local/Global/Hybrid 查询模式
   - 前端集成（调用 `/graphrag/query` 接口）

5. **高级特性**
   - 完成阶段 3: 论断抽取
   - 完成阶段 4: 主题社区
   - 完成阶段 5: 谓词治理

### 优先级 P2（低优先级）
6. **治理闭环**
   - 完成阶段 8: 评价指标
   - 实现反馈审核流程
   - 创建指标看板

---

## 依赖关系

```
阶段 0 (篇章切分)
  ↓
阶段 1 (指代消解)
  ↓
阶段 2 (实体链接) ────→ 阶段 3 (论断抽取)
  ↓                       ↓
阶段 4 (主题社区) ←──────┘
  ↓
阶段 5 (谓词治理)
  ↓
阶段 6 (幂等落库)
  ↓
阶段 7 (GraphRAG 检索)
  ↓
阶段 8 (评价与反馈)
```

---

## 质量标准

### 代码质量
- [ ] 所有模块有单元测试（覆盖率 >= 70%）
- [ ] 所有函数有 Docstring
- [ ] 所有异常有日志记录
- [ ] 所有配置外置（不硬编码）

### 功能质量
- [ ] 实体链接准确率 > 85%
- [ ] 主题一致性 (NMI) > 0.7
- [ ] 检索相关性 (NDCG@5) > 0.8
- [ ] OTHER 谓词占比 < 10%

---

## 文档更新

- ✅ `README.md` - 使用指南
- ✅ `CHANGELOG.md` - 变更日志
- ⏳ API 文档（FastAPI 自动生成）
- ⏳ 单测文档
- ⏳ 部署文档

---

**备注**: 本 Changelog 记录 GraphRAG 模块的创建与演进，所有开发必须遵循 `.cursor/rules/knowledge-graph-algorithm.mdc` 规范。

