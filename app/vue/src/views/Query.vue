<template>
  <div class="query">
    <el-card shadow="never" class="page-header">
      <h2>{{ t('query.title') }}</h2>
    </el-card>

    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="t('query.cypher_query')" name="cypher">
          <el-form>
            <el-form-item :label="t('query.enter_cypher')">
              <el-input
                v-model="cypherQuery"
                type="textarea"
                :rows="6"
                :placeholder="t('query.cypher_help')"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="executing" @click="executeCypher">
                {{ t('query.execute') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('query.get_nodes')" name="nodes">
          <el-form :inline="true">
            <el-form-item :label="t('query.label_optional')">
              <el-input
                v-model="nodeLabel"
                :placeholder="t('query.label_help')"
                clearable
              />
            </el-form-item>
            <el-form-item :label="t('query.limit')">
              <el-input-number v-model="nodeLimit" :min="1" :max="1000" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="fetchingNodes" @click="fetchNodes">
                {{ t('query.get_nodes_btn') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('query.get_edges')" name="edges">
          <el-form :inline="true">
            <el-form-item :label="t('query.rel_type_optional')">
              <el-input
                v-model="relType"
                :placeholder="t('query.rel_type_help')"
                clearable
              />
            </el-form-item>
            <el-form-item :label="t('query.limit')">
              <el-input-number v-model="edgeLimit" :min="1" :max="1000" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="fetchingEdges" @click="fetchEdges">
                {{ t('query.get_edges_btn') }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <el-divider v-if="queryResult" />

      <div v-if="queryResult" class="query-result">
        <el-alert
          :title="t('query.success')"
          type="success"
          :closable="false"
          show-icon
          style="margin-bottom: 20px"
        />

        <el-tabs v-model="resultView">
          <el-tab-pane :label="t('query.view_result')" name="table">
            <el-table :data="queryResult" border style="width: 100%">
              <el-table-column
                v-for="(value, key) in queryResult[0]"
                :key="key"
                :prop="key"
                :label="key"
                show-overflow-tooltip
              />
            </el-table>
          </el-tab-pane>
          <el-tab-pane :label="t('query.view_raw_json')" name="json">
            <pre class="json-view">{{ JSON.stringify(queryResult, null, 2) }}</pre>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { executeCypherQuery, getNodes, getEdges } from '@/api/services'

const { t } = useI18n()
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

const executeCypher = async () => {
  if (!cypherQuery.value.trim()) {
    ElMessage.warning(t('query.enter_cypher'))
    return
  }

  executing.value = true
  try {
    const result = await executeCypherQuery(cypherQuery.value)
    if (Array.isArray(result) && result.length > 0) {
      queryResult.value = result
      ElMessage.success(t('query.success'))
    } else {
      ElMessage.warning(t('query.no_results'))
      queryResult.value = null
    }
  } catch (error) {
    ElMessage.error(t('common.error'))
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
      ElMessage.success(t('query.found_nodes', { count: result.length }))
    } else {
      ElMessage.warning(t('query.no_nodes_found'))
      queryResult.value = null
    }
  } catch (error) {
    ElMessage.error(t('common.error'))
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
      ElMessage.success(t('query.found_edges', { count: result.length }))
    } else {
      ElMessage.warning(t('query.no_edges_found'))
      queryResult.value = null
    }
  } catch (error) {
    ElMessage.error(t('common.error'))
    queryResult.value = null
  } finally {
    fetchingEdges.value = false
  }
}
</script>

<style lang="scss" scoped>
.query {
  .page-header {
    margin-bottom: 20px;
    h2 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
    }
  }

  .json-view {
    background: #f5f7fa;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
  }
}
</style>

