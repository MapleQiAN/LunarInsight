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

                <!-- 主题根节点配置 -->
                <n-form-item label="主题根节点（可选）" style="margin-top: 16px;">
                  <n-input
                    v-model:value="rootTopic"
                    placeholder="例如：机器学习、Web开发、算法等，留空则自动识别"
                    :maxlength="100"
                    show-count
                    clearable
                  >
                    <template #prefix>
                      <n-icon :component="SparklesOutline" />
                    </template>
                  </n-input>
                  <template #feedback>
                    <span style="font-size: 12px; color: #999;">指定文档的主要主题，有助于更好地组织知识图谱</span>
                  </template>
                </n-form-item>

                <!-- AI 配置选项 -->
                <div class="ai-config-section">
                  <n-collapse>
                    <n-collapse-item title="🤖 AI 智能分析（可选）" name="ai-config">
                      <n-space vertical :size="12">
                        <n-switch v-model:value="enableAI">
                          <template #checked>启用 AI 深度分析</template>
                          <template #unchecked>使用传统模式</template>
                        </n-switch>
                        
                        <n-alert v-if="enableAI" type="info" size="small">
                          AI 模式将提供更深入的概念理解和语义关系识别
                        </n-alert>

                        <n-form-item v-if="enableAI" label="自定义分析提示（可选）">
                          <n-input
                            v-model:value="userPrompt"
                            type="textarea"
                            placeholder="例如：重点关注技术架构和设计模式..."
                            :rows="3"
                            :maxlength="500"
                            show-count
                          />
                        </n-form-item>

                        <n-checkbox v-if="enableAI && userPrompt" v-model:checked="optimizePrompt">
                          让 AI 优化我的提示词
                        </n-checkbox>
                      </n-space>
                    </n-collapse-item>
                  </n-collapse>
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
                  {{ enableAI ? '🤖 AI 智能处理' : t('upload.upload_process') }}
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
                <n-form-item label="主题根节点（可选）">
                  <n-input
                    v-model:value="rootTopic"
                    placeholder="例如：机器学习、Web开发、算法等，留空则自动识别"
                    :maxlength="100"
                    show-count
                    clearable
                  >
                    <template #prefix>
                      <n-icon :component="SparklesOutline" />
                    </template>
                  </n-input>
                  <template #feedback>
                    <span style="font-size: 12px; color: #999;">指定文档的主要主题，有助于更好地组织知识图谱</span>
                  </template>
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
                
                <!-- AI 配置选项 -->
                <div class="ai-config-section">
                  <n-collapse>
                    <n-collapse-item title="🤖 AI 智能分析（可选）" name="ai-config">
                      <n-space vertical :size="12">
                        <n-switch v-model:value="enableAI">
                          <template #checked>启用 AI 深度分析</template>
                          <template #unchecked>使用传统模式</template>
                        </n-switch>
                        
                        <n-alert v-if="enableAI" type="info" size="small">
                          AI 模式将提供更深入的概念理解和语义关系识别
                        </n-alert>

                        <n-form-item v-if="enableAI" label="自定义分析提示（可选）">
                          <n-input
                            v-model:value="userPrompt"
                            type="textarea"
                            placeholder="例如：重点关注技术架构和设计模式..."
                            :rows="3"
                            :maxlength="500"
                            show-count
                          />
                        </n-form-item>

                        <n-checkbox v-if="enableAI && userPrompt" v-model:checked="optimizePrompt">
                          让 AI 优化我的提示词
                        </n-checkbox>
                      </n-space>
                    </n-collapse-item>
                  </n-collapse>
                </div>

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
                  {{ enableAI ? '🤖 AI 智能处理' : '提交文本并处理' }}
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
                <n-form-item label="主题根节点（可选）">
                  <n-input
                    v-model:value="rootTopic"
                    placeholder="例如：机器学习、Web开发、算法等，留空则自动识别"
                    :maxlength="100"
                    show-count
                    clearable
                  >
                    <template #prefix>
                      <n-icon :component="SparklesOutline" />
                    </template>
                  </n-input>
                  <template #feedback>
                    <span style="font-size: 12px; color: #999;">指定文档的主要主题，有助于更好地组织知识图谱</span>
                  </template>
                </n-form-item>
                <n-alert type="info" style="margin-bottom: 16px">
                  系统将自动抓取网页内容并提取文本，支持大部分公开网页
                </n-alert>
                
                <!-- AI 配置选项 -->
                <div class="ai-config-section">
                  <n-collapse>
                    <n-collapse-item title="🤖 AI 智能分析（可选）" name="ai-config">
                      <n-space vertical :size="12">
                        <n-switch v-model:value="enableAI">
                          <template #checked>启用 AI 深度分析</template>
                          <template #unchecked>使用传统模式</template>
                        </n-switch>
                        
                        <n-alert v-if="enableAI" type="info" size="small">
                          AI 模式将提供更深入的概念理解和语义关系识别
                        </n-alert>

                        <n-form-item v-if="enableAI" label="自定义分析提示（可选）">
                          <n-input
                            v-model:value="userPrompt"
                            type="textarea"
                            placeholder="例如：重点关注技术架构和设计模式..."
                            :rows="3"
                            :maxlength="500"
                            show-count
                          />
                        </n-form-item>

                        <n-checkbox v-if="enableAI && userPrompt" v-model:checked="optimizePrompt">
                          让 AI 优化我的提示词
                        </n-checkbox>
                      </n-space>
                    </n-collapse-item>
                  </n-collapse>
                </div>

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
                  {{ enableAI ? '🤖 AI 智能处理' : '抓取网页并处理' }}
                </n-button>
              </n-form>
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-card>

      <!-- Processing Progress Card (Optional local view) -->
      <transition name="slide-fade">
        <n-card v-if="currentTask" class="progress-card" :bordered="false">
          <div class="section-header">
            <n-icon size="20">
              <checkmark-circle-outline v-if="processCompleted" />
              <close-outline v-else-if="processFailed" />
              <rocket-outline v-else />
            </n-icon>
            <h3>
              <span v-if="processCompleted">处理完成</span>
              <span v-else-if="processFailed">处理失败</span>
              <span v-else>正在处理文档</span>
            </h3>
          </div>

          <!-- Document Info -->
          <n-descriptions v-if="uploadResult" bordered :column="1" class="result-descriptions" style="margin-bottom: 20px">
            <n-descriptions-item label="文档 ID">
              <n-text code strong>{{ uploadResult.documentId }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item label="文件名">
              <n-text>{{ uploadResult.filename }}</n-text>
            </n-descriptions-item>
            <n-descriptions-item v-if="currentJobId" label="任务 ID">
              <n-text code>{{ currentJobId }}</n-text>
            </n-descriptions-item>
          </n-descriptions>

          <!-- Progress Bar -->
          <div v-if="processing || processCompleted" class="progress-section">
            <div class="progress-info">
              <span class="progress-label">{{ progressMessage || '处理中...' }}</span>
              <span class="progress-percent">{{ progress }}%</span>
            </div>
            <n-progress
              type="line"
              :percentage="progress"
              :status="processFailed ? 'error' : processCompleted ? 'success' : 'default'"
              :show-indicator="false"
              :height="12"
              border-radius="6px"
            />
          </div>

          <!-- AI Mode Badge -->
          <n-alert v-if="currentTask?.aiMode" type="success" style="margin-bottom: 16px">
            <template #icon>
              <n-icon><sparkles-outline /></n-icon>
            </template>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>🤖 AI 智能分析模式</span>
              <n-tag v-if="currentTask?.aiStats?.model" type="info" size="small">
                {{ currentTask.aiStats.model }}
              </n-tag>
            </div>
          </n-alert>

          <!-- Stats (when completed) -->
          <div v-if="processCompleted && processStats" class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ processStats.chunks }}</div>
              <div class="stat-label">文本块</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ processStats.triplets }}</div>
              <div class="stat-label">知识三元组</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ processStats.concepts }}</div>
              <div class="stat-label">概念数量</div>
            </div>
          </div>

          <!-- AI Tokens Usage (when AI mode and completed) -->
          <div v-if="processCompleted && currentTask?.aiMode && currentTask?.aiStats" class="ai-stats-section">
            <n-divider style="margin: 20px 0">AI Tokens 用量</n-divider>
            <div class="ai-stats-grid">
              <div class="ai-stat-item">
                <div class="ai-stat-icon">📊</div>
                <div class="ai-stat-content">
                  <div class="ai-stat-label">总 Tokens</div>
                  <div class="ai-stat-value">{{ formatNumber(currentTask.aiStats.totalTokens) }}</div>
                </div>
              </div>
              <div class="ai-stat-item">
                <div class="ai-stat-icon">📝</div>
                <div class="ai-stat-content">
                  <div class="ai-stat-label">输入 Tokens</div>
                  <div class="ai-stat-value">{{ formatNumber(currentTask.aiStats.promptTokens) }}</div>
                </div>
              </div>
              <div class="ai-stat-item">
                <div class="ai-stat-icon">💬</div>
                <div class="ai-stat-content">
                  <div class="ai-stat-label">输出 Tokens</div>
                  <div class="ai-stat-value">{{ formatNumber(currentTask.aiStats.completionTokens) }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- AI Insights (when available) -->
          <div v-if="processCompleted && currentTask?.insights && currentTask.insights.length > 0" class="insights-section">
            <n-divider style="margin: 20px 0">💡 知识洞察</n-divider>
            <n-space vertical :size="8">
              <n-alert 
                v-for="(insight, index) in currentTask.insights" 
                :key="index"
                type="info"
                size="small"
                style="font-size: 13px;"
              >
                {{ insight }}
              </n-alert>
            </n-space>
          </div>

          <!-- Error Message -->
          <n-alert v-if="processFailed" type="error" style="margin-top: 16px">
            {{ progressMessage || '处理过程中发生错误' }}
          </n-alert>

          <!-- Actions -->
          <n-space vertical :size="12" style="margin-top: 20px">
            <n-button
              v-if="processCompleted"
              type="primary"
              @click="$router.push('/graph')"
              block
              size="large"
              class="action-button"
            >
              查看知识图谱
            </n-button>
            
            <n-button
              @click="resetUpload"
              block
              size="large"
            >
              <template #icon>
                <n-icon><add-circle-outline /></n-icon>
              </template>
              上传新文档
            </n-button>
          </n-space>
        </n-card>
      </transition>
    </n-space>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import { useProcessingStore } from '@/stores/processing'
import {
  CloudUploadOutline,
  DocumentTextOutline,
  CloseOutline,
  RocketOutline,
  CheckmarkCircleOutline,
  AddCircleOutline,
  GlobeOutline,
  LinkOutline,
  SparklesOutline
} from '@vicons/ionicons5'
import { uploadFile, uploadText, uploadUrl } from '@/api/services'

const router = useRouter()
const { t } = useI18n()
const message = useMessage()
const processingStore = useProcessingStore()

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

// Topic root state
const rootTopic = ref('')

// AI configuration state
const enableAI = ref(false)
const userPrompt = ref('')
const optimizePrompt = ref(true)

// Common state
const uploading = ref(false)
const uploadResult = ref(null)

// Current upload job ID for tracking
const currentJobId = ref(null)

// Processing state from global store
const currentTask = computed(() => {
  if (!currentJobId.value) return null
  return processingStore.tasks.get(currentJobId.value)
})

const processing = computed(() => currentTask.value?.status === 'processing')
const processCompleted = computed(() => currentTask.value?.status === 'completed')
const processFailed = computed(() => currentTask.value?.status === 'failed')
const progress = computed(() => currentTask.value?.progress || 0)
const progressMessage = computed(() => currentTask.value?.message || '')
const processStats = computed(() => currentTask.value?.stats)

// Watch for task cancellation to reset upload component state
watch(currentTask, (task) => {
  if (task && task.status === 'cancelled') {
    // Reset upload component state when task is cancelled
    uploading.value = false
    resetState()
  }
}, { immediate: false })

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString('zh-CN')
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
    resetState()
    message.success(t('upload.file_selected', { name: file.file.name }))
  }
}

