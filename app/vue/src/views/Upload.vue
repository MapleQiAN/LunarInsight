<template>
  <div class="upload">
    <el-card shadow="never" class="page-header">
      <h2>{{ t('upload.title') }}</h2>
    </el-card>

    <el-card shadow="never">
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          {{ t('upload.choose_file') }}<em>{{ t('upload.supported_formats') }}</em>
        </div>
      </el-upload>

      <div v-if="selectedFile" class="file-info" style="margin-top: 20px">
        <el-descriptions :column="1" border>
          <el-descriptions-item :label="t('upload.file')">
            {{ selectedFile.name }}
          </el-descriptions-item>
          <el-descriptions-item :label="t('upload.size')">
            {{ formatFileSize(selectedFile.size) }} {{ t('upload.bytes') }}
          </el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 20px">
          <el-button
            type="primary"
            :loading="uploading"
            @click="handleUpload"
            style="width: 100%"
          >
            {{ t('upload.upload_process') }}
          </el-button>
        </div>
      </div>

      <el-divider v-if="uploadResult" />

      <div v-if="uploadResult" class="upload-result">
        <el-alert
          :title="t('upload.upload_success')"
          type="success"
          :closable="false"
          show-icon
        />
        <el-descriptions :column="1" border style="margin-top: 20px">
          <el-descriptions-item :label="t('upload.document_id')">
            {{ uploadResult.documentId }}
          </el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 20px">
          <el-button
            type="primary"
            :loading="ingesting"
            @click="handleIngestion"
            style="width: 100%"
          >
            {{ t('upload.start_ingestion') }}
          </el-button>
        </div>
      </div>

      <div v-if="ingestionResult" class="ingestion-result" style="margin-top: 20px">
        <el-alert
          :title="t('upload.ingestion_started')"
          type="success"
          :closable="false"
          show-icon
        />
        <el-descriptions :column="1" border style="margin-top: 20px">
          <el-descriptions-item :label="t('upload.job_id')">
            {{ ingestionResult.jobId }}
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          :title="t('upload.check_status')"
          type="info"
          :closable="false"
          style="margin-top: 20px"
        />
        <div style="margin-top: 20px">
          <el-button @click="$router.push(`/status?jobId=${ingestionResult.jobId}`)">
            {{ t('status.check_status') }}
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadFile, startIngestion } from '@/api/services'

const { t } = useI18n()
const uploadRef = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const ingesting = ref(false)
const uploadResult = ref(null)
const ingestionResult = ref(null)

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  uploadResult.value = null
  ingestionResult.value = null
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning(t('upload.choose_file'))
    return
  }

  uploading.value = true
  try {
    const result = await uploadFile(selectedFile.value)
    uploadResult.value = result
    ElMessage.success(t('upload.upload_success'))
  } catch (error) {
    ElMessage.error(t('upload.error'))
  } finally {
    uploading.value = false
  }
}

const handleIngestion = async () => {
  if (!uploadResult.value?.documentId) {
    ElMessage.warning(t('upload.document_id'))
    return
  }

  ingesting.value = true
  try {
    const result = await startIngestion(uploadResult.value.documentId)
    ingestionResult.value = result
    ElMessage.success(t('upload.ingestion_started'))
  } catch (error) {
    ElMessage.error(t('upload.error'))
  } finally {
    ingesting.value = false
  }
}
</script>

<style lang="scss" scoped>
.upload {
  .page-header {
    margin-bottom: 20px;
    h2 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
    }
  }
}
</style>

