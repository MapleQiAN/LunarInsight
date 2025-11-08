<template>
  <div class="upload-page">
    <!-- Enhanced Header -->
    <div class="upload-header">
      <div>
        <h1 class="upload-title">
          <n-gradient-text type="warning">
            {{ t('upload.title') }}
          </n-gradient-text>
        </h1>
        <p class="upload-subtitle">{{ t('upload.supported_formats') }}</p>
      </div>
    </div>

    <n-space vertical :size="24">
      <!-- Upload Card -->
      <n-card class="upload-card" :bordered="false">
        <n-upload
          :max="1"
          :default-upload="false"
          @change="handleFileChange"
          :show-file-list="false"
          accept=".pdf,.md,.markdown,.txt,.doc,.docx"
        >
          <n-upload-dragger class="enhanced-dragger">
            <div class="dragger-content">
              <div class="dragger-icon-wrapper">
                <n-icon size="64" :component="CloudUploadOutline" class="dragger-icon" />
                <div class="icon-ring"></div>
                <div class="icon-ring ring-2"></div>
              </div>
              <div class="dragger-text">
                <h3>{{ t('upload.choose_file') }}</h3>
                <p>{{ t('upload.drag_hint') }}</p>
                <div class="dragger-formats">
                  <n-tag round size="small" type="info">PDF</n-tag>
                  <n-tag round size="small" type="success">Markdown</n-tag>
                  <n-tag round size="small" type="warning">TXT</n-tag>
                  <n-tag round size="small" type="primary">Word</n-tag>
                </div>
              </div>
            </div>
          </n-upload-dragger>
        </n-upload>

        <!-- File Info Card -->
        <div v-if="selectedFile" class="file-selected-card">
          <div class="file-preview">
            <div class="file-icon-wrapper">
              <n-icon size="40" :component="DocumentTextOutline" />
            </div>
            <div class="file-details">
              <div class="file-name">{{ selectedFile.name }}</div>
              <div class="file-meta">
                <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
                <n-divider vertical />
                <span class="file-type">{{ getFileType(selectedFile.name) }}</span>
              </div>
            </div>
            <n-button circle quaternary @click="removeFile">
              <template #icon>
                <n-icon :component="CloseOutline" />
              </template>
            </n-button>
          </div>

          <n-button
            type="primary"
            :loading="uploading"
            @click="handleUpload"
            block
            size="large"
            class="upload-button"
          >
            <template #icon>
              <n-icon><rocket-outline /></n-icon>
            </template>
            {{ t('upload.upload_process') }}
          </n-button>
        </div>
      </n-card>

      <!-- Success Card -->
      <transition name="slide-fade">
        <n-card v-if="uploadResult" class="success-card" :bordered="false">
          <div class="success-header">
            <div class="success-icon">
              <n-icon size="48" :component="CheckmarkCircleOutline" />
            </div>
            <div class="success-content">
              <h2>{{ t('upload.upload_success') }}</h2>
              <p>{{ t('upload.upload_success_desc') }}</p>
            </div>
          </div>

          <n-descriptions bordered :column="1" class="result-descriptions">
            <n-descriptions-item label="文档 ID">
              <n-text code strong>{{ uploadResult.documentId }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item label="上传时间">
              <n-text>{{ new Date().toLocaleString('zh-CN') }}</n-text>
            </n-descriptions-item>
          </n-descriptions>

          <n-button
            type="primary"
            :loading="ingesting"
            @click="handleIngestion"
            block
            size="large"
            class="action-button"
          >
            <template #icon>
              <n-icon><play-circle-outline /></n-icon>
            </template>
            {{ t('upload.start_ingestion') }}
          </n-button>
        </n-card>
      </transition>

      <!-- Ingestion Started Card -->
      <transition name="slide-fade">
        <n-card v-if="ingestionResult" class="ingestion-card" :bordered="false">
          <div class="ingestion-header">
            <div class="ingestion-icon">
              <n-icon size="48" :component="CodeWorkingOutline" />
            </div>
            <div class="ingestion-content">
              <h2>{{ t('upload.ingestion_started') }}</h2>
              <p>{{ t('upload.ingestion_started_desc') }}</p>
            </div>
          </div>

          <n-descriptions bordered :column="1" class="result-descriptions">
            <n-descriptions-item label="任务 ID">
              <n-text code strong>{{ ingestionResult.jobId }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item label="状态">
              <n-tag type="info" round>处理中</n-tag>
            </n-descriptions-item>
          </n-descriptions>

          <n-space vertical :size="12" style="margin-top: 20px">
            <n-button
              type="primary"
              @click="$router.push(`/status?jobId=${ingestionResult.jobId}`)"
              block
              size="large"
              class="action-button"
            >
              <template #icon>
                <n-icon><time-outline /></n-icon>
              </template>
              {{ t('status.check_status') }}
            </n-button>
            
            <n-button
              @click="resetUpload"
              block
              size="large"
            >
              <template #icon>
                <n-icon><add-circle-outline /></n-icon>
              </template>
              {{ t('upload.upload_new') }}
            </n-button>
          </n-space>
        </n-card>
      </transition>
    </n-space>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import {
  CloudUploadOutline,
  DocumentTextOutline,
  CloseOutline,
  RocketOutline,
  PlayCircleOutline,
  TimeOutline,
  CheckmarkCircleOutline,
  CodeWorkingOutline,
  AddCircleOutline
} from '@vicons/ionicons5'
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

const getFileType = (filename) => {
  const ext = filename.split('.').pop().toUpperCase()
  return ext
}

// 允许的文件类型
const ALLOWED_EXTENSIONS = ['.pdf', '.md', '.markdown', '.txt', '.doc', '.docx']
const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'text/markdown',
  'text/plain',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]

// 验证文件类型
const validateFileType = (file) => {
  const fileName = file.name.toLowerCase()
  const fileExt = '.' + fileName.split('.').pop()
  
  // 检查扩展名
  if (!ALLOWED_EXTENSIONS.includes(fileExt)) {
    return false
  }
  
  // 检查 MIME 类型（如果可用）
  if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
    // 对于某些情况，浏览器可能不识别 .md 文件的 MIME 类型
    if (!(fileExt === '.md' || fileExt === '.markdown')) {
      return false
    }
  }
  
  return true
}