const removeFile = () => {
  selectedFile.value = null
  resetState()
}

// Reset all state
const resetState = () => {
  uploadResult.value = null
  currentJobId.value = null
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    message.warning(t('upload.choose_file'))
    return
  }

  uploading.value = true
  resetState()
  
  try {
    const aiOptions = enableAI.value ? {
      enableAI: true,
      userPrompt: userPrompt.value || undefined,
      optimizePrompt: optimizePrompt.value
    } : undefined
    
    const options = {
      ...aiOptions,
      rootTopic: rootTopic.value || undefined
    }
    
    const result = await uploadFile(selectedFile.value, options)
    uploadResult.value = result
    
    if (result.status === 'duplicate') {
      message.warning(result.message || '文档已存在')
      uploading.value = false
      return
    }
    
    if (result.jobId) {
      message.success('文件上传成功，开始处理...')
      uploading.value = false
      currentJobId.value = result.jobId
      
      // Add task to global processing store
      processingStore.addTask({
        jobId: result.jobId,
        documentId: result.documentId,
        filename: result.filename,
        status: 'processing',
        progress: 0,
        message: '开始处理...'
      })
    } else {
      message.success(t('upload.upload_success'))
      uploading.value = false
    }
  } catch (error) {
    message.error(t('upload.error') + ': ' + error.message)
    uploading.value = false
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
  resetState()
  
  try {
    const aiOptions = enableAI.value ? {
      enableAI: true,
      userPrompt: userPrompt.value || undefined,
      optimizePrompt: optimizePrompt.value
    } : undefined
    
    const options = {
      ...aiOptions,
      rootTopic: rootTopic.value || undefined
    }
    
    const result = await uploadText(
      textContent.value,
      textTitle.value || undefined,
      true, // auto_process
      options
    )
    
    uploadResult.value = result
    
    if (result.status === 'duplicate') {
      message.warning(result.message || '文档已存在')
      uploading.value = false
      return
    }
    
    if (result.jobId) {
      message.success('文本已提交，开始处理...')
      uploading.value = false
      currentJobId.value = result.jobId
      
      // Add task to global processing store
      processingStore.addTask({
        jobId: result.jobId,
        documentId: result.documentId,
        filename: result.filename,
        status: 'processing',
        progress: 0,
        message: '开始处理...'
      })
    } else {
      message.success('文本已保存')
      uploading.value = false
    }
    
    // Clear form
    textContent.value = ''
    textTitle.value = ''
    rootTopic.value = ''
  } catch (error) {
    console.error('Text upload failed:', error)
    message.error(error.message || '文本提交失败')
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
  resetState()
  
  try {
    const aiOptions = enableAI.value ? {
      enableAI: true,
      userPrompt: userPrompt.value || undefined,
      optimizePrompt: optimizePrompt.value
    } : undefined
    
    const options = {
      ...aiOptions,
      rootTopic: rootTopic.value || undefined
    }
    
    const result = await uploadUrl(
      urlInput.value,
      urlTitle.value || undefined,
      true, // auto_process
      options
    )
    
    uploadResult.value = result
    
    if (result.status === 'duplicate') {
      message.warning(result.message || '文档已存在')
      uploading.value = false
      return
    }
    
    if (result.jobId) {
      message.success('网页内容已抓取，开始处理...')
      uploading.value = false
      currentJobId.value = result.jobId
      
      // Add task to global processing store
      processingStore.addTask({
        jobId: result.jobId,
        documentId: result.documentId,
        filename: result.filename,
        status: 'processing',
        progress: 0,
        message: '开始处理...'
      })
    } else {
      message.success('网页内容已保存')
      uploading.value = false
    }
    
    // Clear form
    urlInput.value = ''
    urlTitle.value = ''
    rootTopic.value = ''
  } catch (error) {
    console.error('URL upload failed:', error)
    message.error(error.message || '网页抓取失败')
    uploading.value = false
  }
}

const resetUpload = () => {
  selectedFile.value = null
  textContent.value = ''
  textTitle.value = ''
  urlInput.value = ''
  urlTitle.value = ''
  rootTopic.value = ''
  resetState()
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

  // Progress Card
  .progress-card {
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
    }

    .result-descriptions {
      :deep(.n-descriptions) {
        border-radius: 12px;
        overflow: hidden;
      }
    }

    .progress-section {
      padding: 20px;
      background: linear-gradient(135deg, rgba(194, 164, 116, 0.05) 0%, rgba(155, 135, 245, 0.05) 100%);
      border-radius: 12px;
      margin-bottom: 16px;

      .progress-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;

        .progress-label {
          font-size: 14px;
          font-weight: 600;
          color: #1e293b;
        }

        .progress-percent {
          font-size: 16px;
          font-weight: 700;
          color: #c2a474;
          letter-spacing: 0.5px;
        }
      }

      :deep(.n-progress) {
        .n-progress-graph {
          .n-progress-graph-line-fill {
            background: linear-gradient(90deg, #c2a474 0%, #9b87f5 50%, #f59e0b 100%);
          }
        }
      }
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-top: 20px;

      .stat-item {
        padding: 16px;
        background: linear-gradient(135deg, rgba(194, 164, 116, 0.08) 0%, rgba(155, 135, 245, 0.08) 100%);
        border-radius: 12px;
        text-align: center;
        border: 1px solid rgba(194, 164, 116, 0.15);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

        &:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(194, 164, 116, 0.2);
        }

        .stat-value {
          font-size: 28px;
          font-weight: 700;
          background: linear-gradient(135deg, #c2a474 0%, #9b87f5 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 13px;
          color: #64748b;
          font-weight: 500;
        }
      }
    }

    .action-button {
      height: 48px;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0.3px;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(194, 164, 116, 0.3);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(194, 164, 116, 0.4);
      }
    }

    // AI Stats Section
    .ai-stats-section {
      margin-top: 20px;

      .ai-stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;

        .ai-stat-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: linear-gradient(135deg, rgba(194, 164, 116, 0.08) 0%, rgba(155, 135, 245, 0.08) 100%);
          border-radius: 10px;
          border: 1px solid rgba(194, 164, 116, 0.15);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

          &:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(194, 164, 116, 0.2);
          }

          .ai-stat-icon {
            font-size: 24px;
            flex-shrink: 0;
          }

          .ai-stat-content {
            flex: 1;
            min-width: 0;

            .ai-stat-label {
              font-size: 12px;
              color: #64748b;
              font-weight: 500;
              margin-bottom: 4px;
            }

            .ai-stat-value {
              font-size: 18px;
              font-weight: 700;
              background: linear-gradient(135deg, #c2a474 0%, #9b87f5 100%);
              -webkit-background-clip: text;
              -webkit-text-fill-color: transparent;
              background-clip: text;
            }
          }
        }
      }
    }

    // Insights Section
    .insights-section {
      margin-top: 20px;
    }
  }

  // AI Config Section
  .ai-config-section {
    margin: 16px 0;

    :deep(.n-collapse) {
      border-radius: 12px;
      overflow: hidden;
      background: linear-gradient(135deg, rgba(194, 164, 116, 0.05) 0%, rgba(155, 135, 245, 0.05) 100%);
      border: 1px solid rgba(194, 164, 116, 0.2);
    }

    :deep(.n-collapse-item__header) {
      font-weight: 600;
      color: #1e293b;
      padding: 12px 16px;
    }

    :deep(.n-collapse-item__content-wrapper) {
      padding: 0 16px 16px;
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

