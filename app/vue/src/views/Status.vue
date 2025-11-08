<template>
  <div class="status-page">
    <div class="status-header">
      <h1 class="status-title">
        <n-gradient-text type="warning">
          {{ t('status.title') }}
        </n-gradient-text>
      </h1>
      <p class="status-subtitle">查看文档处理任务的实时状态</p>
    </div>

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
.status-page {
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
      radial-gradient(circle at 20% 20%, rgba(245, 158, 11, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(251, 191, 36, 0.05) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(217, 119, 6, 0.03) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  > * {
    position: relative;
    z-index: 1;
  }

  .status-header {
    margin-bottom: 32px;
    padding: 32px 36px;
    background: linear-gradient(135deg, 
      rgba(255, 250, 240, 0.95) 0%, 
      rgba(254, 243, 199, 0.95) 50%, 
      rgba(253, 230, 138, 0.95) 100%);
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
        rgba(245, 158, 11, 0.4), 
        transparent);
    }

    .status-title {
      font-size: 36px;
      font-weight: 700;
      margin: 0 0 10px 0;
      letter-spacing: -0.5px;
    }

    .status-subtitle {
      font-size: 15px;
      color: #64748b;
      margin: 0;
      font-weight: 500;
    }
  }

  :deep(.n-card) {
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

    .n-card__header {
      padding: 20px 24px;
      font-weight: 700;
      font-size: 17px;
      letter-spacing: -0.2px;
    }
  }

  :deep(.n-input) {
    .n-input__border,
    .n-input__state-border {
      border-radius: 16px;
    }
  }

  :deep(.n-button) {
    border-radius: 16px;
    font-weight: 700;
    letter-spacing: 0.3px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    height: 44px;
    padding: 0 28px;

    &:not(:disabled):hover {
      transform: translateY(-2px);
    }

    &.n-button--primary-type {
      box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);

      &:hover {
        box-shadow: 0 6px 16px rgba(245, 158, 11, 0.4);
      }
    }
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 20px;
    border-radius: 16px;
    background: linear-gradient(135deg, 
      rgba(248, 250, 252, 0.6) 0%, 
      rgba(241, 245, 249, 0.6) 100%);
    transition: all 0.3s;

    &:hover {
      background: linear-gradient(135deg, 
        rgba(248, 250, 252, 1) 0%, 
        rgba(241, 245, 249, 1) 100%);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    }

    :deep(.n-text) {
      font-weight: 600;
      font-size: 15px;
    }

    :deep(.n-tag) {
      font-weight: 700;
      letter-spacing: 0.3px;
      padding: 6px 14px;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    }
  }

  .status-result {
    animation: fadeInUp 0.6s ease-out;

    :deep(.n-code) {
      border-radius: 16px;
      background: linear-gradient(135deg, 
        rgba(15, 23, 42, 0.98) 0%, 
        rgba(30, 41, 59, 0.98) 100%);
      padding: 20px 24px;
      font-size: 13px;
      line-height: 1.6;
    }

    :deep(.n-card) {
      margin-bottom: 20px;
      
      &:last-child {
        margin-bottom: 0;
      }
    }
  }

  :deep(.n-empty) {
    padding: 48px 24px;
    
    .n-empty__icon {
      margin-bottom: 20px;
      
      .n-icon {
        color: #cbd5e1;
      }
    }

    .n-empty__description {
      font-size: 16px;
      font-weight: 500;
      color: #64748b;
    }
  }

  :deep(.n-space) {
    > * {
      .n-input {
        font-weight: 600;
      }
    }
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
