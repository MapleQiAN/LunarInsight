<template>
  <div class="status">
    <n-page-header :title="t('status.title')" />

    <n-card>
      <n-space :size="16" style="margin-bottom: 20px">
        <n-input
          v-model:value="jobId"
          :placeholder="t('status.job_id_help')"
          style="width: 300px"
        >
          <template #prefix>
            {{ t('status.job_id') }}:
          </template>
        </n-input>
        
        <n-button type="primary" :loading="checking" @click="checkStatus">
          <template #icon>
            <n-icon><search-outline /></n-icon>
          </template>
          {{ t('status.check_status') }}
        </n-button>
      </n-space>

      <n-divider v-if="statusData" />

      <div v-if="statusData" class="status-result">
        <n-space vertical :size="16">
          <n-card :title="t('status.status')" size="small">
            <n-space :size="16">
              <div class="status-item">
                <n-text strong>{{ t('status.status') }}:</n-text>
                <n-tag :type="getStatusType(statusData.status)" round>
                  {{ getStatusText(statusData.status) }}
                </n-tag>
              </div>
              
              <div class="status-item">
                <n-text strong>{{ t('status.progress') }}:</n-text>
                <n-text>{{ statusData.progress || 'N/A' }}</n-text>
              </div>
            </n-space>
          </n-card>

          <n-card v-if="statusData.statistics" :title="t('status.statistics')" size="small">
            <n-code :code="JSON.stringify(statusData.statistics, null, 2)" language="json" />
          </n-card>

          <n-card v-if="statusData.result" :title="t('status.view_full_result')" size="small">
            <n-code :code="JSON.stringify(statusData.result, null, 2)" language="json" />
          </n-card>
        </n-space>
      </div>

      <n-empty
        v-else-if="!checking && !jobId"
        :description="t('status.enter_job_id')"
        size="large"
      >
        <template #icon>
          <n-icon size="48">
            <document-text-outline />
          </n-icon>
        </template>
      </n-empty>
    </n-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { SearchOutline, DocumentTextOutline } from '@vicons/ionicons5'
import { getJobStatus } from '@/api/services'

const { t } = useI18n()
const route = useRoute()
const message = useMessage()

const jobId = ref(route.query.jobId || '')
const checking = ref(false)
const statusData = ref(null)

const getStatusType = (status) => {
  const statusMap = {
    completed: 'success',
    processing: 'warning',
    pending: 'info',
    failed: 'error'
  }
  return statusMap[status] || 'default'
}

const getStatusText = (status) => {
  return t(`status.${status}`) || status
}

const checkStatus = async () => {
  if (!jobId.value.trim()) {
    message.warning(t('status.job_id_help'))
    return
  }

  checking.value = true
  try {
    const result = await getJobStatus(jobId.value)
    statusData.value = result
    message.success(t('common.success'))
  } catch (error) {
    message.error(t('status.fetch_error'))
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
  .status-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}
</style>
