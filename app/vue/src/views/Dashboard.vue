<template>
  <div class="dashboard">
    <n-page-header :title="t('dashboard.title')" />

    <n-spin :show="loading">
      <n-space vertical :size="16">
        <!-- Metrics Cards -->
        <n-grid cols="1 s:2 m:4" responsive="screen" :x-gap="16" :y-gap="16">
          <n-gi>
            <n-card class="metric-card metric-blue" hoverable>
              <n-statistic :label="t('dashboard.total_nodes')" :value="stats.totalNodes">
                <template #prefix>
                  <n-icon size="24"><cube-outline /></n-icon>
                </template>
              </n-statistic>
            </n-card>
          </n-gi>
          <n-gi>
            <n-card class="metric-card metric-green" hoverable>
              <n-statistic :label="t('dashboard.total_edges')" :value="stats.totalEdges">
                <template #prefix>
                  <n-icon size="24"><git-network-outline /></n-icon>
                </template>
              </n-statistic>
            </n-card>
          </n-gi>
          <n-gi>
            <n-card class="metric-card metric-yellow" hoverable>
              <n-statistic :label="t('dashboard.concepts')" :value="stats.concepts">
                <template #prefix>
                  <n-icon size="24"><bulb-outline /></n-icon>
                </template>
              </n-statistic>
            </n-card>
          </n-gi>
          <n-gi>
            <n-card class="metric-card metric-gray" hoverable>
              <n-statistic :label="t('dashboard.documents')" :value="stats.documents">
                <template #prefix>
                  <n-icon size="24"><document-text-outline /></n-icon>
                </template>
              </n-statistic>
            </n-card>
          </n-gi>
        </n-grid>

        <!-- Quick Actions and System Status -->
        <n-grid cols="1 s:1 m:2" responsive="screen" :x-gap="16" :y-gap="16">
          <n-gi>
            <n-card :title="t('dashboard.quick_actions')">
              <n-space vertical :size="12">
                <n-button type="primary" block @click="$router.push('/upload')">
                  <template #icon>
                    <n-icon><cloud-upload-outline /></n-icon>
                  </template>
                  {{ t('dashboard.upload_document') }}
                </n-button>
                <n-button block @click="$router.push('/graph')">
                  <template #icon>
                    <n-icon><git-network-outline /></n-icon>
                  </template>
                  {{ t('dashboard.view_graph') }}
                </n-button>
                <n-button block @click="$router.push('/query')">
                  <template #icon>
                    <n-icon><search-outline /></n-icon>
                  </template>
                  {{ t('dashboard.execute_query') }}
                </n-button>
              </n-space>
            </n-card>
          </n-gi>
          
          <n-gi>
            <n-card :title="t('dashboard.system_status')">
              <n-space vertical :size="12">
                <div class="status-item">
                  <span>{{ t('dashboard.api_service') }}</span>
                  <n-tag type="success" round>运行中</n-tag>
                </div>
                <n-divider style="margin: 8px 0" />
                <div class="status-item">
                  <span>{{ t('dashboard.graph_database') }}</span>
                  <n-tag type="success" round>已连接</n-tag>
                </div>
                <n-divider style="margin: 8px 0" />
                <div class="status-item">
                  <span>{{ t('dashboard.processing_engine') }}</span>
                  <n-tag type="info" round>就绪</n-tag>
                </div>
              </n-space>
            </n-card>
          </n-gi>
        </n-grid>

        <!-- Node Distribution Table -->
        <n-card v-if="nodeDistribution.length > 0" :title="t('dashboard.node_distribution')">
          <n-data-table
            :columns="columns"
            :data="nodeDistribution"
            :pagination="false"
          />
        </n-card>
      </n-space>
    </n-spin>
  </div>
</template>

<script setup>
import { h, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { NIcon, NTag } from 'naive-ui'
import { getNodes, getEdges } from '@/api/services'
import {
  CubeOutline,
  GitNetworkOutline,
  BulbOutline,
  DocumentTextOutline,
  CloudUploadOutline,
  SearchOutline
} from '@vicons/ionicons5'

const router = useRouter()
const { t } = useI18n()
const loading = ref(false)
const stats = ref({
  totalNodes: 0,
  totalEdges: 0,
  concepts: 0,
  documents: 0
})
const nodeDistribution = ref([])

const columns = [
  {
    title: t('dashboard.type'),
    key: 'type'
  },
  {
    title: t('dashboard.count'),
    key: 'count',
    render: (row) => {
      return h(NTag, { type: 'info' }, { default: () => row.count.toLocaleString() })
    }
  }
]

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
  .metric-card {
    &.metric-blue {
      background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
      border-left: 4px solid #3b82f6;
    }

    &.metric-green {
      background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
      border-left: 4px solid #10b981;
    }

    &.metric-yellow {
      background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
      border-left: 4px solid #d4af37;
    }

    &.metric-gray {
      background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
      border-left: 4px solid #6b7280;
    }
  }

  .status-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>

