<template>
  <div class="settings-view">
    <div class="settings-container">
      <!-- Header -->
      <div class="settings-header">
        <h1 class="title">{{ t('settings.title') }}</h1>
        <p class="subtitle">{{ t('settings.subtitle') }}</p>
      </div>

      <!-- AI Provider Settings -->
      <n-card :title="t('settings.ai_provider')" class="settings-card">
        <n-form
          ref="formRef"
          :model="formData"
          :rules="formRules"
          label-placement="left"
          label-width="150"
          require-mark-placement="right-hanging"
        >
          <n-form-item :label="t('settings.provider_type')" path="ai_provider">
            <n-select
              v-model:value="formData.ai_provider"
              :options="providerOptions"
              @update:value="handleProviderChange"
            />
          </n-form-item>

          <!-- OpenAI Settings -->
          <n-divider v-if="formData.ai_provider === 'openai'" title-placement="left">
            OpenAI {{ t('settings.configuration') }}
          </n-divider>

          <template v-if="formData.ai_provider === 'openai'">
            <n-form-item :label="t('settings.api_key')" path="openai_api_key">
              <n-input
                v-model:value="formData.openai_api_key"
                type="password"
                show-password-on="click"
                :placeholder="t('settings.api_key_placeholder')"
              />
            </n-form-item>

            <n-form-item :label="t('settings.model')" path="openai_model">
              <n-input
                v-model:value="formData.openai_model"
                :placeholder="'gpt-4o-mini'"
              />
            </n-form-item>

            <n-form-item :label="t('settings.base_url')" path="openai_base_url">
              <n-input
                v-model:value="formData.openai_base_url"
                :placeholder="t('settings.base_url_placeholder')"
              />
            </n-form-item>
          </template>

          <!-- Ollama Settings -->
          <n-divider v-if="formData.ai_provider === 'ollama'" title-placement="left">
            Ollama {{ t('settings.configuration') }}
          </n-divider>

          <template v-if="formData.ai_provider === 'ollama'">
            <n-form-item :label="t('settings.base_url')" path="ollama_base_url">
              <n-input
                v-model:value="formData.ollama_base_url"
                placeholder="http://localhost:11434"
              />
            </n-form-item>

            <n-form-item :label="t('settings.model')" path="ollama_model">
              <n-space vertical style="width: 100%">
                <n-select
                  v-model:value="formData.ollama_model"
                  :options="ollamaModelOptions"
                  :loading="loadingModels"
                  filterable
                  tag
                  :placeholder="t('settings.select_or_type_model')"
                />
                <n-button
                  text
                  type="primary"
                  size="small"
                  @click="fetchOllamaModels"
                  :loading="loadingModels"
                >
                  <template #icon>
                    <n-icon><refresh-outline /></n-icon>
                  </template>
                  {{ t('settings.refresh_models') }}
                </n-button>
              </n-space>
            </n-form-item>
          </template>

          <!-- Action Buttons -->
          <n-space justify="end" style="margin-top: 24px">
            <n-button @click="testConnection" :loading="testing">
              <template #icon>
                <n-icon><flash-outline /></n-icon>
              </template>
              {{ t('settings.test_connection') }}
            </n-button>

            <n-button type="primary" @click="saveSettings" :loading="saving">
              <template #icon>
                <n-icon><save-outline /></n-icon>
              </template>
              {{ t('settings.save') }}
            </n-button>
          </n-space>
        </n-form>
      </n-card>

      <!-- Database Settings (Read-only) -->
      <n-card :title="t('settings.database')" class="settings-card">
        <n-descriptions bordered :column="1">
          <n-descriptions-item :label="t('settings.neo4j_uri')">
            {{ formData.neo4j_uri }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('settings.neo4j_user')">
            {{ formData.neo4j_user }}
          </n-descriptions-item>
          <n-descriptions-item :label="t('settings.redis_url')">
            {{ formData.redis_url }}
          </n-descriptions-item>
        </n-descriptions>
        <n-alert type="info" style="margin-top: 16px">
          {{ t('settings.database_readonly_notice') }}
        </n-alert>
      </n-card>

      <!-- Help Information -->
      <n-card :title="t('settings.help')" class="settings-card">
        <n-space vertical>
          <div>
            <strong>{{ t('settings.how_to_use_ollama') }}</strong>
            <n-ol style="margin-top: 8px">
              <n-li>{{ t('settings.ollama_step1') }}</n-li>
              <n-li>{{ t('settings.ollama_step2') }}</n-li>
              <n-li>{{ t('settings.ollama_step3') }}</n-li>
            </n-ol>
          </div>

          <n-divider />

          <div>
            <strong>{{ t('settings.how_to_use_openai') }}</strong>
            <n-ol style="margin-top: 8px">
              <n-li>{{ t('settings.openai_step1') }}</n-li>
              <n-li>{{ t('settings.openai_step2') }}</n-li>
            </n-ol>
          </div>
        </n-space>
      </n-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMessage } from 'naive-ui'
import {
  FlashOutline,
  SaveOutline,
  RefreshOutline
} from '@vicons/ionicons5'
import {
  getSettings,
  updateAISettings,
  testAIConnection,
  getOllamaModels
} from '@/api/services'

const { t } = useI18n()
const message = useMessage()

