# GraphRAG 测试说明

本目录包含 GraphRAG 模块的所有测试代码。

## 目录结构

```
tests/
├── README.md                    # 本文件
├── graphrag/                    # GraphRAG 模块测试
│   └── stages/                  # 各阶段测试
│       ├── test_stage0_chunker.py
│       ├── test_stage1_coref.py
│       ├── test_stage2_entity_linker.py
│       └── ...
├── integration/                 # 集成测试
│   └── test_full_pipeline.py
├── e2e/                         # 端到端测试
│   └── test_api_endpoints.py
├── scripts/                     # 手动测试脚本
│   ├── test_stage0_manual.py
│   ├── test_stage1_manual.py
│   └── test_full_pipeline.py
└── fixtures/                    # 测试数据
    └── test_doc.txt
```

## 快速开始

### 1. 安装测试依赖

```bash
cd server
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### 2. 运行测试

#### 运行所有测试

```bash
# 从项目根目录
pytest tests/ -v
```

#### 运行单个阶段的测试

```bash
# 阶段 0: 篇章切分
pytest tests/graphrag/stages/test_stage0_chunker.py -v

# 阶段 1: 指代消解
pytest tests/graphrag/stages/test_stage1_coref.py -v
```

#### 运行手动测试脚本

```bash
# 阶段 0 手动测试
python tests/scripts/test_stage0_manual.py

# 阶段 1 手动测试
python tests/scripts/test_stage1_manual.py

# 完整流程测试
python tests/scripts/test_full_pipeline.py
```

### 3. 查看测试覆盖率

```bash
pytest tests/ --cov=server.graphrag --cov-report=html
open htmlcov/index.html
```

## 测试类型

### 单元测试

测试每个阶段的独立功能，位于 `tests/graphrag/stages/`。

### 集成测试

测试多个阶段的协作，位于 `tests/integration/`。

### 端到端测试

测试完整的 API 流程，位于 `tests/e2e/`。

### 手动测试脚本

用于交互式测试和调试，位于 `tests/scripts/`。

## 详细文档

请参考 [TESTING_GUIDE.md](../server/graphrag/TESTING_GUIDE.md) 获取完整的测试指南。

