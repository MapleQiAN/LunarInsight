<template>
  <div class="upload">
    <n-page-header :title="t('upload.title')" />

    <n-space vertical :size="16">
      <n-card>
        <n-upload
          :max="1"
          :default-upload="false"
          @change="handleFileChange"
          :show-file-list="false"
        >
          <n-upload-dragger>
            <div style="padding: 40px 0">
              <n-icon size="48" :depth="3">
                <cloud-upload-outline />
              </n-icon>
              <n-text style="font-size: 16px; display: block; margin-top: 12px">
                {{ t('upload.choose_file') }}
              </n-text>
              <n-text depth="3" style="font-size: 12px; display: block; margin-top: 8px">
                {{ t('upload.supported_formats') }}
              </n-text>
            </div>
          </n-upload-dragger>
        </n-upload>

        <div v-if="selectedFile" style="margin-top: 24px">
          <n-card size="small" :title="t('upload.file')" hoverable>
            <n-space vertical :size="12">
              <div class="file-info-item">
                <n-text strong>{{ t('upload.file') }}:</n-text>
                <n-text>{{ selectedFile.name }}</n-text>
              </div>
              <div class="file-info-item">
                <n-text strong>{{ t('upload.size') }}:</n-text>
                <n-text>{{ formatFileSize(selectedFile.size) }}</n-text>
              </div>
            </n-space>
          </n-card>

          <n-button
            type="primary"
            :loading="uploading"
            @click="handleUpload"
            block
            size="large"
            style="margin-top: 16px"
          >
            <template #icon>
              <n-icon><cloud-upload-outline /></n-icon>
            </template>
            {{ t('upload.upload_process') }}
          </n-button>
        </div>
      </n-card>

      <n-card v-if="uploadResult" :title="t('upload.upload_success')">
        <n-alert type="success" :show-icon="true">
          {{ t('upload.upload_success') }}
        </n-alert>
        
        <n-descriptions bordered :column="1" style="margin-top: 16px">
          <n-descriptions-item :label="t('upload.document_id')">
            <n-text code>{{ uploadResult.documentId }}</n-text>
          </n-descriptions-item>
        </n-descriptions>

        <n-button
          type="primary"
          :loading="ingesting"
          @click="handleIngestion"
          block
          size="large"
          style="margin-top: 16px"
        >
          <template #icon>
            <n-icon><play-outline /></n-icon>
          </template>
          {{ t('upload.start_ingestion') }}
        </n-button>
      </n-card>

      <n-card v-if="ingestionResult" :title="t('upload.ingestion_started')">
        <n-alert type="success" :show-icon="true">
          {{ t('upload.ingestion_started') }}
        </n-alert>
        
        <n-descriptions bordered :column="1" style="margin-top: 16px">
          <n-descriptions-item :label="t('upload.job_id')">
            <n-text code>{{ ingestionResult.jobId }}</n-text>
          </n-descriptions-item>
        </n-descriptions>

        <n-alert type="info" style="margin-top: 16px">
          {{ t('upload.check_status') }}
        </n-alert>

        <n-button
          type="primary"
          @click="$router.push(`/status?jobId=${ingestionResult.jobId}`)"
          block
          size="large"
          style="margin-top: 16px"
        >
          <template #icon>
            <n-icon><time-outline /></n-icon>
          </template>
          {{ t('status.check_status') }}
        </n-button>
      </n-card>
    </n-space>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { CloudUploadOutline, PlayOutline, TimeOutline } from '@vicons/ionicons5'
import { uploadFile, startIngestion } from '@/api/services'

const router = useRouter()
const { t } = useI18n()
const message = useMessage()

const selectedFile = ref(null)
const uploading = ref(false)
const ingesting = ref(false)
const uploadResult = ref(null)
const ingestionResult = ref(null)

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const handleFileChange = ({ file, fileList }) => {
  if (file) {
    selectedFile.value = file.file
    uploadResult.value = null
    ingestionResult.value = null
  }
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    message.warning(t('upload.choose_file'))
    return
  }

  uploading.value = true
  try {
    const result = await uploadFile(selectedFile.value)
    uploadResult.value = result
    message.success(t('upload.upload_success'))
  } catch (error) {
    message.error(t('upload.error') + ': ' + error.message)
  } finally {
    uploading.value = false
  }
}

const handleIngestion = async () => {
  if (!uploadResult.value?.documentId) {
    message.warning(t('upload.document_id'))
    return
  }

  ingesting.value = true
  try {
    const result = await startIngestion(uploadResult.value.documentId)
    ingestionResult.value = result
    message.success(t('upload.ingestion_started'))
  } catch (error) {
    message.error(t('upload.error') + ': ' + error.message)
  } finally {
    ingesting.value = false
  }
}
</script>

<style lang="scss" scoped>
.upload {
  .file-info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>

