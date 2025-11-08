# LunarInsight | 月悟

> **A quiet knowledge graph engine for insight.**  
> 在静夜中沉淀知识、联结万象、点亮顿悟。

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![Vue](https://img.shields.io/badge/vue-3.x-green.svg)](https://vuejs.org)
[![Neo4j](https://img.shields.io/badge/neo4j-5.x-green.svg)](https://neo4j.com)

**语言**: [English](README_EN.md) | [简体中文](README.md)

---

## 🖼️ 项目截图

<details>
<summary>点击查看截图</summary>

### 仪表盘
> 知识图谱统计概览和最近活动
<!-- ![Dashboard](docs/images/dashboard.png) -->

### 知识图谱可视化
> 使用 Cytoscape.js 进行交互式图谱探索
<!-- ![Graph](docs/images/graph.png) -->

### 知识卡片管理
> 创建和管理带有丰富元数据的知识卡片
<!-- ![Knowledge Cards](docs/images/knowledge-cards.png) -->

### 文档上传与处理
> 上传文档，让 AI 自动提取知识
<!-- ![Upload](docs/images/upload.png) -->

</details>

---

## 📖 目录

- [项目简介](#1-项目简介)
- [核心特性](#2-核心特性)
- [系统架构](#3-系统架构)
- [核心模块](#4-核心模块)
- [技术栈](#5-技术栈)
- [快速开始](#6-快速开始)
- [API 概览](#7-api-概览)
- [数据模型](#8-数据模型)
- [使用示例](#9-使用示例)
- [路线图](#10-路线图)
- [文档资源](#-文档资源)
- [贡献指南](#-贡献指南)
- [故障排查](#-故障排查)
- [开源协议](#-开源协议)

---

## 1) 项目简介

**LunarInsight（月悟）** 是一个 AI 驱动的开源个人知识图谱系统，将你的文档转化为互联的知识网络。智能抽取实体关系，构建 Neo4j 图谱，实现强大的知识探索与分析。

- **🤖 AI 驱动**：支持 12 种 AI 提供商（OpenAI、Anthropic、DeepSeek、通义千问、Ollama 等）
- **📚 文档处理**：上传 PDF、Markdown 或纯文本文件，自动提取知识
- **🕸️ 知识图谱**：构建和可视化概念间的语义关系
- **💡 智能卡片**：手动创建或通过 AI 提取管理知识卡片
- **🔍 查询探索**：使用 Cytoscape.js 进行交互式图谱可视化
- **🌐 双语支持**：完整的中英文界面

## 2) 核心特性

- **🎯 AI 智能分析**
  - 深度语义理解，支持自定义提示词
  - 丰富的概念提取，包含类别、领域、重要性级别
  - 语义关系识别（因果、包含、比较等）
  - 知识洞察与理解生成
  - 自动提示词优化以获得更好结果

- **🗂️ 灵活的知识管理**
  - 手动创建或 AI 提取知识卡片
  - 标签系统，支持别名和关联概念
  - 领域和类别组织
  - 重要性级别（低、中、高）
  - 通过 REST API 完整的增删改查操作

- **🔌 多提供商 AI 支持**
  - 12 种 AI 提供商：OpenAI、Anthropic、Google Gemini、DeepSeek、通义千问、智谱 GLM、Kimi、文心一言、MiniMax、豆包、Ollama、Mock
  - 统一配置接口
  - 轻松切换提供商
  - 通过 Ollama 支持本地模型

- **🎨 现代化 UI**
  - Vue 3 + Vite + Naive UI
  - 使用 Cytoscape.js 的交互式图谱可视化
  - 实时处理状态
  - 响应式设计
  - 暗黑模式（即将推出）

- **🔐 隐私与安全**
  - 本地优先架构
  - 自托管部署
  - 数据不离开你的基础设施
  - 可选的身份认证（JWT + RBAC 计划中）

## 3) 系统架构

```mermaid
flowchart TB
    subgraph Frontend["前端 (Vue 3)"]
        UI[Web UI<br/>Naive UI + Cytoscape.js]
    end
    
    subgraph Backend["后端 (FastAPI)"]
        API[REST API]
        Parser[文档解析器<br/>PDF/MD/TXT]
        AIService[AI 服务<br/>多提供商支持]
        Extractor[知识提取器]
        GraphService[图谱服务]
    end
    
    subgraph Storage["数据存储"]
        Neo4j[(Neo4j<br/>知识图谱)]
        Redis[(Redis<br/>队列 & 缓存)]
        Files[文件存储]
    end
    
    subgraph AI["AI 提供商"]
        OpenAI[OpenAI]
        Anthropic[Anthropic]
        Others[DeepSeek/通义千问<br/>GLM/Ollama...]
    end
    
    UI -->|上传/查询| API
    API --> Parser
    Parser --> AIService
    AIService --> Extractor
    Extractor --> GraphService
    GraphService --> Neo4j
    API --> Redis
    Parser --> Files
    
    AIService -.->|API 调用| OpenAI
    AIService -.->|API 调用| Anthropic
    AIService -.->|API 调用| Others
    
    Neo4j -->|查询结果| API
    API -->|JSON 响应| UI
```

## 4) 核心模块

**前端（Vue 3）**
- **🏠 仪表盘**：知识图谱统计概览和最近活动
- **📤 知识构建**：文档上传和 AI 驱动处理
- **🃏 知识卡片**：手动创建和管理知识卡片
- **🕸️ 图谱可视化**：使用 Cytoscape.js 进行交互式图谱探索
- **🔍 查询**：高级图谱查询的 Cypher 查询界面
- **⚙️ 设置**：系统配置和 AI 提供商设置
- **📊 状态**：实时处理状态和系统健康

**后端（FastAPI）**
- **文档处理**：多格式解析器（PDF、Markdown、TXT）
- **AI 集成**：12+ AI 提供商的统一接口
- **知识提取**：智能概念和关系提取
- **图谱管理**：Neo4j 增删改查操作和查询执行
- **队列管理**：使用 Redis 的异步处理
- **API 路由**：所有操作的 RESTful 端点

## 5) 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3, TypeScript, Vite, Naive UI, Cytoscape.js, Axios, Vue-i18n, Pinia |
| **后端** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn |
| **数据库** | Neo4j 5.x (Bolt), Redis 7.x |
| **AI/ML** | OpenAI, Anthropic, Google Gemini, DeepSeek, 阿里云通义千问, 智谱GLM, 月之暗面Kimi, 百度文心一言, MiniMax, 字节豆包, Ollama |
| **文档处理** | PyMuPDF (PDF), Markdown, 纯文本 |
| **容器化** | Docker, Docker Compose |
| **未来计划** | 向量搜索 (pgvector/FAISS), OpenTelemetry, Prometheus |

## 6) 快速开始

**先决条件**
- Docker & Docker Compose（推荐）
- 或 Python 3.11+、Node.js 18+、Neo4j 5.x、Redis 7.x（用于本地开发）

**方式 A：Docker Compose（推荐）**

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/LunarInsight.git
cd LunarInsight

# 2. 配置环境变量
cat > .env << EOF
# AI 提供商配置（选择一个）
AI_PROVIDER=openai
AI_API_KEY=sk-your-api-key-here

# 或使用 Ollama 本地模型
# AI_PROVIDER=ollama
# AI_BASE_URL=http://host.docker.internal:11434

# Neo4j 配置
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASS=test1234

# Redis 配置
REDIS_URL=redis://redis:6379/0
EOF

# 3. 启动所有服务
docker-compose up -d

# 4. 访问应用
# - 前端：http://localhost:8788
# - API 文档：http://localhost:8000/docs
# - Neo4j 浏览器：http://localhost:7474 (neo4j/test1234)
```

**方式 B：本地开发**

```bash
# 1. 使用 Docker 启动 Neo4j 和 Redis
docker-compose up -d neo4j redis

# 2. 设置后端
cd server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASS=test1234
export AI_PROVIDER=openai
export AI_API_KEY=sk-your-key

# 启动后端
uvicorn main:app --reload --port 8000

# 3. 设置前端（在另一个终端）
cd app/vue
npm install
npm run dev  # 在 http://localhost:5173 启动
```

**📖 详细指南**
- [AI 提供商配置](docs/AI_PROVIDERS.md) - 所有 12 个 AI 提供商的设置
- [快速开始指南](QUICKSTART.md) - 全面的设置说明
- [环境变量](docs/env-template.md) - 完整配置参考

## 7) API 概览

**文档与知识管理**
```
POST   /uploads/file               # 上传文件 (PDF/MD/TXT)
POST   /uploads/text               # 上传文本内容
GET    /uploads/{file_id}          # 获取文件信息
POST   /ingest/{document_id}       # 启动 AI 提取
GET    /ingest/status/{job_id}     # 查看处理状态
```

**知识卡片**
```
POST   /knowledge-cards            # 创建知识卡片
GET    /knowledge-cards            # 列出卡片（支持过滤）
GET    /knowledge-cards/{card_id}  # 获取卡片详情
PUT    /knowledge-cards/{card_id}  # 更新卡片
DELETE /knowledge-cards/{card_id}  # 删除卡片
```

**图谱操作**
```
GET    /graph/query                # 执行 Cypher 查询
GET    /graph/nodes                # 获取所有节点
GET    /graph/edges                # 获取所有关系
GET    /graph/stats                # 获取图谱统计
```

**系统**
```
GET    /settings/ai-providers      # 列出可用的 AI 提供商
GET    /settings/config            # 获取系统配置
PUT    /settings/config            # 更新配置
GET    /                           # API 健康检查
GET    /docs                       # OpenAPI 文档
```

📚 **完整 API 文档**：运行时访问 `http://localhost:8000/docs`

## 8) 数据模型

**节点类型**
- **`Concept`**：核心知识实体
  - 属性：`name`, `description`, `domain`, `category`, `importance`, `tags`, `created_at`, `updated_at`, `source`
- **`Document`**：上传的文档
  - 属性：`id`, `filename`, `checksum`, `kind`, `size`, `created_at`, `status`
- **`Alias`**：概念的别名
  - 属性：`name`

**关系类型**
- **`MENTIONS`**：文档提及概念
  - 属性：`evidence`, `offset`, `confidence`
- **`DERIVES_FROM`**：概念派生自另一概念
  - 属性：`relationship_type`, `description`
- **`RELATED_TO`**：概念相关
  - 属性：`strength`, `context`
- **`REFERS_TO`**：别名指向概念
  - 无属性

**Neo4j 约束与索引**
```cypher
# 约束
CREATE CONSTRAINT concept_name_unique IF NOT EXISTS
  FOR (c:Concept) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT document_id_unique IF NOT EXISTS
  FOR (d:Document) REQUIRE d.id IS UNIQUE;

# 索引
CREATE INDEX document_checksum IF NOT EXISTS
  FOR (d:Document) ON (d.checksum);

CREATE INDEX concept_domain IF NOT EXISTS
  FOR (c:Concept) ON (c.domain);

CREATE INDEX concept_category IF NOT EXISTS
  FOR (c:Concept) ON (c.category);
```

## 9) 使用示例

**1. 上传并处理文档**
```bash
# 上传文件
curl -X POST "http://localhost:8000/uploads/file" \
  -F "file=@document.pdf"

# 使用自定义提示启动 AI 提取
curl -X POST "http://localhost:8000/ingest/{document_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "enable_ai_segmentation": true,
    "user_prompt": "关注技术概念和方法论"
  }'

# 查看处理状态
curl "http://localhost:8000/ingest/status/{job_id}"
```

**2. 创建知识卡片**
```bash
curl -X POST "http://localhost:8000/knowledge-cards" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "机器学习",
    "description": "人工智能的一个子集，专注于从数据中学习",
    "domain": "计算机科学",
    "category": "技术",
    "importance": "high",
    "tags": ["AI", "数据科学"],
    "aliases": ["ML"],
    "related_concepts": ["深度学习", "神经网络"]
  }'
```

**3. 查询知识图谱**
```bash
# 获取某个领域的所有概念
curl "http://localhost:8000/graph/query?cypher=MATCH%20(c:Concept)%20WHERE%20c.domain='技术'%20RETURN%20c"

# 获取图谱统计
curl "http://localhost:8000/graph/stats"
```

## 10) 路线图

**当前版本（v0.9）**
- ✅ 多提供商 AI 集成（12 个提供商）
- ✅ 文档上传和处理（PDF、Markdown、TXT）
- ✅ AI 驱动的知识提取
- ✅ 手动知识卡片管理
- ✅ 交互式图谱可视化
- ✅ 双语 UI（中文/英文）
- ✅ Docker 部署

**下一版本（v1.0）- 2025 Q2**
- 🎯 向量搜索集成（pgvector/FAISS）
- 🎯 高级查询构建器 UI
- 🎯 知识卡片模板
- 🎯 批量导入/导出
- 🎯 图谱分析仪表板
- 🎯 网页捕获浏览器扩展

**未来（v1.1+）**
- 🔮 基于知识图谱的自然语言问答
- 🔮 学习路径规划和推荐
- 🔮 冲突检测和解决
- 🔮 多用户支持和 JWT 认证
- 🔮 Notion/Obsidian 连接器
- 🔮 移动应用（React Native）
- 🔮 OpenTelemetry 可观测性

---

## 📚 文档资源

- **[快速开始指南](QUICKSTART.md)** - 分步设置说明
- **[AI 提供商指南](docs/AI_PROVIDERS.md)** - 所有 12 个 AI 提供商的配置
- **[AI 分段 API](docs/AI_SEGMENTATION_API.md)** - AI 驱动的文档分析
- **[环境变量](docs/env-template.md)** - 完整配置参考
- **[前端集成](docs/FRONTEND_AI_INTEGRATION.md)** - 前端 AI 功能
- **[实现摘要](docs/IMPLEMENTATION_SUMMARY.md)** - 技术实现细节

## 🤝 贡献指南

我们欢迎贡献！以下是你可以帮助的方式：

1. **报告 Bug**：打开一个 issue 描述 bug 及如何重现
2. **建议功能**：使用 `enhancement` 标签打开 issue
3. **提交 PR**：
   - Fork 本仓库
   - 创建功能分支（`git checkout -b feature/amazing-feature`）
   - 提交你的更改（`git commit -m 'Add amazing feature'`）
   - 推送到分支（`git push origin feature/amazing-feature`）
   - 打开一个 Pull Request

**指南**：
- 遵循现有代码风格和约定
- 为新功能添加测试
- 根据需要更新文档
- 对于重大更改，请先打开 issue 讨论

## 🐛 故障排查

**Neo4j 连接错误**
```bash
# 检查 Neo4j 是否运行
docker ps | grep neo4j

# 检查连接
curl http://localhost:7474
```

**AI 提供商错误**
```bash
# 验证 API 密钥已设置
echo $AI_API_KEY

# 查看日志
docker-compose logs api
```

**前端构建错误**
```bash
# 清除 node_modules 并重新安装
cd app/vue
rm -rf node_modules package-lock.json
npm install
```

**端口已被占用**
```bash
# 查找使用端口 8000 的进程
# Windows PowerShell:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -ti:8000

# 终止进程
# Windows:
taskkill /PID <PID> /F
# Linux/Mac:
kill -9 $(lsof -ti:8000)
```

## 📄 开源协议

Apache License 2.0 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- **Neo4j** - 图数据库平台
- **FastAPI** - 现代 Python Web 框架
- **Vue.js** - 渐进式 JavaScript 框架
- **Naive UI** - Vue 3 组件库
- **Cytoscape.js** - 图可视化库
- 所有出色的开源 AI 提供商

## 📮 联系与支持

- **Issues**: [GitHub Issues](https://github.com/yourusername/LunarInsight/issues)
- **讨论**: [GitHub Discussions](https://github.com/yourusername/LunarInsight/discussions)
- **邮箱**: your-email@example.com (如适用)

---

<p align="center">用 ❤️ 由 LunarInsight 社区制作</p>
<p align="center">⭐ 如果这个项目对你有帮助，请在 GitHub 上给我们一个星标！</p>
