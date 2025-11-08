<template>
  <div class="upload-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">{{ t('upload.title') }}</h1>
        <p class="page-subtitle">支持文件上传、文本输入、网页链接</p>
      </div>
    </div>

    <n-space vertical :size="24">
      <!-- Input Method Tabs -->
      <n-card class="upload-card" :bordered="false">
        <n-tabs v-model:value="activeTab" type="segment" animated>
          <!-- File Upload Tab -->
          <n-tab-pane name="file" tab="文件上传">
            <div class="tab-content">
              <div class="section-header">
                <n-icon size="20"><cloud-upload-outline /></n-icon>
                <h3>上传文档文件</h3>
              </div>
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
                    </div>
                    <div class="dragger-text">
                      <h3>{{ t('upload.choose_file') }}</h3>
                      <p>{{ t('upload.drag_hint') }}</p>
                      <div class="dragger-formats">
                        <n-tag :bordered="false" size="small" type="warning">PDF</n-tag>
                        <n-tag :bordered="false" size="small" type="success">Markdown</n-tag>
                        <n-tag :bordered="false" size="small" type="info">TXT</n-tag>
                        <n-tag :bordered="false" size="small" type="error">Word</n-tag>
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
            </div>
          </n-tab-pane>

          <!-- Text Input Tab -->
          <n-tab-pane name="text" tab="文本输入">
            <div class="tab-content">
              <div class="section-header">
                <n-icon size="20"><document-text-outline /></n-icon>
                <h3>直接输入文本内容</h3>
              </div>
              <n-form>
                <n-form-item label="文档标题（可选）">
                  <n-input
                    v-model:value="textTitle"
                    placeholder="为文档起个标题，留空则自动生成"
                    :maxlength="100"
                    show-count
                  />
                </n-form-item>
                <n-form-item label="文本内容">
                  <n-input
                    v-model:value="textContent"
                    type="textarea"
                    placeholder="粘贴或输入文本内容（至少10个字符）..."
                    :rows="12"
                    :maxlength="100000"
                    show-count
                  />
                </n-form-item>
                <n-button
                  type="primary"
                  :loading="uploading"
                  :disabled="!textContent || textContent.trim().length < 10"
                  @click="handleTextUpload"
                  block
                  size="large"
                  class="upload-button"
                >
                  <template #icon>
                    <n-icon><rocket-outline /></n-icon>
                  </template>
                  提交文本并处理
                </n-button>
              </n-form>
            </div>
          </n-tab-pane>

          <!-- URL Input Tab -->
          <n-tab-pane name="url" tab="网页链接">
            <div class="tab-content">
              <div class="section-header">
                <n-icon size="20"><globe-outline /></n-icon>
                <h3>从网页抓取内容</h3>
              </div>
              <n-form>
                <n-form-item label="网页链接">
                  <n-input
                    v-model:value="urlInput"
                    placeholder="输入网页 URL，例如：https://example.com/article"
                    :maxlength="2000"
                  >
                    <template #prefix>
                      <n-icon :component="LinkOutline" />
                    </template>
                  </n-input>
                </n-form-item>
                <n-form-item label="文档标题（可选）">
                  <n-input
                    v-model:value="urlTitle"
                    placeholder="为文档起个标题，留空则使用网页标题"
                    :maxlength="100"
                    show-count
                  />
                </n-form-item>
                <n-alert type="info" style="margin-bottom: 16px">
                  系统将自动抓取网页内容并提取文本，支持大部分公开网页
                </n-alert>
                <n-button
                  type="primary"
                  :loading="uploading"
                  :disabled="!urlInput || !isValidUrl(urlInput)"
                  @click="handleUrlUpload"
                  block
                  size="large"
                  class="upload-button"
                >
                  <template #icon>
                    <n-icon><rocket-outline /></n-icon>
                  </template>
                  抓取网页并处理
                </n-button>
              </n-form>
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-card>

      <!-- Success Card -->
      <transition name="slide-fade">
        <n-card v-if="uploadResult" class="success-card" :bordered="false">
          <div class="section-header">
            <n-icon size="20"><checkmark-circle-outline /></n-icon>
            <h3>{{ t('upload.upload_success') }}</h3>
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
          <div class="section-header">
            <n-icon size="20"><code-working-outline /></n-icon>
            <h3>{{ t('upload.ingestion_started') }}</h3>
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
  AddCircleOutline,
  GlobeOutline,
  LinkOutline
} from '@vicons/ionicons5'
import { uploadFile, uploadText, uploadUrl, startIngestion } from '@/api/services'

