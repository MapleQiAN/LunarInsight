<template>
  <div class="dashboard-page">
    <!-- Header Section -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">月悟·镜</h1>
        <p class="page-subtitle">知识图谱洞察仪表盘 · Knowledge Graph Insights Dashboard</p>
      </div>
      <div class="header-actions">
        <n-button type="primary" @click="refreshStats" :loading="loading">
          <template #icon>
            <n-icon><refresh-outline /></n-icon>
          </template>
          刷新数据
        </n-button>
        <n-button @click="$router.push('/knowledge')">
          <template #icon>
            <n-icon><cloud-upload-outline /></n-icon>
          </template>
          知识构建
        </n-button>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="stats-grid">
      <div class="stat-card" :style="{ '--card-color': '#d4af37' }">
        <div class="stat-icon" style="background: linear-gradient(135deg, #d4af37, #c9a668);">
          <n-icon size="32"><document-text-outline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">文档总数</div>
          <div class="stat-value">
            <n-number-animation :from="0" :to="stats.totalDocuments" :duration="1000" />
          </div>
          <div class="stat-footer">
            <span class="stat-desc">PDF · Markdown · EPUB</span>
          </div>
        </div>
      </div>

      <div class="stat-card" :style="{ '--card-color': '#c9a668' }">
        <div class="stat-icon" style="background: linear-gradient(135deg, #c9a668, #b8860b);">
          <n-icon size="32"><bulb-outline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">概念节点</div>
          <div class="stat-value">
            <n-number-animation :from="0" :to="stats.totalConcepts" :duration="1000" />
          </div>
          <div class="stat-footer">
            <span class="stat-desc">知识体系构建中</span>
          </div>
        </div>
      </div>

      <div class="stat-card" :style="{ '--card-color': '#b8860b' }">
        <div class="stat-icon" style="background: linear-gradient(135deg, #b8860b, #9a7509);">
          <n-icon size="32"><git-network-outline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">关系连接</div>
          <div class="stat-value">
            <n-number-animation :from="0" :to="stats.totalRelations" :duration="1000" />
          </div>
          <div class="stat-footer">
            <span class="stat-desc">知识关联网络</span>
          </div>
        </div>
      </div>

      <div class="stat-card" :style="{ '--card-color': '#daa520' }">
        <div class="stat-icon" style="background: linear-gradient(135deg, #daa520, #c9a668);">
          <n-icon size="32"><analytics-outline /></n-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">图谱密度</div>
          <div class="stat-value">
            <n-number-animation :from="0" :to="graphDensity" :duration="1000" :precision="2" />%
          </div>
          <div class="stat-footer">
            <n-icon :component="TrendingUpOutline" class="trend-icon" />
            <span class="stat-desc trend-up">持续增长</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts and Info Section -->
    <div class="content-grid">
      <!-- Left: Relation Type Distribution -->
      <div class="chart-section">
        <div class="section-header">
          <n-icon size="20"><pie-chart-outline /></n-icon>
          <h3>关系类型分布</h3>
        </div>
        <div class="chart-container">
          <v-chart v-if="!loading && pieChartOption.series[0].data.length > 0" :option="pieChartOption" autoresize />
          <n-empty v-else-if="!loading" description="暂无数据" size="small" />
          <n-spin v-else size="small" />
        </div>
      </div>

      <!-- Middle: Top Concepts -->
      <div class="info-section">
        <div class="section-header">
          <n-icon size="20"><trophy-outline /></n-icon>
          <h3>核心概念排行</h3>
        </div>
        <div class="concepts-list">
          <n-scrollbar style="max-height: 350px;">
            <div v-if="stats.topConcepts && stats.topConcepts.length > 0">
              <div 
                v-for="(concept, index) in stats.topConcepts" 
                :key="index" 
                class="concept-item"
              >
                <div class="concept-rank" :class="`rank-${index + 1}`">{{ index + 1 }}</div>
                <div class="concept-info">
                  <div class="concept-name">{{ concept.name }}</div>
                  <div class="concept-domain" v-if="concept.domain">{{ concept.domain }}</div>
                </div>
                <div class="concept-connections">
                  <n-tag :bordered="false" type="warning" size="small">
                    {{ concept.connections }} 连接
                  </n-tag>
                </div>
              </div>
            </div>
            <n-empty v-else description="暂无概念数据" size="small" />
          </n-scrollbar>
        </div>
      </div>

      <!-- Right: Quick Actions -->
      <div class="actions-section">
        <div class="section-header">
          <n-icon size="20"><rocket-outline /></n-icon>
          <h3>快速操作</h3>
        </div>
        <div class="quick-actions">
          <div class="action-card" @click="$router.push('/knowledge')">
            <div class="action-icon" style="background: linear-gradient(135deg, #d4af37, #b8860b);">
              <n-icon size="28"><cloud-upload-outline /></n-icon>
            </div>
            <div class="action-content">
              <div class="action-title">知识构建</div>
              <div class="action-desc">导入文档/文本构建知识</div>
            </div>
            <n-icon class="action-arrow" size="16"><arrow-forward-outline /></n-icon>
          </div>

          <div class="action-card" @click="$router.push('/graph')">
            <div class="action-icon" style="background: linear-gradient(135deg, #c9a668, #9a7509);">
              <n-icon size="28"><git-network-outline /></n-icon>
            </div>
            <div class="action-content">
              <div class="action-title">图谱可视化</div>
              <div class="action-desc">探索知识关系网络</div>
            </div>
            <n-icon class="action-arrow" size="16"><arrow-forward-outline /></n-icon>
          </div>

          <div class="action-card" @click="$router.push('/query')">
            <div class="action-icon" style="background: linear-gradient(135deg, #b8860b, #8b6914);">
              <n-icon size="28"><search-outline /></n-icon>
            </div>
            <div class="action-content">
              <div class="action-title">知识查询</div>
              <div class="action-desc">使用 Cypher 查询图谱</div>
            </div>
            <n-icon class="action-arrow" size="16"><arrow-forward-outline /></n-icon>
          </div>

          <div class="action-card" @click="handleAsk">
            <div class="action-icon" style="background: linear-gradient(135deg, #daa520, #c9a668);">
              <n-icon size="28"><chatbubble-ellipses-outline /></n-icon>
            </div>
            <div class="action-content">
              <div class="action-title">智能问答</div>
              <div class="action-desc">向知识图谱提问</div>
            </div>
            <n-icon class="action-arrow" size="16"><arrow-forward-outline /></n-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Documents Table -->
    <div class="table-section">
      <div class="section-header">
        <n-icon size="20"><time-outline /></n-icon>
        <h3>最近上传的文档</h3>
      </div>
      <n-data-table
        :columns="docColumns"
        :data="stats.recentDocuments || []"
        :bordered="false"
        :single-line="false"
        :loading="loading"
      />
    </div>

    <!-- System Status -->
    <div class="status-section">
      <div class="section-header">
        <n-icon size="20"><server-outline /></n-icon>
        <h3>系统状态</h3>
      </div>
      <div class="status-grid">
        <div class="status-item">
          <div class="status-icon" style="background: linear-gradient(135deg, #52c41a, #389e0d);">
            <n-icon size="24"><server-outline /></n-icon>
          </div>
          <div class="status-content">
            <div class="status-label">Neo4j 图数据库</div>
            <n-tag :type="systemStatus.neo4j ? 'success' : 'error'" :bordered="false">
              {{ systemStatus.neo4j ? '运行中' : '离线' }}
            </n-tag>
          </div>
        </div>
        <div class="status-item">
          <div class="status-icon" style="background: linear-gradient(135deg, #ff7875, #ff4d4f);">
            <n-icon size="24"><layers-outline /></n-icon>
          </div>
          <div class="status-content">
            <div class="status-label">Redis 队列</div>
            <n-tag :type="systemStatus.redis ? 'success' : 'warning'" :bordered="false">
              {{ systemStatus.redis ? '运行中' : '未配置' }}
            </n-tag>
          </div>
        </div>
        <div class="status-item">
          <div class="status-icon" style="background: linear-gradient(135deg, #40a9ff, #1890ff);">
            <n-icon size="24"><cube-outline /></n-icon>
          </div>
          <div class="status-content">
            <div class="status-label">向量检索</div>
            <n-tag type="info" :bordered="false">
              {{ systemStatus.vector }}
            </n-tag>
          </div>
        </div>
        <div class="status-item">
          <div class="status-icon" style="background: linear-gradient(135deg, #b37feb, #9254de);">
            <n-icon size="24"><sparkles-outline /></n-icon>
          </div>
          <div class="status-content">
            <div class="status-label">LLM 服务</div>
            <n-tag :type="systemStatus.llm ? 'success' : 'warning'" :bordered="false">
              {{ systemStatus.llm ? '已配置' : 'Mock模式' }}
            </n-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { 
  NButton, 
  NIcon, 
  NNumberAnimation, 
  NSpin, 
  NEmpty,
  NTag,
  NDataTable,
  NScrollbar,
  useMessage
} from 'naive-ui'
import {
  RefreshOutline,
  CloudUploadOutline,
  DocumentTextOutline,
  BulbOutline,
  GitNetworkOutline,
  AnalyticsOutline,
  TrendingUpOutline,
  PieChartOutline,
  TrophyOutline,
  RocketOutline,
  ArrowForwardOutline,
  SearchOutline,
  ChatbubbleEllipsesOutline,
  TimeOutline,
  ServerOutline,
  LayersOutline,
  CubeOutline,
  SparklesOutline
} from '@vicons/ionicons5'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import { getDashboardStats } from '@/api/services'