const handleFileChange = ({ file, fileList }) => {
  if (file) {
    // 验证文件类型
    if (!validateFileType(file.file)) {
      message.error(t('upload.invalid_file_type'))
      return
    }
    
    selectedFile.value = file.file
    uploadResult.value = null
    ingestionResult.value = null
    message.success(t('upload.file_selected', { name: file.file.name }))
  }
}

const removeFile = () => {
  selectedFile.value = null
  uploadResult.value = null
  ingestionResult.value = null
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

const resetUpload = () => {
  selectedFile.value = null
  uploadResult.value = null
  ingestionResult.value = null
}
</script>

<style lang="scss" scoped>
.upload-page {
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

  // Header - 轻奢现代化设计
  .upload-header {
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

    .upload-title {
      font-size: 36px;
      font-weight: 700;
      margin: 0 0 10px 0;
      letter-spacing: -0.5px;
    }

    .upload-subtitle {
      font-size: 15px;
      color: #64748b;
      margin: 0;
      font-weight: 500;
    }
  }

  // Upload Card - 企业级卡片
  .upload-card {
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
  }

  // Enhanced Dragger - 轻奢上传区
  .enhanced-dragger {
    :deep(.n-upload-dragger) {
      padding: 72px 48px;
      border: 3px dashed rgba(194, 164, 116, 0.3);
      border-radius: 24px;
      background: linear-gradient(135deg, 
        rgba(255, 250, 240, 0.8) 0%, 
        rgba(254, 243, 199, 0.8) 50%, 
        rgba(253, 230, 138, 0.6) 100%);
      backdrop-filter: blur(10px);
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;

      &::before {
        content: '';
        position: absolute;
        inset: 0;
        background: 
          radial-gradient(circle at 30% 40%, rgba(245, 158, 11, 0.05) 0%, transparent 60%),
          radial-gradient(circle at 70% 60%, rgba(194, 164, 116, 0.05) 0%, transparent 60%);
        pointer-events: none;
      }

      &:hover {
        border-color: rgba(194, 164, 116, 0.6);
        background: linear-gradient(135deg, 
          rgba(253, 230, 138, 0.9) 0%, 
          rgba(252, 211, 77, 0.9) 50%, 
          rgba(251, 191, 36, 0.8) 100%);
        transform: translateY(-6px);
        box-shadow: 
          0 16px 40px rgba(245, 158, 11, 0.25),
          0 8px 16px rgba(0, 0, 0, 0.08);
      }
    }

    .dragger-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 24px;
    }

    .dragger-icon-wrapper {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;

      .dragger-icon {
        color: #f59e0b;
        position: relative;
        z-index: 2;
        animation: float 3s ease-in-out infinite;
      }

      .icon-ring {
        position: absolute;
        width: 100px;
        height: 100px;
        border: 3px solid rgba(245, 158, 11, 0.2);
        border-radius: 50%;
        animation: pulse 2s ease-in-out infinite;

        &.ring-2 {
          width: 120px;
          height: 120px;
          animation-delay: 0.5s;
        }
      }
    }

    .dragger-text {
      text-align: center;
      position: relative;
      z-index: 1;

      h3 {
        font-size: 22px;
        font-weight: 700;
        color: #0f172a;
        margin: 0 0 10px 0;
        letter-spacing: -0.3px;
      }

      p {
        font-size: 15px;
        color: #64748b;
        margin: 0 0 20px 0;
        font-weight: 500;
      }

      .dragger-formats {
        display: flex;
        gap: 10px;
        justify-content: center;
        
        :deep(.n-tag) {
          font-weight: 600;
          letter-spacing: 0.3px;
          padding: 6px 14px;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        }
      }
    }
  }

  // File Selected Card - 轻奢文件卡片
  .file-selected-card {
    margin-top: 28px;
    padding: 28px;
    border-radius: 20px;
    background: linear-gradient(135deg, 
      rgba(59, 130, 246, 0.08) 0%, 
      rgba(37, 99, 235, 0.08) 100%);
    border: 2px solid rgba(59, 130, 246, 0.2);
    backdrop-filter: blur(10px);
    box-shadow: 
      0 4px 16px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.6);

    .file-preview {
      display: flex;
      align-items: center;
      gap: 20px;
      padding: 24px;
      background: linear-gradient(135deg, 
        rgba(255, 255, 255, 0.98) 0%, 
        rgba(248, 250, 252, 0.98) 100%);
      backdrop-filter: blur(10px);
      border-radius: 18px;
      margin-bottom: 20px;
      box-shadow: 
        0 4px 16px rgba(0, 0, 0, 0.06),
        inset 0 1px 0 rgba(255, 255, 255, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.6);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &:hover {
        box-shadow: 
          0 8px 20px rgba(0, 0, 0, 0.1),
          inset 0 1px 0 rgba(255, 255, 255, 0.8);
        transform: translateY(-2px);
      }

      .file-icon-wrapper {
        width: 64px;
        height: 64px;
        background: linear-gradient(135deg, 
          #3b82f6 0%, 
          #2563eb 50%, 
          #1d4ed8 100%);
        border-radius: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
        box-shadow: 
          0 6px 16px rgba(59, 130, 246, 0.3),
          0 2px 8px rgba(0, 0, 0, 0.08);
      }

      .file-details {
        flex: 1;

        .file-name {
          font-size: 17px;
          font-weight: 700;
          color: #0f172a;
          margin-bottom: 8px;
          word-break: break-all;
          letter-spacing: -0.2px;
        }

        .file-meta {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 14px;
          color: #64748b;

          .file-size {
            font-weight: 600;
          }

          .file-type {
            font-weight: 700;
            color: #3b82f6;
            letter-spacing: 0.5px;
          }
        }
      }
    }

    .upload-button {
      margin-top: 12px;
      height: 52px;
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0.3px;
      background: linear-gradient(135deg, 
        #3b82f6 0%, 
        #2563eb 50%, 
        #1d4ed8 100%);
      border: none;
      border-radius: 18px;
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);

      &:hover {
        background: linear-gradient(135deg, 
          #2563eb 0%, 
          #1d4ed8 50%, 
          #1e40af 100%);
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.4);
      }
    }
  }

  // Success Card - 轻奢成功卡片
  .success-card {
    border-radius: 24px;
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 2px solid rgba(16, 185, 129, 0.2);
    backdrop-filter: blur(10px);

    .success-header {
      display: flex;
      align-items: center;
      gap: 24px;
      margin-bottom: 28px;
      padding: 28px;
      background: linear-gradient(135deg, 
        rgba(240, 253, 244, 0.8) 0%, 
        rgba(209, 250, 229, 0.6) 100%);
      backdrop-filter: blur(10px);
      border-radius: 20px;
      border: 1px solid rgba(16, 185, 129, 0.15);

      .success-icon {
        width: 72px;
        height: 72px;
        background: linear-gradient(135deg, 
          #10b981 0%, 
          #059669 50%, 
          #047857 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        box-shadow: 
          0 8px 20px rgba(16, 185, 129, 0.4),
          0 2px 8px rgba(0, 0, 0, 0.1);
        flex-shrink: 0;
        animation: bounceIn 0.6s ease-out;
      }

      .success-content {
        h2 {
          font-size: 22px;
          font-weight: 800;
          color: #0f172a;
          margin: 0 0 10px 0;
          letter-spacing: -0.3px;
        }

        p {
          font-size: 15px;
          color: #64748b;
          margin: 0;
          font-weight: 500;
        }
      }
    }

    .result-descriptions {
      margin-bottom: 20px;
      
      :deep(.n-descriptions) {
        border-radius: 16px;
        overflow: hidden;
      }
    }

    .action-button {
      height: 52px;
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0.3px;
      border-radius: 18px;
      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);

      &:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
      }
    }
  }

  // Ingestion Card - 轻奢处理卡片
  .ingestion-card {
    border-radius: 24px;
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 2px solid rgba(59, 130, 246, 0.2);
    backdrop-filter: blur(10px);

    .ingestion-header {
      display: flex;
      align-items: center;
      gap: 24px;
      margin-bottom: 28px;
      padding: 28px;
      background: linear-gradient(135deg, 
        rgba(236, 254, 255, 0.8) 0%, 
        rgba(219, 234, 254, 0.6) 100%);
      backdrop-filter: blur(10px);
      border-radius: 20px;
      border: 1px solid rgba(59, 130, 246, 0.15);

      .ingestion-icon {
        width: 72px;
        height: 72px;
        background: linear-gradient(135deg, 
          #3b82f6 0%, 
          #2563eb 50%, 
          #1d4ed8 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        box-shadow: 
          0 8px 20px rgba(59, 130, 246, 0.4),
          0 2px 8px rgba(0, 0, 0, 0.1);
        flex-shrink: 0;
        animation: pulse-icon 2s ease-in-out infinite;
      }

      .ingestion-content {
        h2 {
          font-size: 22px;
          font-weight: 800;
          color: #0f172a;
          margin: 0 0 10px 0;
          letter-spacing: -0.3px;
        }

        p {
          font-size: 15px;
          color: #64748b;
          margin: 0;
          font-weight: 500;
        }
      }
    }

    .result-descriptions {
      :deep(.n-descriptions) {
        border-radius: 16px;
        overflow: hidden;
      }
    }

    .action-button {
      height: 52px;
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0.3px;
      border-radius: 18px;

      &:first-of-type {
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);

        &:hover {
          transform: translateY(-3px);
          box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
        }
      }
    }
  }
}

// 全局样式增强
:deep(.n-card) {
  border-radius: 24px;
}

:deep(.n-button) {
  border-radius: 16px;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:not(:disabled):hover {
    transform: translateY(-2px);
  }
}

// Animations
@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.1;
  }
}

@keyframes bounceIn {
  0% {
    opacity: 0;
    transform: scale(0.3);
  }
  50% {
    opacity: 1;
    transform: scale(1.05);
  }
  70% {
    transform: scale(0.9);
  }
  100% {
    transform: scale(1);
  }
}

@keyframes pulse-icon {
  0%, 100% {
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  }
  50% {
    box-shadow: 0 4px 24px rgba(59, 130, 246, 0.6);
  }
}

.slide-fade-enter-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 1, 1);
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(30px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-30px);
}
</style>

