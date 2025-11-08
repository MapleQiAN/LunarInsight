# LunarInsight Frontend (Vue 3)

Vue 3 前端应用，使用 Vite 构建，Element Plus UI 组件库，Cytoscape.js 图谱可视化。

## 技术栈

- **Vue 3** (Composition API)
- **Vite** - 构建工具
- **Vue Router 4** - 路由
- **Pinia** - 状态管理
- **Element Plus** - UI 组件库
- **Cytoscape.js** - 图谱可视化
- **ECharts** - 图表可视化
- **vue-i18n** - 国际化
- **Axios** - HTTP 客户端

## 开发

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动。

### 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录。

### 预览生产构建

```bash
npm run preview
```

## 环境变量

创建 `.env` 文件（参考 `.env.example`）：

```
VITE_API_BASE=http://localhost:8000
```

## 项目结构

```
src/
├── api/              # API 服务
│   ├── index.js     # Axios 配置
│   └── services.js  # API 接口
├── assets/          # 静态资源
├── components/      # 公共组件
├── i18n/           # 国际化
│   └── locales/     # 翻译文件
├── layouts/         # 布局组件
├── router/          # 路由配置
├── stores/          # Pinia stores
├── styles/          # 全局样式
├── views/           # 页面组件
│   ├── Dashboard.vue
│   ├── Upload.vue
│   ├── Graph.vue
│   ├── Query.vue
│   └── Status.vue
├── App.vue          # 根组件
└── main.js          # 入口文件
```

## Docker

使用 Docker 构建和运行：

```bash
docker build -t lunarinsight-frontend .
docker run -p 80:80 lunarinsight-frontend
```

## 功能

- 📊 **仪表板** - 系统概览和核心指标
- 📤 **文档上传** - 上传并处理文档
- 🕸️ **图谱可视化** - 使用 Cytoscape.js 可视化知识图谱
- 🔍 **图谱查询** - Cypher 查询和节点/关系检索
- 📈 **处理状态** - 查看任务处理状态

## 国际化

支持中文和英文，使用 `vue-i18n` 管理翻译。语言切换在顶部导航栏。

