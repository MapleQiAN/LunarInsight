# LunarInsight Vue 前端升级说明

## 🎉 升级概述

前端 UI 框架已从 **Element Plus** 升级到 **Naive UI**，并采用了类似 [naive-ui-admin](https://github.com/jekip/naive-ui-admin) 的现代化布局设计。

## ✨ 新特性

### 1. **现代化布局**
- ✅ 左侧可折叠侧边栏导航
- ✅ 顶部导航栏（面包屑、语言切换、通知、用户菜单）
- ✅ 多页面标签切换（Tab Bar）
- ✅ 页面过渡动画
- ✅ 响应式设计

### 2. **UI 组件升级**
- 所有页面组件已迁移到 Naive UI
- 更流畅的用户体验
- 更优雅的视觉设计
- 更好的性能表现

### 3. **布局特点**
- **侧边栏**：
  - 可折叠展开
  - 图标 + 文字导航
  - 渐变色 Logo
  - 折叠时显示简化图标

- **顶部栏**：
  - 面包屑导航
  - 语言切换（中文/英文）
  - 通知徽章
  - 用户下拉菜单

- **标签栏**：
  - 多页面标签管理
  - 支持关闭标签
  - 点击切换页面

- **底部栏**：
  - 版权信息
  - 快捷链接

## 📦 安装依赖

进入 Vue 项目目录并安装新的依赖：

```bash
cd app/vue
pnpm install
```

或使用 npm：

```bash
npm install
```

## 🚀 运行项目

### 开发模式

```bash
pnpm run dev
```

或

```bash
npm run dev
```

默认访问地址：http://localhost:5173

### 生产构建

```bash
pnpm run build
```

或

```bash
npm run build
```

## 📝 主要变更

### 依赖变更

#### 移除的依赖
- ❌ `element-plus`
- ❌ `@element-plus/icons-vue`

#### 新增的依赖
- ✅ `naive-ui` - 主 UI 框架
- ✅ `@vicons/ionicons5` - Ionicons 图标库
- ✅ `@vicons/antd` - Ant Design 图标库

### 文件变更

#### 修改的文件
- `package.json` - 依赖更新
- `src/main.js` - Naive UI 初始化
- `src/App.vue` - 配置 Naive UI Provider
- `src/layouts/MainLayout.vue` - 全新布局实现
- `src/views/Dashboard.vue` - 使用 Naive UI 组件
- `src/views/Upload.vue` - 使用 Naive UI 组件
- `src/views/Graph.vue` - 使用 Naive UI 组件
- `src/views/Query.vue` - 使用 Naive UI 组件
- `src/views/Status.vue` - 使用 Naive UI 组件
- `src/styles/main.scss` - 样式优化

## 🎨 设计亮点

### 1. 配色方案
- **主色调**：渐变紫蓝色 `#667eea` → `#764ba2`
- **成功色**：绿色 `#18a058`
- **信息色**：蓝色 `#2080f0`
- **警告色**：橙色 `#f0a020`
- **错误色**：红色 `#d03050`

### 2. 图标系统
使用 Ionicons 5 图标库，包括：
- `StatsChartOutline` - 仪表板
- `CloudUploadOutline` - 上传
- `GitNetworkOutline` - 图谱
- `SearchOutline` - 查询
- `TimeOutline` - 状态
- 等等...

### 3. 交互设计
- **悬停效果**：卡片悬停放大
- **过渡动画**：页面切换淡入淡出
- **加载状态**：Spin 加载动画
- **消息提示**：优雅的 Message 组件

## 📚 Naive UI 文档

官方文档：https://www.naiveui.com/

中文文档：https://www.naiveui.com/zh-CN/

## 🔧 开发技巧

### 1. 使用 Message
```javascript
import { useMessage } from 'naive-ui'

const message = useMessage()
message.success('操作成功')
message.error('操作失败')
message.warning('警告信息')
message.info('提示信息')
```

### 2. 使用 Dialog
```javascript
import { useDialog } from 'naive-ui'

const dialog = useDialog()
dialog.warning({
  title: '警告',
  content: '你确定吗？',
  positiveText: '确定',
  negativeText: '取消',
  onPositiveClick: () => {
    // 确定操作
  }
})
```

### 3. 使用 Notification
```javascript
import { useNotification } from 'naive-ui'

const notification = useNotification()
notification.create({
  title: '通知',
  content: '这是一条通知消息',
  duration: 3000
})
```

## 🐛 常见问题

### Q: 安装依赖时出错？
A: 尝试删除 `node_modules` 和 `pnpm-lock.yaml`（或 `package-lock.json`），然后重新安装：
```bash
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Q: 页面样式异常？
A: 确保浏览器缓存已清除，或使用无痕模式访问。

### Q: 图标不显示？
A: 检查网络连接，确保可以访问 CDN 资源。

## 🎯 下一步计划

- [ ] 添加深色主题支持
- [ ] 实现更多自定义主题
- [ ] 添加更多页面模板
- [ ] 优化移动端体验
- [ ] 添加更多图表可视化

## 📄 参考资源

- [Naive UI 官方文档](https://www.naiveui.com/)
- [Naive UI Admin 模板](https://github.com/jekip/naive-ui-admin)
- [Vicons 图标库](https://www.xicons.org/)
- [Vue 3 文档](https://vuejs.org/)

---

**升级日期**: 2024-11-08
**升级版本**: v2.0.0
**负责人**: AI Assistant

