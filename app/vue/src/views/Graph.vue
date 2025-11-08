<template>
  <div class="graph-page">
    <!-- Enhanced Header -->
    <div class="graph-header">
      <div>
        <h1 class="graph-title">
          <n-gradient-text type="success">
            {{ t('graph.title') }}
          </n-gradient-text>
        </h1>
        <p class="graph-subtitle">交互式知识图谱可视化</p>
      </div>
    </div>

    <n-card class="graph-card" :bordered="false">
      <!-- Control Panel -->
      <div class="control-panel">
        <n-space :size="16" align="center">
          <!-- Node Limit -->
          <div class="control-item">
            <n-icon size="20" :component="LayersOutline" class="control-icon" />
            <n-input-number
              v-model:value="nodeLimit"
              :min="10"
              :max="1000"
              :step="10"
              style="width: 160px"
            >
              <template #prefix>
                {{ t('graph.node_limit') }}
              </template>
            </n-input-number>
          </div>

          <!-- Layout Type -->
          <div class="control-item">
            <n-icon size="20" :component="GridOutline" class="control-icon" />
            <n-select
              v-model:value="layoutType"
              :options="layoutOptions"
              style="width: 140px"
              @update:value="handleLayoutChange"
            />
          </div>

          <!-- Load Button -->
          <n-button type="primary" :loading="loading" @click="loadGraph" size="large">
            <template #icon>
              <n-icon><refresh-outline /></n-icon>
            </template>
            {{ t('graph.load_graph') }}
          </n-button>

          <n-divider vertical />

          <!-- Graph Controls -->
          <n-button-group>
            <n-button @click="zoomIn" :disabled="!cy">
              <template #icon>
                <n-icon><add-outline /></n-icon>
              </template>
            </n-button>
            <n-button @click="zoomOut" :disabled="!cy">
              <template #icon>
                <n-icon><remove-outline /></n-icon>
              </template>
            </n-button>
            <n-button @click="fitView" :disabled="!cy">
              <template #icon>
                <n-icon><expand-outline /></n-icon>
              </template>
            </n-button>
            <n-button @click="resetView" :disabled="!cy">
              <template #icon>
                <n-icon><contract-outline /></n-icon>
              </template>
            </n-button>
          </n-button-group>

          <!-- Export -->
          <n-button @click="exportGraph" :disabled="!cy">
            <template #icon>
              <n-icon><download-outline /></n-icon>
            </template>
            导出
          </n-button>
        </n-space>
      </div>

      <!-- Stats Bar -->
      <div v-if="graphData" class="stats-bar">
        <div class="stat-item stat-blue">
          <n-icon size="20" :component="CubeOutline" />
          <span class="stat-label">{{ t('graph.nodes') }}</span>
          <n-number-animation :from="0" :to="graphData.nodes.length" :duration="1000" class="stat-value" />
        </div>
        <div class="stat-item stat-green">
          <n-icon size="20" :component="GitNetworkOutline" />
          <span class="stat-label">{{ t('graph.edges') }}</span>
          <n-number-animation :from="0" :to="graphData.edges.length" :duration="1000" class="stat-value" />
        </div>
        <div class="stat-item stat-yellow" v-if="selectedNode">
          <n-icon size="20" :component="InformationCircleOutline" />
          <span class="stat-label">已选择</span>
          <span class="stat-value">{{ selectedNode.label }}</span>
        </div>
      </div>

      <!-- Graph Container -->
      <div class="graph-wrapper">
        <div ref="graphContainer" class="graph-container"></div>
        
        <!-- Legend -->
        <div class="graph-legend">
          <div class="legend-title">节点类型</div>
          <div class="legend-items">
            <div class="legend-item">
              <div class="legend-color" style="background: #2080f0"></div>
              <span>概念 (Concept)</span>
            </div>
            <div class="legend-item">
              <div class="legend-color" style="background: #2d3748"></div>
              <span>文档 (Document)</span>
            </div>
            <div class="legend-item">
              <div class="legend-color" style="background: #f0a020"></div>
              <span>实体 (Entity)</span>
            </div>
            <div class="legend-item">
              <div class="legend-color" style="background: #18a058"></div>
              <span>其他 (Other)</span>
            </div>
          </div>
        </div>

        <!-- Loading Overlay -->
        <div v-if="loading" class="loading-overlay">
          <n-spin size="large">
            <template #description>
              <div class="loading-text">正在加载图谱数据...</div>
            </template>
          </n-spin>
        </div>

        <!-- Empty State -->
        <div v-if="!loading && !graphData" class="empty-state">
          <n-empty :description="t('graph.no_data')" size="huge">
            <template #icon>
              <n-icon size="80" :component="GitNetworkOutline" style="opacity: 0.3" />
            </template>
            <template #extra>
              <n-button type="primary" @click="$router.push('/upload')">
                上传文档开始
              </n-button>
            </template>
          </n-empty>
        </div>
      </div>

      <!-- Node Detail Panel -->
      <n-drawer v-model:show="showNodeDetail" :width="400" placement="right">
        <n-drawer-content title="节点详情">
          <div v-if="selectedNode" class="node-detail">
            <n-descriptions :column="1" bordered>
              <n-descriptions-item label="ID">
                <n-text code>{{ selectedNode.id }}</n-text>
              </n-descriptions-item>
              <n-descriptions-item label="标签">
                <n-tag type="info" size="small">{{ selectedNode.label }}</n-tag>
              </n-descriptions-item>
              <n-descriptions-item v-for="(value, key) in selectedNode.properties" :key="key" :label="key">
                {{ value }}
              </n-descriptions-item>
            </n-descriptions>
          </div>
        </n-drawer-content>
      </n-drawer>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import {
  RefreshOutline,
  LayersOutline,
  GridOutline,
  AddOutline,
  RemoveOutline,
  ExpandOutline,
  ContractOutline,
  DownloadOutline,
  CubeOutline,
  GitNetworkOutline,
  InformationCircleOutline
} from '@vicons/ionicons5'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { getGraphData } from '@/api/services'