const router = useRouter()
const { t } = useI18n()
const message = useMessage()

// Tab state
const activeTab = ref('file')

// File upload state
const selectedFile = ref(null)

// Text input state
const textContent = ref('')
const textTitle = ref('')

// URL input state
const urlInput = ref('')
const urlTitle = ref('')

// Common state
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

// URL validation
const isValidUrl = (url) => {
  try {
    const urlObj = new URL(url)
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
  } catch {
    return false
  }
}

// Text upload handler
const handleTextUpload = async () => {
  if (!textContent.value || textContent.value.trim().length < 10) {
    message.error('文本内容至少需要10个字符')
    return
  }

  uploading.value = true
  try {
    const result = await uploadText(
      textContent.value,
      textTitle.value || undefined,
      true // auto_process
    )
    
    uploadResult.value = result
    
    // Check if auto-processed
    if (result.jobId) {
      ingestionResult.value = {
        jobId: result.jobId,
        documentId: result.documentId
      }
      message.success('文本已提交并开始处理')
    } else {
      message.success('文本已保存')
    }
    
    // Clear form
    textContent.value = ''
    textTitle.value = ''
  } catch (error) {
    console.error('Text upload failed:', error)
    message.error(error.message || '文本提交失败')
  } finally {
    uploading.value = false
  }
}

// URL upload handler
const handleUrlUpload = async () => {
  if (!urlInput.value || !isValidUrl(urlInput.value)) {
    message.error('请输入有效的网页链接')
    return
  }

  uploading.value = true
  try {
    const result = await uploadUrl(
      urlInput.value,
      urlTitle.value || undefined,
      true // auto_process
    )
    
    uploadResult.value = result
    
    // Check if auto-processed
    if (result.jobId) {
      ingestionResult.value = {
        jobId: result.jobId,
        documentId: result.documentId
      }
      message.success('网页内容已抓取并开始处理')
    } else {
      message.success('网页内容已保存')
    }
    
    // Clear form
    urlInput.value = ''
    urlTitle.value = ''
  } catch (error) {
    console.error('URL upload failed:', error)
    message.error(error.message || '网页抓取失败')
  } finally {
    uploading.value = false
  }
}

const resetUpload = () => {
  selectedFile.value = null
  textContent.value = ''
  textTitle.value = ''
  urlInput.value = ''
  urlTitle.value = ''
  uploadResult.value = null
  ingestionResult.value = null
  activeTab.value = 'file'
}
</script>