use([
  CanvasRenderer,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent
])

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const stats = ref({
  totalDocuments: 0,
  totalConcepts: 0,
  totalRelations: 0,
  recentDocuments: [],
  topConcepts: [],
  relationTypes: []
})

const systemStatus = ref({
  neo4j: true,
  redis: false,
  vector: 'FAISS',
  llm: false
})

// Computed
const graphDensity = computed(() => {
  if (stats.value.totalConcepts === 0) return 0
  const maxPossibleEdges = stats.value.totalConcepts * (stats.value.totalConcepts - 1)
  if (maxPossibleEdges === 0) return 0
  return (stats.value.totalRelations / maxPossibleEdges * 100)
})

// Pie Chart Option
const pieChartOption = computed(() => {
  const data = stats.value.relationTypes.map(rt => ({
    value: rt.count,
    name: rt.type
  }))

  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: {
        color: '#666'
      }
    },
    series: [
      {
        name: '关系类型',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 18,
            fontWeight: 'bold',
            color: '#d4af37'
          }
        },
        labelLine: {
          show: false
        },
        data: data,
        color: ['#d4af37', '#c9a668', '#b8860b', '#daa520', '#8b6914']
      }
    ]
  }
})

// Document Table Columns
const docColumns = [
  {
    title: '文件名',
    key: 'filename',
    ellipsis: {
      tooltip: true
    },
    render: (row) => {
      return h('div', { style: 'display: flex; align-items: center; gap: 8px;' }, [
        h(NIcon, { size: 18, color: '#d4af37' }, { default: () => h(DocumentTextOutline) }),
        h('span', { style: 'font-weight: 500;' }, row.filename || '未命名文档')
      ])
    }
  },
  {
    title: '类型',
    key: 'kind',
    width: 100,
    render: (row) => {
      const typeMap = {
        pdf: { text: 'PDF', type: 'error' },
        md: { text: 'Markdown', type: 'info' },
        docx: { text: 'Word', type: 'primary' },
        epub: { text: 'EPUB', type: 'success' }
      }
      const config = typeMap[row.kind] || { text: row.kind?.toUpperCase() || 'UNKNOWN', type: 'default' }
      return h(NTag, { type: config.type, size: 'small', bordered: false }, { default: () => config.text })
    }
  },
  {
    title: '文档ID',
    key: 'id',
    width: 150,
    ellipsis: {
      tooltip: true
    },
    render: (row) => {
      return h('code', { style: 'font-size: 12px; color: #666;' }, row.id || 'N/A')
    }
  },
  {
    title: '上传时间',
    key: 'createdAt',
    width: 180,
    render: (row) => {
      if (!row.createdAt) return '未知'
      const date = new Date(row.createdAt)
      return date.toLocaleString('zh-CN')
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => {
      return h('div', { style: 'display: flex; gap: 8px;' }, [
        h(NButton, {
          size: 'small',
          type: 'primary',
          text: true,
          onClick: () => handleViewDocument(row)
        }, { default: () => '查看' }),
        h(NButton, {
          size: 'small',
          type: 'error',
          text: true,
          onClick: () => handleDeleteDocument(row)
        }, { default: () => '删除' })
      ])
    }
  }
]

// Methods
const loadStats = async () => {
  loading.value = true
  try {
    const data = await getDashboardStats()
    stats.value = {
      totalDocuments: data.totalDocuments || 0,
      totalConcepts: data.totalConcepts || 0,
      totalRelations: data.totalRelations || 0,
      recentDocuments: data.recentDocuments || [],
      topConcepts: data.topConcepts || [],
      relationTypes: data.relationTypes || []
    }
    
    // Update system status based on data
    systemStatus.value.neo4j = data.totalDocuments >= 0 // If we got data, Neo4j is running
    
    // message.success('数据加载成功')
  } catch (error) {
    message.error('加载统计数据失败')
    console.error('Failed to load stats:', error)
  } finally {
    loading.value = false
  }
}

const refreshStats = () => {
  loadStats()
}

const handleAsk = () => {
  message.info('智能问答功能开发中...')
}

const handleViewDocument = (row) => {
  message.info(`查看文档: ${row.filename}`)
}

const handleDeleteDocument = (row) => {
  message.warning(`删除功能开发中: ${row.filename}`)
}

// Lifecycle
onMounted(() => {
  loadStats()
})
</script>

<style lang="scss" scoped>
.dashboard-page {
  padding: 32px 48px;
  background: #f5f7fa;
  min-height: calc(100vh - 70px);
  position: relative;

  &::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: 
      radial-gradient(circle at 20% 20%, rgba(212, 175, 55, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(218, 165, 32, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(184, 134, 11, 0.03) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  > * {
    position: relative;
    z-index: 1;
  }

  // 统一按钮样式 - 移除所有默认边框颜色
  :deep(.n-button) {
    border: none !important;
    
    &:focus {
      outline: none;
      box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.2);
    }
  }

  :deep(.n-button--primary-type) {
    background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%) !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(212, 175, 55, 0.3);
    color: white;
    
    &:hover {
      background: linear-gradient(135deg, #c9a668 0%, #9a7509 100%) !important;
      box-shadow: 0 4px 12px rgba(212, 175, 55, 0.4);
      transform: translateY(-1px);
    }
    
    &:active {
      background: linear-gradient(135deg, #b8860b 0%, #8b6914 100%) !important;
      transform: translateY(0);
    }
    
    &:focus {
      outline: none;
      box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.3);
    }
  }

  :deep(.n-button--default-type) {
    background: white;
    border: 1px solid #e0e0e0 !important;
    color: #666;
    
    &:hover {
      background: #fafafa;
      border-color: #d4af37 !important;
      color: #d4af37;
      transform: translateY(-1px);
    }
    
    &:active {
      background: #f0f0f0;
      transform: translateY(0);
    }
    
    &:focus {
      outline: none;
      border-color: #d4af37 !important;
      box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.2);
    }
  }

  :deep(.n-button--text-type) {
    color: #d4af37;
    border: none !important;
    
    &:hover {
      background: rgba(212, 175, 55, 0.1);
      color: #b8860b;
    }
    
    &:active {
      background: rgba(212, 175, 55, 0.2);
    }
  }

  :deep(.n-button--error-type) {
    color: #ff4d4f;
    
    &:hover {
      background: rgba(255, 77, 79, 0.1);
      color: #cf1322;
    }
  }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.header-content {
  flex: 1;

  .page-title {
    font-size: 32px;
    font-weight: 700;
    margin: 0 0 8px 0;
    background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .page-subtitle {
    font-size: 14px;
    color: #666;
    margin: 0;
  }
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  border: 2px solid transparent;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  cursor: pointer;

  &:hover {
    border-color: var(--card-color);
    box-shadow: 0 4px 20px rgba(212, 175, 55, 0.3);
    transform: translateY(-4px);
  }

  .stat-icon {
    width: 64px;
    height: 64px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(212, 175, 55, 0.3);
  }

  .stat-content {
    flex: 1;
    min-width: 0;

    .stat-label {
      font-size: 14px;
      color: #999;
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 32px;
      font-weight: 700;
      color: #333;
      line-height: 1;
      margin-bottom: 8px;
    }

    .stat-footer {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;

      .stat-desc {
        color: #666;

        &.trend-up {
          color: #52c41a;
          font-weight: 600;
        }
      }

      .trend-icon {
        color: #52c41a;
      }
    }
  }
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 24px;
  margin-bottom: 32px;
}

.chart-section,
.info-section,
.actions-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 2px solid transparent;
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba(212, 175, 55, 0.3);
    box-shadow: 0 4px 20px rgba(212, 175, 55, 0.15);
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid #f0f0f0;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }

    .n-icon {
      color: #d4af37;
    }
  }
}

.chart-container {
  height: 350px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.concepts-list {
  .concept-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 8px;
    background: #fafafa;
    transition: all 0.2s ease;

    &:hover {
      background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(184, 134, 11, 0.1));
      transform: translateX(4px);
    }

    .concept-rank {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 14px;
      background: #e0e0e0;
      color: #666;

      &.rank-1 {
        background: linear-gradient(135deg, #d4af37, #b8860b);
        color: white;
      }

      &.rank-2 {
        background: linear-gradient(135deg, #c9a668, #9a7509);
        color: white;
      }

      &.rank-3 {
        background: linear-gradient(135deg, #daa520, #c9a668);
        color: white;
      }
    }

    .concept-info {
      flex: 1;
      min-width: 0;

      .concept-name {
        font-weight: 600;
        font-size: 14px;
        color: #333;
        margin-bottom: 4px;
      }

      .concept-domain {
        font-size: 12px;
        color: #999;
      }
    }

    .concept-connections {
      flex-shrink: 0;
    }
  }
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;

  .action-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    border-radius: 12px;
    background: #fafafa;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 2px solid transparent;

    &:hover {
      background: white;
      border-color: rgba(212, 175, 55, 0.5);
      box-shadow: 0 4px 16px rgba(212, 175, 55, 0.2);
      transform: translateX(4px);

      .action-arrow {
        transform: translateX(4px);
      }
    }

    .action-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(212, 175, 55, 0.3);
    }

    .action-content {
      flex: 1;

      .action-title {
        font-weight: 600;
        font-size: 14px;
        color: #333;
        margin-bottom: 4px;
      }

      .action-desc {
        font-size: 12px;
        color: #999;
      }
    }

    .action-arrow {
      color: #d4af37;
      transition: transform 0.3s ease;
    }
  }
}

.table-section,
.status-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 2px solid transparent;
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba(212, 175, 55, 0.3);
    box-shadow: 0 4px 20px rgba(212, 175, 55, 0.15);
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid #f0f0f0;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }

    .n-icon {
      color: #d4af37;
    }
  }
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;

  .status-item {
    padding: 20px;
    background: white;
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 16px;
    transition: all 0.3s ease;
    border: 2px solid transparent;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

    &:hover {
      border-color: rgba(212, 175, 55, 0.3);
      box-shadow: 0 4px 16px rgba(212, 175, 55, 0.2);
      transform: translateY(-2px);
    }

    .status-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .status-content {
      flex: 1;
      display: flex;
      justify-content: space-between;
      align-items: center;
      min-width: 0;

      .status-label {
        font-size: 14px;
        font-weight: 600;
        color: #333;
      }
    }
  }
}

:deep(.n-data-table) {
  .n-data-table-th {
    background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(184, 134, 11, 0.1));
    color: #d4af37;
    font-weight: 600;
  }

  .n-data-table-tr:hover {
    background: linear-gradient(135deg, rgba(212, 175, 55, 0.05), rgba(184, 134, 11, 0.05));
  }
}

@media (max-width: 1440px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .status-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 16px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    
    button {
      flex: 1;
    }
  }
}
</style>
