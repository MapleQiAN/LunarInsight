<template>
  <div class="status">
    <el-card shadow="never" class="page-header">
      <h2>{{ t('status.title') }}</h2>
    </el-card>

    <el-card shadow="never">
      <el-form :inline="true">
        <el-form-item :label="t('status.job_id')">
          <el-input
            v-model="jobId"
            :placeholder="t('status.job_id_help')"
            style="width: 300px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="checking" @click="checkStatus">
            {{ t('status.check_status') }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider v-if="statusData" />

      <div v-if="statusData" class="status-result">
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="t('status.status')">
            <el-tag :type="getStatusType(statusData.status)">
              {{ getStatusText(statusData.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="t('status.progress')">
            {{ statusData.progress || 'N/A' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-card v-if="statusData.statistics" shadow="never" style="margin-top: 20px">
          <template #header>
            <span>{{ t('status.statistics') }}</span>
          </template>
          <pre class="json-view">{{ JSON.stringify(statusData.statistics, null, 2) }}</pre>
        </el-card>

        <el-card v-if="statusData.result" shadow="never" style="margin-top: 20px">
          <template #header>
            <span>{{ t('status.view_full_result') }}</span>
          </template>
          <pre class="json-view">{{ JSON.stringify(statusData.result, null, 2) }}</pre>
        </el-card>
      </div>

      <el-empty
        v-else-if="!checking && !jobId"
        :description="t('status.enter_job_id')"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getJobStatus } from '@/api/services'

const { t } = useI18n()
const route = useRoute()
const jobId = ref(route.query.jobId || '')
const checking = ref(false)
const statusData = ref(null)

const getStatusType = (status) => {
  const statusMap = {
    completed: 'success',
    processing: 'warning',
    pending: 'info',
    failed: 'danger'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  return t(`status.${status}`) || status
}

const checkStatus = async () => {
  if (!jobId.value.trim()) {
    ElMessage.warning(t('status.job_id_help'))
    return
  }

  checking.value = true
  try {
    const result = await getJobStatus(jobId.value)
    statusData.value = result
  } catch (error) {
    ElMessage.error(t('status.fetch_error'))
    statusData.value = null
  } finally {
    checking.value = false
  }
}

onMounted(() => {
  if (jobId.value) {
    checkStatus()
  }
})
</script>

<style lang="scss" scoped>
.status {
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