<style lang="scss" scoped>
.upload-page {
  padding: 32px 48px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
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
      radial-gradient(circle at 20% 20%, rgba(194, 164, 116, 0.08) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(155, 135, 245, 0.08) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(245, 158, 11, 0.06) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
  }

  > * {
    position: relative;
    z-index: 1;
  }

  // Page Header
  .page-header {
    margin-bottom: 32px;
    padding: 32px;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.85) 100%);
    border-radius: 20px;
    backdrop-filter: blur(20px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 8px rgba(0, 0, 0, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
    border: 1px solid rgba(194, 164, 116, 0.2);
    position: relative;
    overflow: hidden;

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, 
        rgba(194, 164, 116, 0.5), 
        rgba(155, 135, 245, 0.5), 
        rgba(245, 158, 11, 0.5));
    }

    .page-title {
      font-size: 32px;
      font-weight: 700;
      background: linear-gradient(135deg, #c2a474 0%, #9b87f5 50%, #f59e0b 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin: 0 0 8px 0;
      letter-spacing: -0.5px;
    }

    .page-subtitle {
      font-size: 14px;
      color: #64748b;
      margin: 0;
      font-weight: 500;
    }
  }

  // Section Header (内卡片标题)
  .section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid rgba(194, 164, 116, 0.1);

    .n-icon {
      color: #c2a474;
    }

    h3 {
      font-size: 18px;
      font-weight: 600;
      color: #1e293b;
      margin: 0;
      letter-spacing: -0.3px;
    }
  }

  // Upload Card
  .upload-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.8) 100%);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(194, 164, 116, 0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.08),
        0 4px 16px rgba(0, 0, 0, 0.06);
      transform: translateY(-2px);
    }

    .tab-content {
      padding: 20px 0;
    }
  }

  // Enhanced Dragger
  .enhanced-dragger {
    :deep(.n-upload-dragger) {
      padding: 64px 48px;
      border: 2px dashed rgba(194, 164, 116, 0.3);
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.5) 0%, rgba(248, 250, 252, 0.5) 100%);
      backdrop-filter: blur(10px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;

      &::before {
        content: '';
        position: absolute;
        inset: 0;
        background: 
          radial-gradient(circle at 30% 40%, rgba(194, 164, 116, 0.05) 0%, transparent 60%),
          radial-gradient(circle at 70% 60%, rgba(155, 135, 245, 0.05) 0%, transparent 60%);
        pointer-events: none;
      }

      &:hover {
        border-color: rgba(194, 164, 116, 0.5);
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(248, 250, 252, 0.8) 100%);
        transform: translateY(-4px);
        box-shadow: 
          0 12px 32px rgba(194, 164, 116, 0.15),
          0 4px 12px rgba(0, 0, 0, 0.06);
      }
    }

    .dragger-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
    }

    .dragger-icon-wrapper {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;

      .dragger-icon {
        color: #c2a474;
        position: relative;
        z-index: 2;
        animation: float 3s ease-in-out infinite;
      }
    }

    .dragger-text {
      text-align: center;
      position: relative;
      z-index: 1;

      h3 {
        font-size: 20px;
        font-weight: 600;
        color: #1e293b;
        margin: 0 0 8px 0;
        letter-spacing: -0.3px;
      }

      p {
        font-size: 14px;
        color: #64748b;
        margin: 0 0 16px 0;
        font-weight: 500;
      }

      .dragger-formats {
        display: flex;
        gap: 8px;
        justify-content: center;
        
        :deep(.n-tag) {
          font-weight: 600;
          letter-spacing: 0.3px;
          padding: 4px 12px;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        }
      }
    }
  }

  // File Selected Card
  .file-selected-card {
    margin-top: 24px;
    padding: 24px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(194, 164, 116, 0.08) 0%, rgba(155, 135, 245, 0.08) 100%);
    border: 1px solid rgba(194, 164, 116, 0.2);
    backdrop-filter: blur(10px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

    .file-preview {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 20px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.9) 100%);
      backdrop-filter: blur(10px);
      border-radius: 12px;
      margin-bottom: 16px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      border: 1px solid rgba(194, 164, 116, 0.15);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        transform: translateY(-2px);
      }

      .file-icon-wrapper {
        width: 56px;
        height: 56px;
        background: linear-gradient(135deg, #c2a474 0%, #9b87f5 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(194, 164, 116, 0.3);
      }

      .file-details {
        flex: 1;

        .file-name {
          font-size: 16px;
          font-weight: 600;
          color: #1e293b;
          margin-bottom: 6px;
          word-break: break-all;
          letter-spacing: -0.2px;
        }

        .file-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: #64748b;

          .file-size {
            font-weight: 500;
          }

          .file-type {
            font-weight: 600;
            color: #c2a474;
            letter-spacing: 0.3px;
          }
        }
      }
    }

    .upload-button {
      margin-top: 12px;
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      background: linear-gradient(135deg, #c2a474 0%, #9b87f5 100%);
      border: none;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(194, 164, 116, 0.3);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(194, 164, 116, 0.4);
      }
    }
  }

  // Success Card
  .success-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.8) 100%);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(16, 185, 129, 0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.08),
        0 4px 16px rgba(0, 0, 0, 0.06);
    }

    .result-descriptions {
      margin-bottom: 20px;
      
      :deep(.n-descriptions) {
        border-radius: 12px;
        overflow: hidden;
      }
    }

    .action-button {
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
      }
    }
  }

  // Ingestion Card
  .ingestion-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.8) 100%);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    box-shadow: 
      0 8px 32px rgba(0, 0, 0, 0.06),
      0 2px 12px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(59, 130, 246, 0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

    &:hover {
      box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.08),
        0 4px 16px rgba(0, 0, 0, 0.06);
    }

    .result-descriptions {
      margin-bottom: 20px;
      
      :deep(.n-descriptions) {
        border-radius: 12px;
        overflow: hidden;
      }
    }

    .action-button {
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      border-radius: 12px;

      &:first-of-type {
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
        }
      }
    }
  }
}

// 全局样式增强
:deep(.n-card) {
  border-radius: 20px;
}

:deep(.n-button) {
  border-radius: 12px;
  font-weight: 600;
  letter-spacing: 0.3px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:not(:disabled):hover {
    transform: translateY(-2px);
  }
}

// 动画
@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

// 过渡动画
.slide-fade-enter-active {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 1, 1);
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(24px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-24px);
}
</style>