cytoscape.use(dagre)

const { t } = useI18n()
const message = useMessage()
const nodeLimit = ref(100)
const loading = ref(false)
const graphContainer = ref(null)
const graphData = ref(null)
const layoutType = ref('dagre')
const selectedNode = ref(null)
const showNodeDetail = ref(false)
let cy = null

// Layout options
const layoutOptions = [
  { label: '层级布局', value: 'dagre' },
  { label: '圆形布局', value: 'circle' },
  { label: '网格布局', value: 'grid' },
  { label: '同心圆', value: 'concentric' },
  { label: '力导向', value: 'cose' }
]

const loadGraph = async () => {
  loading.value = true
  try {
    const result = await getGraphData(nodeLimit.value)
    
    if (!result) {
      message.warning(t('graph.no_data'))
      return
    }

    let nodes = []
    let edges = []
    const nodeMap = new Map()

    // Handle different response formats
    if (result.nodes && result.edges) {
      nodes = result.nodes
      edges = result.edges
    } else if (Array.isArray(result)) {
      result.forEach(item => {
        if (item.n) {
          const nodeId = item.n.id || item.n.properties?.id || String(item.n)
          if (nodeId && !nodeMap.has(nodeId)) {
            nodeMap.set(nodeId, true)
            const props = typeof item.n === 'object' ? item.n.properties || item.n : {}
            nodes.push({
              data: {
                id: String(nodeId),
                label: props.name || props.filename || String(nodeId),
                ...props
              },
              classes: (item.n.labels || []).join(' ') || ''
            })
          }
        }
        if (item.m) {
          const nodeId = item.m.id || item.m.properties?.id || String(item.m)
          if (nodeId && !nodeMap.has(nodeId)) {
            nodeMap.set(nodeId, true)
            const props = typeof item.m === 'object' ? item.m.properties || item.m : {}
            nodes.push({
              data: {
                id: String(nodeId),
                label: props.name || props.filename || String(nodeId),
                ...props
              },
              classes: (item.m.labels || []).join(' ') || ''
            })
          }
        }
        if (item.r && item.a && item.b) {
          const source = item.a.id || item.a.properties?.id || String(item.a)
          const target = item.b.id || item.b.properties?.id || String(item.b)
          if (source && target) {
            edges.push({
              data: {
                id: `${source}-${target}-${item.r.type || 'RELATED'}`,
                source: String(source),
                target: String(target),
                label: item.r.type || 'RELATED'
              }
            })
          }
        }
      })
    }

    graphData.value = { nodes, edges }

    if (nodes.length === 0) {
      message.warning(t('graph.no_nodes'))
      return
    }

    await nextTick()
    renderGraph()
    message.success(t('graph.loaded', { nodes: nodes.length, edges: edges.length }))
  } catch (error) {
    message.error(t('common.error'))
    console.error('Failed to load graph:', error)
  } finally {
    loading.value = false
  }
}