// Form data
const formRef = ref(null)
const formData = ref({
  ai_provider: 'mock',
  openai_api_key: '',
  openai_model: 'gpt-4o-mini',
  openai_base_url: '',
  ollama_base_url: 'http://localhost:11434',
  ollama_model: 'llama3',
  neo4j_uri: '',
  neo4j_user: '',
  redis_url: ''
})

// Loading states
const saving = ref(false)
const testing = ref(false)
const loadingModels = ref(false)

// Ollama models
const ollamaModels = ref([])
const ollamaModelOptions = computed(() => 
  ollamaModels.value.map(model => ({
    label: model,
    value: model
  }))
)

// Provider options
const providerOptions = [
  { label: 'Mock (测试模式)', value: 'mock' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Ollama (本地)', value: 'ollama' }
]

// Form rules
const formRules = {
  ai_provider: {
    required: true,
    message: t('settings.provider_required'),
    trigger: 'change'
  },
  openai_api_key: {
    required: true,
    message: t('settings.api_key_required'),
    trigger: 'blur'
  }
}

// Load settings
const loadSettings = async () => {
  try {
    const response = await getSettings()
    if (response) {
      Object.assign(formData.value, response)
      // If API key is masked, clear it
      if (formData.value.openai_api_key === '***') {
        formData.value.openai_api_key = ''
      }
      
      // If provider is ollama, automatically fetch models and ensure saved model is in list
      if (formData.value.ai_provider === 'ollama') {
        await fetchOllamaModels(true) // silent mode (no success message)
        // Ensure saved model is in the options list
        if (formData.value.ollama_model && !ollamaModels.value.includes(formData.value.ollama_model)) {
          ollamaModels.value.push(formData.value.ollama_model)
        }
      }
    }
  } catch (error) {
    message.error(t('settings.load_failed'))
    console.error('Failed to load settings:', error)
  }
}

// Fetch Ollama models
const fetchOllamaModels = async (silent = false) => {
  loadingModels.value = true
  try {
    const response = await getOllamaModels()
    if (response.success) {
      const savedModel = formData.value.ollama_model
      ollamaModels.value = response.models
      
      // Ensure saved model is in the list even if not returned from API
      if (savedModel && !ollamaModels.value.includes(savedModel)) {
        ollamaModels.value.push(savedModel)
      }
      
      if (!silent) {
        message.success(t('settings.models_loaded', { count: ollamaModels.value.length }))
      }
    } else {
      if (!silent) {
        message.warning(response.message)
      }
    }
  } catch (error) {
    if (!silent) {
      message.error(t('settings.fetch_models_failed'))
    }
    console.error('Failed to fetch Ollama models:', error)
  } finally {
    loadingModels.value = false
  }
}

// Handle provider change
const handleProviderChange = (value) => {
  if (value === 'ollama' && ollamaModels.value.length === 0) {
    fetchOllamaModels()
  }
}

// Test connection
const testConnection = async () => {
  testing.value = true
  try {
    const response = await testAIConnection({
      ai_provider: formData.value.ai_provider,
      openai_api_key: formData.value.openai_api_key,
      openai_model: formData.value.openai_model,
      openai_base_url: formData.value.openai_base_url,
      ollama_base_url: formData.value.ollama_base_url,
      ollama_model: formData.value.ollama_model
    })

    if (response.success) {
      message.success(response.message)
    } else {
      message.error(response.message)
    }
  } catch (error) {
    message.error(t('settings.test_failed'))
    console.error('Test connection failed:', error)
  } finally {
    testing.value = false
  }
}

// Save settings
const saveSettings = async () => {
  try {
    await formRef.value?.validate()
    
    saving.value = true
    const response = await updateAISettings({
      ai_provider: formData.value.ai_provider,
      openai_api_key: formData.value.openai_api_key,
      openai_model: formData.value.openai_model,
      openai_base_url: formData.value.openai_base_url,
      ollama_base_url: formData.value.ollama_base_url,
      ollama_model: formData.value.ollama_model
    })

    if (response.success) {
      message.success(response.message)
      // Reload settings to ensure form displays the saved values from backend
      await loadSettings()
    } else {
      message.error(response.message || t('settings.save_failed'))
    }
  } catch (error) {
    if (error?.errors) {
      // Validation errors
      return
    }
    message.error(t('settings.save_failed'))
    console.error('Failed to save settings:', error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style lang="scss" scoped>
.settings-view {
  padding: 24px;
  min-height: 100%;
  background: #f5f7fa;
}

.settings-container {
  max-width: 900px;
  margin: 0 auto;
}

.settings-header {
  margin-bottom: 24px;
  
  .title {
    font-size: 28px;
    font-weight: 700;
    color: #111827;
    margin: 0 0 8px 0;
  }
  
  .subtitle {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }
}

.settings-card {
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  
  :deep(.n-card-header) {
    font-weight: 600;
    font-size: 18px;
    color: #111827;
  }
}

:deep(.n-form-item-label) {
  font-weight: 500;
  color: #374151;
}

:deep(.n-alert) {
  border-radius: 8px;
}

:deep(.n-ol) {
  margin-left: 0;
  padding-left: 20px;
}

:deep(.n-li) {
  margin-bottom: 8px;
  color: #4b5563;
}
</style>

