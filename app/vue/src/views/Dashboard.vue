<template>
  <div class="dashboard">
    <el-card shadow="never" class="page-header">
      <h2>{{ t('dashboard.title') }}</h2>
    </el-card>

    <el-card shadow="never" v-loading="loading" class="metrics-card">
      <template #header>
        <span>{{ t('dashboard.key_metrics') }}</span>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="metric-card metric-blue">
            <div class="metric-label">{{ t('dashboard.total_nodes') }}</div>
            <div class="metric-value">{{ stats.totalNodes.toLocaleString() }}</div>
            <div class="metric-subtitle">Total Nodes</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card metric-green">
            <div class="metric-label">{{ t('dashboard.total_edges') }}</div>
            <div class="metric-value">{{ stats.totalEdges.toLocaleString() }}</div>
            <div class="metric-subtitle">Total Relationships</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card metric-yellow">
            <div class="metric-label">{{ t('dashboard.concepts') }}</div>
            <div class="metric-value">{{ stats.concepts.toLocaleString() }}</div>
            <div class="metric-subtitle">Concepts</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card metric-gray">
            <div class="metric-label">{{ t('dashboard.documents') }}</div>
            <div class="metric-value">{{ stats.documents.toLocaleString() }}</div>
            <div class="metric-subtitle">Documents</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <span>{{ t('dashboard.quick_actions') }}</span>
          </template>
          <el-space direction="vertical" style="width: 100%">
            <el-button type="primary" @click="$router.push('/upload')" style="width: 100%">
              <el-icon><Upload /></el-icon>
              {{ t('dashboard.upload_document') }}
            </el-button>
            <el-button @click="$router.push('/graph')" style="width: 100%">
              <el-icon><Share /></el-icon>
              {{ t('dashboard.view_graph') }}
            </el-button>
            <el-button @click="$router.push('/query')" style="width: 100%">
              <el-icon><Search /></el-icon>
              {{ t('dashboard.execute_query') }}
            </el-button>
          </el-space>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <span>{{ t('dashboard.system_status') }}</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item :label="t('dashboard.api_service')">
              <el-tag type="success">运行中</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('dashboard.graph_database')">
              <el-tag type="success">已连接</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('dashboard.processing_engine')">
              <el-tag type="info">就绪</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" v-if="nodeDistribution.length > 0" style="margin-top: 20px">
      <template #header>
        <span>{{ t('dashboard.node_distribution') }}</span>
      </template>
      <el-table :data="nodeDistribution" style="width: 100%">
        <el-table-column prop="type" :label="t('dashboard.type')" />
        <el-table-column prop="count" :label="t('dashboard.count')" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getNodes, getEdges } from '@/api/services'
import { Upload, Share, Search } from '@element-plus/icons-vue'

const { t } = useI18n()
const loading = ref(false)
const stats = ref({
  totalNodes: 0,
  totalEdges: 0,
  concepts: 0,
  documents: 0
})
const nodeDistribution = ref([])

const loadStats = async () => {
  loading.value = true
  try {
    const [nodesResult, edgesResult] = await Promise.all([
      getNodes(null, 1000),
      getEdges(null, 1000)
    ])

    const nodes = Array.isArray(nodesResult) ? nodesResult : []
    const edges = Array.isArray(edgesResult) ? edgesResult : []

    stats.value.totalNodes = nodes.length
    stats.value.totalEdges = edges.length
    stats.value.concepts = nodes.filter(n => n.labels?.includes('Concept')).length
    stats.value.documents = nodes.filter(n => n.labels?.includes('Document')).length

    // Node distribution
    const distribution = {}
    nodes.forEach(node => {
      const labels = node.labels || ['Other']
      labels.forEach(label => {
        distribution[label] = (distribution[label] || 0) + 1
      })
    })
    nodeDistribution.value = Object.entries(distribution).map(([type, count]) => ({
      type: t(`dashboard.${type.toLowerCase()}`) || type,
      count
    }))
  } catch (error) {
    console.error('Failed to load stats:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style lang="scss" scoped>
.dashboard {
  .page-header {
    margin-bottom: 20px;
    h2 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
    }
  }

  .metric-card {
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 4px solid;
    text-align: center;

    .metric-label {
      font-size: 0.875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }

    .metric-value {
      font-size: 2.5rem;
      font-weight: 700;
      margin: 0.5rem 0;
    }

    .metric-subtitle {
      font-size: 0.75rem;
      color: #64748b;
    }

    &.metric-blue {
      background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
      border-color: #3b82f6;
      color: #1e40af;
    }

    &.metric-green {
      background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
      border-color: #10b981;
      color: #166534;
    }

    &.metric-yellow {
      background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
      border-color: #d4af37;
      color: #92400e;
    }

    &.metric-gray {
      background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
      border-color: #6b7280;
      color: #374151;
    }
  }
}
</style>

