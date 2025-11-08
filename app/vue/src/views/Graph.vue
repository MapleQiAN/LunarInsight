<template>
  <div class="graph">
    <n-page-header :title="t('graph.title')" />

    <n-card>
      <n-space :size="16" style="margin-bottom: 20px">
        <n-input-number
          v-model:value="nodeLimit"
          :min="10"
          :max="1000"
          :step="10"
          style="width: 150px"
        >
          <template #prefix>
            {{ t('graph.node_limit') }}:
          </template>
        </n-input-number>
        
        <n-button type="primary" :loading="loading" @click="loadGraph">
          <template #icon>
            <n-icon><refresh-outline /></n-icon>
          </template>
          {{ t('graph.load_graph') }}
        </n-button>
      </n-space>

      <div v-if="graphData" style="margin-bottom: 20px">
        <n-space :size="12">
          <n-tag type="info" :bordered="false">
            {{ t('graph.nodes') }}: {{ graphData.nodes.length }}
          </n-tag>
          <n-tag type="success" :bordered="false">
            {{ t('graph.edges') }}: {{ graphData.edges.length }}
          </n-tag>
        </n-space>
      </div>

      <div ref="graphContainer" class="graph-container"></div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
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
let cy = null

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
          'width': 30,
          'height': 30,
          'text-valign': 'center',
          'text-halign': 'center',
          'font-size': '12px',
          'font-family': 'Noto Serif SC, sans-serif'
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
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#94a3b8',
          'target-arrow-color': '#94a3b8',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'label': 'data(label)',
          'font-size': '10px'
        }
      }
    ],
    layout: {
      name: 'dagre',
      rankDir: 'TB',
      spacingFactor: 1.5
    }
  })
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
.graph {
  .graph-container {
    width: 100%;
    height: 700px;
    border: 1px solid #efeff5;
    border-radius: 8px;
    background: #fafafa;
  }
}
</style>