const renderGraph = () => {
  if (!graphContainer.value || !graphData.value) return

  if (cy) {
    cy.destroy()
  }

  cy = cytoscape({
    container: graphContainer.value,
    elements: [...graphData.value.nodes, ...graphData.value.edges],
    style: [
      {
        selector: 'node',
        style: {
          'background-color': '#18a058',
          'label': 'data(label)',
          'width': 40,
          'height': 40,
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 8,
          'font-size': '12px',
          'font-weight': '500',
          'font-family': 'Noto Serif SC, sans-serif',
          'color': '#333',
          'text-background-color': '#fff',
          'text-background-opacity': 0.8,
          'text-background-padding': '4px',
          'border-width': 3,
          'border-color': '#fff',
          'box-shadow': '0 4px 8px rgba(0,0,0,0.15)'
        }
      },
      {
        selector: 'node.Concept',
        style: {
          'background-color': '#2080f0'
        }
      },
      {
        selector: 'node.Document',
        style: {
          'background-color': '#2d3748'
        }
      },
      {
        selector: 'node.Entity',
        style: {
          'background-color': '#f0a020'
        }
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 4,
          'border-color': '#6366f1',
          'width': 50,
          'height': 50
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#cbd5e1',
          'target-arrow-color': '#cbd5e1',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'label': 'data(label)',
          'font-size': '10px',
          'text-background-color': '#fff',
          'text-background-opacity': 0.8,
          'text-background-padding': '2px'
        }
      },
      {
        selector: 'edge:selected',
        style: {
          'width': 3,
          'line-color': '#6366f1',
          'target-arrow-color': '#6366f1'
        }
      }
    ],
    layout: {
      name: layoutType.value,
      rankDir: 'TB',
      spacingFactor: 1.5,
      animate: true,
      animationDuration: 500
    }
  })

  // Node click handler
  cy.on('tap', 'node', (evt) => {
    const node = evt.target
    selectedNode.value = {
      id: node.id(),
      label: node.data('label'),
      properties: node.data()
    }
    showNodeDetail.value = true
  })
}

// Graph control functions
const zoomIn = () => {
  if (cy) cy.zoom(cy.zoom() * 1.2)
}

const zoomOut = () => {
  if (cy) cy.zoom(cy.zoom() * 0.8)
}

const fitView = () => {
  if (cy) cy.fit(null, 50)
}

const resetView = () => {
  if (cy) {
    cy.zoom(1)
    cy.center()
  }
}

const handleLayoutChange = () => {
  if (cy && graphData.value) {
    const layout = cy.layout({
      name: layoutType.value,
      animate: true,
      animationDuration: 500,
      spacingFactor: 1.5
    })
    layout.run()
  }
}

const exportGraph = () => {
  if (!cy) return
  
  const png = cy.png({
    full: true,
    scale: 2,
    bg: '#ffffff'
  })
  
  const link = document.createElement('a')
  link.download = `knowledge-graph-${Date.now()}.png`
  link.href = png
  link.click()
  
  message.success('图谱已导出')
}

onMounted(() => {
  loadGraph()
})

onUnmounted(() => {
  if (cy) {
    cy.destroy()
  }
})
</script>

