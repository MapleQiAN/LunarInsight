<template>
  <div class="query">
    <n-page-header :title="t('query.title')" />

    <n-card>
      <n-tabs v-model:value="activeTab" type="line">
        <n-tab-pane :name="'cypher'" :tab="t('query.cypher_query')">
          <n-space vertical :size="16">
            <n-input
              v-model:value="cypherQuery"
              type="textarea"
              :rows="8"
              :placeholder="t('query.cypher_help')"
            />
            
            <n-button type="primary" :loading="executing" @click="executeCypher">
              <template #icon>
                <n-icon><play-outline /></n-icon>
              </template>
              {{ t('query.execute') }}
            </n-button>
          </n-space>
        </n-tab-pane>

        <n-tab-pane :name="'nodes'" :tab="t('query.get_nodes')">
          <n-space :size="16" style="margin-bottom: 16px">
            <n-input
              v-model:value="nodeLabel"
              :placeholder="t('query.label_help')"
              clearable
              style="width: 200px"
            >
              <template #prefix>
                {{ t('query.label_optional') }}:
              </template>
            </n-input>
            
            <n-input-number
              v-model:value="nodeLimit"
              :min="1"
              :max="1000"
              style="width: 150px"
            >
              <template #prefix>
                {{ t('query.limit') }}:
              </template>
            </n-input-number>
            
            <n-button type="primary" :loading="fetchingNodes" @click="fetchNodes">
              <template #icon>
                <n-icon><search-outline /></n-icon>
              </template>
              {{ t('query.get_nodes_btn') }}
            </n-button>
          </n-space>
        </n-tab-pane>

        <n-tab-pane :name="'edges'" :tab="t('query.get_edges')">
          <n-space :size="16" style="margin-bottom: 16px">
            <n-input
              v-model:value="relType"
              :placeholder="t('query.rel_type_help')"
              clearable
              style="width: 200px"
            >
              <template #prefix>
                {{ t('query.rel_type_optional') }}:
              </template>
            </n-input>
            
            <n-input-number
              v-model:value="edgeLimit"
              :min="1"
              :max="1000"
              style="width: 150px"
            >
              <template #prefix>
                {{ t('query.limit') }}:
              </template>
            </n-input-number>
            
            <n-button type="primary" :loading="fetchingEdges" @click="fetchEdges">
              <template #icon>
                <n-icon><search-outline /></n-icon>
              </template>
              {{ t('query.get_edges_btn') }}
            </n-button>
          </n-space>
        </n-tab-pane>
      </n-tabs>

      <n-divider v-if="queryResult" />

      <div v-if="queryResult" class="query-result">
        <n-alert type="success" :show-icon="true" style="margin-bottom: 16px">
          {{ t('query.success') }}
        </n-alert>

        <n-tabs v-model:value="resultView" type="card">
          <n-tab-pane :name="'table'" :tab="t('query.view_result')">
            <n-data-table
              :columns="resultColumns"
              :data="queryResult"
              :pagination="{ pageSize: 10 }"
              :scroll-x="1200"
            />
          </n-tab-pane>
          
          <n-tab-pane :name="'json'" :tab="t('query.view_raw_json')">
            <n-code :code="JSON.stringify(queryResult, null, 2)" language="json" />
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { PlayOutline, SearchOutline } from '@vicons/ionicons5'
import { executeCypherQuery, getNodes, getEdges } from '@/api/services'

const { t } = useI18n()
const message = useMessage()

const activeTab = ref('cypher')
const cypherQuery = ref('')
const nodeLabel = ref('')
const nodeLimit = ref(100)
const relType = ref('')
const edgeLimit = ref(100)
const executing = ref(false)
const fetchingNodes = ref(false)
const fetchingEdges = ref(false)
const queryResult = ref(null)
const resultView = ref('table')

const resultColumns = computed(() => {
  if (!queryResult.value || queryResult.value.length === 0) return []
  
  const firstRow = queryResult.value[0]
  return Object.keys(firstRow).map(key => ({
    title: key,
    key: key,
    ellipsis: {
      tooltip: true
    },
    render: (row) => {
      const value = row[key]
      if (typeof value === 'object') {
        return JSON.stringify(value)
      }
      return String(value || '')
    }
  }))
})

const executeCypher = async () => {
  if (!cypherQuery.value.trim()) {
    message.warning(t('query.enter_cypher'))
    return
  }

  executing.value = true
  try {
    const result = await executeCypherQuery(cypherQuery.value)
    if (Array.isArray(result) && result.length > 0) {
      queryResult.value = result
      message.success(t('query.success'))
    } else {
      message.warning(t('query.no_results'))
      queryResult.value = null
    }
  } catch (error) {
    message.error(t('common.error') + ': ' + error.message)
    queryResult.value = null
  } finally {
    executing.value = false
  }
}

const fetchNodes = async () => {
  fetchingNodes.value = true
  try {
    const result = await getNodes(nodeLabel.value || null, nodeLimit.value)
    if (Array.isArray(result) && result.length > 0) {
      queryResult.value = result
      message.success(t('query.found_nodes', { count: result.length }))
    } else {
      message.warning(t('query.no_nodes_found'))
      queryResult.value = null
    }
  } catch (error) {
    message.error(t('common.error') + ': ' + error.message)
    queryResult.value = null
  } finally {
    fetchingNodes.value = false
  }
}

const fetchEdges = async () => {
  fetchingEdges.value = true
  try {
    const result = await getEdges(relType.value || null, edgeLimit.value)
    if (Array.isArray(result) && result.length > 0) {
      queryResult.value = result
      message.success(t('query.found_edges', { count: result.length }))
    } else {
      message.warning(t('query.no_edges_found'))
      queryResult.value = null
    }
  } catch (error) {
    message.error(t('common.error') + ': ' + error.message)
    queryResult.value = null
  } finally {
    fetchingEdges.value = false
  }
}
</script>

<style lang="scss" scoped>
.query {
  .query-result {
    margin-top: 16px;
  }
}
</style>
