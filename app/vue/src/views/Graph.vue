<template>
  <div class="graph">
    <el-card shadow="never" class="page-header">
      <h2>{{ t('graph.title') }}</h2>
    </el-card>

    <el-card shadow="never">
      <el-form :inline="true" style="margin-bottom: 20px">
        <el-form-item :label="t('graph.node_limit')">
          <el-input-number v-model="nodeLimit" :min="10" :max="1000" :step="10" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="loadGraph">
            {{ t('graph.load_graph') }}
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="graphData" class="graph-stats" style="margin-bottom: 20px">
        <el-tag>{{ t('graph.nodes') }}: {{ graphData.nodes.length }}</el-tag>
        <el-tag style="margin-left: 10px">{{ t('graph.edges') }}: {{ graphData.edges.length }}</el-tag>
      </div>

      <div ref="graphContainer" class="graph-container"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { getGraphData } from '@/api/services'

cytoscape.use(dagre)

const { t } = useI18n()
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
      ElMessage.warning(t('graph.no_data'))
      return
    }

    let nodes = []
    let edges = []
    const nodeMap = new Map()

    // Handle different response formats
    if (result.nodes && result.edges) {
      // Format: {nodes: [], edges: []}
      nodes = result.nodes
      edges = result.edges
    } else if (Array.isArray(result)) {
      // Format: Array of query results
      result.forEach(item => {
        // Extract nodes and edges from query result
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
      ElMessage.warning(t('graph.no_nodes'))
      return
    }

    await nextTick()
    renderGraph()
    ElMessage.success(t('graph.loaded', { nodes: nodes.length, edges: edges.length }))
  } catch (error) {
    ElMessage.error(t('common.error'))
    console.error('Failed to load graph:', error)
  } finally {
    loading.value = false
  }
}

const renderGraph = () => {
  if (!graphContainer.value || !graphData.value) return

  // Destroy existing instance
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
          'background-color': '#0ea5e9',
          'label': 'data(label)',
          'width': 30,
          'height': 30,
          'text-valign': 'center',
          'text-halign': 'center',
          'font-size': '12px',
          'font-family': 'Noto Serif SC, serif'
        }
      },
      {
        selector: 'node.Concept',
        style: {
          'background-color': '#0ea5e9'
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
          'background-color': '#d4af37'
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
  .page-header {
    margin-bottom: 20px;
    h2 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
    }
  }

  .graph-container {
    width: 100%;
    height: 700px;
    border: 1px solid #e4e7ed;
    border-radius: 4px;
    background: #f8fafc;
  }
}
</style>