<style lang="scss" scoped>
.graph-page {
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
      radial-gradient(circle at 20% 20%, rgba(16, 185, 129, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(52, 211, 153, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(5, 150, 105, 0.03) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  > * {
    position: relative;
    z-index: 1;
  }

  // Header Section - 轻奢现代化设计
  .graph-header {
    margin-bottom: 32px;
    padding: 32px 36px;
    background: linear-gradient(135deg, 
      rgba(240, 253, 244, 0.95) 0%, 
      rgba(236, 254, 255, 0.95) 50%, 
      rgba(245, 243, 255, 0.95) 100%);
    border-radius: 24px;
    backdrop-filter: blur(20px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 8px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.6);
    position: relative;
    overflow: hidden;

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, 
        transparent, 
        rgba(16, 185, 129, 0.4), 
        transparent);
    }

    .graph-title {
      font-size: 36px;
      font-weight: 700;
      margin: 0 0 10px 0;
      letter-spacing: -0.5px;
    }

    .graph-subtitle {
      font-size: 15px;
      color: #64748b;
      margin: 0;
      font-weight: 500;
    }
  }

  .graph-card {
    border-radius: 24px;
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(10px);
    transition: all 0.3s;

    &:hover {
      box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.08),
        0 4px 16px rgba(0, 0, 0, 0.06);
    }

    :deep(.n-card__content) {
      padding: 28px;
    }
  }

  // Control Panel - 轻奢控制面板
  .control-panel {
    padding: 24px 28px;
    background: linear-gradient(135deg, 
      rgba(240, 253, 244, 0.6) 0%, 
      rgba(236, 254, 255, 0.6) 50%, 
      rgba(255, 255, 255, 0.6) 100%);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    margin-bottom: 24px;
    border: 1px solid rgba(16, 185, 129, 0.15);
    box-shadow: 
      0 4px 16px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);

    .control-item {
      display: flex;
      align-items: center;
      gap: 10px;

      .control-icon {
        color: #10b981;
        filter: drop-shadow(0 2px 4px rgba(16, 185, 129, 0.2));
      }
    }

    :deep(.n-input-number),
    :deep(.n-select) {
      border-radius: 16px;
      
      .n-input__border,
      .n-input__state-border {
        border-radius: 16px;
      }
    }

    :deep(.n-button) {
      border-radius: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      transition: all 0.3s;

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
      }
    }
  }

  // Stats Bar - 轻奢统计条
  .stats-bar {
    display: flex;
    gap: 20px;
    padding: 20px;
    background: linear-gradient(135deg, 
      rgba(255, 255, 255, 0.9) 0%, 
      rgba(248, 250, 252, 0.9) 100%);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    margin-bottom: 24px;
    border: 1px solid rgba(226, 232, 240, 0.6);
    box-shadow: 
      0 4px 16px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);

    .stat-item {
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 16px 24px;
      border-radius: 16px;
      background: linear-gradient(135deg, 
        rgba(255, 255, 255, 0.95) 0%, 
        rgba(248, 250, 252, 0.95) 100%);
      flex: 1;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        transition: width 0.3s;
      }

      &:hover {
        transform: translateY(-4px);
        box-shadow: 
          0 8px 16px rgba(0, 0, 0, 0.1),
          0 2px 8px rgba(0, 0, 0, 0.06);

        &::before {
          width: 100%;
          opacity: 0.05;
        }
      }

      &.stat-blue {
        &::before {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        }
        
        .n-icon {
          color: #3b82f6;
        }
      }

      &.stat-green {
        &::before {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        }
        
        .n-icon {
          color: #10b981;
        }
      }

      &.stat-yellow {
        &::before {
          background: linear-gradient(135deg, #f59e0b 0%, #c2a474 100%);
        }
        
        .n-icon {
          color: #f59e0b;
        }
      }

      .stat-label {
        font-size: 14px;
        color: #64748b;
        font-weight: 600;
      }

      .stat-value {
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.5px;
      }
    }
  }

  // Graph Wrapper - 企业级图谱容器
  .graph-wrapper {
    position: relative;
    height: 720px;
    border-radius: 20px;
    overflow: hidden;
    background: linear-gradient(135deg, 
      #f8fafc 0%, 
      #f1f5f9 50%, 
      #e2e8f0 100%);
    border: 1px solid rgba(226, 232, 240, 0.8);
    box-shadow: 
      inset 0 2px 8px rgba(0, 0, 0, 0.04),
      0 4px 16px rgba(0, 0, 0, 0.06);
  }

  .graph-container {
    width: 100%;
    height: 100%;
    background: #ffffff;
    position: relative;

    &::before {
      content: '';
      position: absolute;
      inset: 0;
      background: 
        radial-gradient(circle at 20% 30%, rgba(99, 102, 241, 0.03) 0%, transparent 50%),
        radial-gradient(circle at 80% 70%, rgba(16, 185, 129, 0.03) 0%, transparent 50%);
      pointer-events: none;
    }
  }

  // Graph Legend - 轻奢图例
  .graph-legend {
    position: absolute;
    bottom: 24px;
    left: 24px;
    background: linear-gradient(135deg, 
      rgba(255, 255, 255, 0.98) 0%, 
      rgba(248, 250, 252, 0.98) 100%);
    backdrop-filter: blur(20px);
    padding: 20px 24px;
    border-radius: 20px;
    box-shadow: 
      0 8px 24px rgba(0, 0, 0, 0.12),
      0 2px 8px rgba(0, 0, 0, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.6);
    z-index: 10;

    .legend-title {
      font-weight: 700;
      font-size: 15px;
      color: #0f172a;
      margin-bottom: 16px;
      letter-spacing: -0.2px;
    }

    .legend-items {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 14px;
      color: #475569;
      font-weight: 500;
      transition: all 0.2s;
      padding: 4px;
      border-radius: 8px;

      &:hover {
        background: rgba(0, 0, 0, 0.02);
        color: #1e293b;
      }

      .legend-color {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 3px solid #fff;
        box-shadow: 
          0 4px 8px rgba(0, 0, 0, 0.15),
          0 1px 4px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
      }

      &:hover .legend-color {
        transform: scale(1.1);
      }
    }
  }

  // Loading Overlay - 轻奢加载层
  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, 
      rgba(255, 255, 255, 0.98) 0%, 
      rgba(248, 250, 252, 0.98) 100%);
    backdrop-filter: blur(16px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
    border-radius: 20px;

    .loading-text {
      margin-top: 20px;
      font-size: 17px;
      color: #475569;
      font-weight: 600;
      letter-spacing: 0.3px;
    }
  }

  // Empty State
  .empty-state {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10;

    :deep(.n-empty) {
      .n-empty__icon {
        margin-bottom: 20px;
      }

      .n-empty__description {
        font-size: 16px;
        font-weight: 500;
        color: #64748b;
      }
    }
  }

  // Node Detail - 轻奢节点详情
  .node-detail {
    :deep(.n-descriptions) {
      .n-descriptions-table-content {
        padding: 12px;
      }

      .n-descriptions-table-wrapper {
        border-radius: 16px;
        overflow: hidden;
      }

      .n-descriptions-table-row {
        transition: background 0.2s;

        &:hover {
          background: rgba(0, 0, 0, 0.02);
        }
      }
    }
  }

  // Drawer 样式增强
  :deep(.n-drawer) {
    .n-drawer-header {
      padding: 24px 28px;
      font-weight: 700;
      font-size: 18px;
      letter-spacing: -0.3px;
      border-bottom: 1px solid rgba(226, 232, 240, 0.6);
    }

    .n-drawer-body-content-wrapper {
      padding: 24px 28px;
    }
  }
}

// Animations - 流畅动画
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.graph-page > * {
  animation: slideIn 0.5s ease-out;
}

// 全局按钮样式增强
:deep(.n-button) {
  border-radius: 16px;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:not(:disabled):hover {
    transform: translateY(-2px);
  }

  &.n-button--primary-type {
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);

    &:hover {
      box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
    }
  }
}

// Button Group 样式增强
:deep(.n-button-group) {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

  .n-button {
    border-radius: 0;

    &:first-child {
      border-top-left-radius: 16px;
      border-bottom-left-radius: 16px;
    }

    &:last-child {
      border-top-right-radius: 16px;
      border-bottom-right-radius: 16px;
    }
  }
}
</style>
