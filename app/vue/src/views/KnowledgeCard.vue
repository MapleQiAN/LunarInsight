<template>
  <div class="knowledge-card-page">
    <n-space vertical :size="24">
      <!-- 页面头部 -->
      <n-page-header :title="$t('knowledge_card.title')" :subtitle="$t('knowledge_card.subtitle')">
        <template #extra>
          <n-button type="primary" @click="showCreateModal = true">
            <template #icon>
              <n-icon><AddOutline /></n-icon>
            </template>
            {{ $t('knowledge_card.create_card') }}
          </n-button>
        </template>
      </n-page-header>

      <!-- 筛选器 -->
      <n-card>
        <n-space>
          <n-select
            v-model:value="filterDomain"
            :options="domainOptions"
            :placeholder="$t('knowledge_card.filter_by_domain')"
            clearable
            style="width: 200px"
            @update:value="loadCards"
          />
          <n-select
            v-model:value="filterCategory"
            :options="categoryOptions"
            :placeholder="$t('knowledge_card.filter_by_category')"
            clearable
            style="width: 200px"
            @update:value="loadCards"
          />
        </n-space>
      </n-card>

      <!-- 卡片列表 -->
      <n-spin :show="loading">
        <n-empty v-if="!loading && cards.length === 0" :description="$t('knowledge_card.no_cards')" />
        
        <n-grid v-else :x-gap="16" :y-gap="16" :cols="1" responsive="screen">
          <n-grid-item v-for="card in cards" :key="card.id">
            <n-card :title="card.name" hoverable>
              <template #header-extra>
                <n-space>
                  <n-tag :type="getImportanceType(card.importance)">
                    {{ $t(`knowledge_card.importance_${card.importance}`) }}
                  </n-tag>
                  <n-button text @click="viewCard(card)">
                    <template #icon>
                      <n-icon><EyeOutline /></n-icon>
                    </template>
                  </n-button>
                  <n-button text @click="editCard(card)">
                    <template #icon>
                      <n-icon><CreateOutline /></n-icon>
                    </template>
                  </n-button>
                  <n-button text type="error" @click="confirmDelete(card)">
                    <template #icon>
                      <n-icon><TrashOutline /></n-icon>
                    </template>
                  </n-button>
                </n-space>
              </template>

              <n-space vertical :size="12">
                <n-text v-if="card.description">{{ card.description }}</n-text>
                <n-text v-else depth="3">{{ $t('knowledge_card.description_placeholder') }}</n-text>
                
                <n-space>
                  <n-tag v-if="card.domain" type="info">
                    {{ card.domain }}
                  </n-tag>
                  <n-tag v-if="card.category" type="success">
                    {{ card.category }}
                  </n-tag>
                  <n-tag v-for="tag in card.tags" :key="tag" :bordered="false">
                    {{ tag }}
                  </n-tag>
                </n-space>

                <n-space>
                  <n-text depth="3">
                    {{ $t('knowledge_card.connections') }}: {{ card.connection_count }}
                  </n-text>
                  <n-divider vertical />
                  <n-text depth="3">
                    {{ $t('knowledge_card.updated_at') }}: {{ formatDate(card.updated_at) }}
                  </n-text>
                </n-space>
              </n-space>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-spin>

      <!-- 统计信息 -->
      <n-card v-if="total > 0">
        <n-text>{{ $t('knowledge_card.total_cards', { count: total }) }}</n-text>
      </n-card>
    </n-space>

    <!-- 创建/编辑模态框 -->
    <n-modal
      v-model:show="showEditModal"
      :title="isEditing ? $t('knowledge_card.edit_card') : $t('knowledge_card.create_card')"
      preset="card"
      style="width: 800px"
      :segmented="{ content: 'soft' }"
    >
      <n-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-placement="top"
      >
        <n-tabs type="line" animated>
          <n-tab-pane :name="$t('knowledge_card.basic_info')" :tab="$t('knowledge_card.basic_info')">
            <n-space vertical :size="16">
              <n-form-item :label="$t('knowledge_card.card_name')" path="name">
                <n-input
                  v-model:value="formData.name"
                  :placeholder="$t('knowledge_card.card_name_placeholder')"
                  :disabled="isEditing"
                />
              </n-form-item>

              <n-form-item :label="$t('knowledge_card.description')" path="description">
                <n-input
                  v-model:value="formData.description"
                  type="textarea"
                  :placeholder="$t('knowledge_card.description_placeholder')"
                  :rows="3"
                />
              </n-form-item>

              <n-grid :cols="2" :x-gap="16">
                <n-grid-item>
                  <n-form-item :label="$t('knowledge_card.domain')" path="domain">
                    <n-input
                      v-model:value="formData.domain"
                      :placeholder="$t('knowledge_card.domain_placeholder')"
                    />
                  </n-form-item>
                </n-grid-item>
                <n-grid-item>
                  <n-form-item :label="$t('knowledge_card.category')" path="category">
                    <n-input
                      v-model:value="formData.category"
                      :placeholder="$t('knowledge_card.category_placeholder')"
                    />
                  </n-form-item>
                </n-grid-item>
              </n-grid>

              <n-form-item :label="$t('knowledge_card.importance')" path="importance">
                <n-radio-group v-model:value="formData.importance">
                  <n-space>
                    <n-radio value="low">{{ $t('knowledge_card.importance_low') }}</n-radio>
                    <n-radio value="medium">{{ $t('knowledge_card.importance_medium') }}</n-radio>
                    <n-radio value="high">{{ $t('knowledge_card.importance_high') }}</n-radio>
                  </n-space>
                </n-radio-group>
              </n-form-item>
            </n-space>
          </n-tab-pane>

          <n-tab-pane :name="$t('knowledge_card.additional_info')" :tab="$t('knowledge_card.additional_info')">
            <n-space vertical :size="16">
              <n-form-item :label="$t('knowledge_card.tags')" path="tags">
                <n-dynamic-tags v-model:value="formData.tags" />
              </n-form-item>

              <n-form-item :label="$t('knowledge_card.aliases')" path="aliases">
                <n-dynamic-tags v-model:value="formData.aliases" />
              </n-form-item>
            </n-space>
          </n-tab-pane>

          <n-tab-pane :name="$t('knowledge_card.relationships')" :tab="$t('knowledge_card.relationships')">
            <n-space vertical :size="16">
              <n-form-item :label="$t('knowledge_card.related_concepts')" path="related_concepts">
                <n-dynamic-tags v-model:value="formData.related_concepts" />
              </n-form-item>
            </n-space>
          </n-tab-pane>
        </n-tabs>
      </n-form>

      <template #footer>
        <n-space justify="end">
          <n-button @click="closeEditModal">{{ $t('knowledge_card.cancel') }}</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ isEditing ? $t('knowledge_card.update') : $t('knowledge_card.create') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 查看详情模态框 -->
    <n-modal
      v-model:show="showViewModal"
      :title="viewingCard?.name"
      preset="card"
      style="width: 700px"
    >
      <n-descriptions v-if="viewingCard" :column="2" bordered>
        <n-descriptions-item :label="$t('knowledge_card.card_name')">
          {{ viewingCard.name }}
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.importance')">
          <n-tag :type="getImportanceType(viewingCard.importance)">
            {{ $t(`knowledge_card.importance_${viewingCard.importance}`) }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.domain')">
          {{ viewingCard.domain || '-' }}
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.category')">
          {{ viewingCard.category || '-' }}
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.description')" :span="2">
          {{ viewingCard.description || '-' }}
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.tags')" :span="2">
          <n-space v-if="viewingCard.tags.length > 0">
            <n-tag v-for="tag in viewingCard.tags" :key="tag">{{ tag }}</n-tag>
          </n-space>
          <n-text v-else depth="3">-</n-text>
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.aliases')" :span="2">
          <n-space v-if="viewingCard.aliases.length > 0">
            <n-tag v-for="alias in viewingCard.aliases" :key="alias" type="info">{{ alias }}</n-tag>
          </n-space>
          <n-text v-else depth="3">-</n-text>
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.related_concepts')" :span="2">
          <n-space v-if="viewingCard.related_concepts.length > 0">
            <n-tag v-for="concept in viewingCard.related_concepts" :key="concept" type="success">
              {{ concept }}
            </n-tag>
          </n-space>
          <n-text v-else depth="3">-</n-text>
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.connections')">
          {{ viewingCard.connection_count }}
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.created_at')">
          {{ formatDate(viewingCard.created_at) }}
        </n-descriptions-item>
        <n-descriptions-item :label="$t('knowledge_card.updated_at')" :span="2">
          {{ formatDate(viewingCard.updated_at) }}
        </n-descriptions-item>
      </n-descriptions>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import {
  AddOutline,
  CreateOutline,
  TrashOutline,
  EyeOutline
} from '@vicons/ionicons5'

const { t } = useI18n()
const message = useMessage()
const dialog = useDialog()

// 数据
const cards = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const submitting = ref(false)

// 筛选
const filterDomain = ref<string | null>(null)
const filterCategory = ref<string | null>(null)

// 模态框
const showEditModal = computed({
  get: () => showCreateModal.value || showUpdateModal.value,
  set: (val) => {
    if (!val) {
      showCreateModal.value = false
      showUpdateModal.value = false
    }
  }
})
const showCreateModal = ref(false)
const showUpdateModal = ref(false)
const showViewModal = ref(false)
const isEditing = computed(() => showUpdateModal.value)

// 表单
const formRef = ref()
const formData = reactive({
  name: '',
  description: '',
  domain: '',
  category: '',
  importance: 'medium',
  tags: [] as string[],
  aliases: [] as string[],
  related_concepts: [] as string[],
  attributes: {}
})

const formRules = {
  name: [
    { required: true, message: t('knowledge_card.card_name_required'), trigger: 'blur' }
  ]
}

const viewingCard = ref<any>(null)
const editingCardId = ref<string | null>(null)

// 选项
const domainOptions = computed(() => {
  const domains = new Set(cards.value.map(c => c.domain).filter(Boolean))
  return [
    { label: t('knowledge_card.all'), value: null },
    ...Array.from(domains).map(d => ({ label: d, value: d }))
  ]
})

const categoryOptions = computed(() => {
  const categories = new Set(cards.value.map(c => c.category).filter(Boolean))
  return [
    { label: t('knowledge_card.all'), value: null },
    ...Array.from(categories).map(c => ({ label: c, value: c }))
  ]
})

// 方法
const loadCards = async () => {
  loading.value = true
  try {
    const params: any = { limit: 100 }
    if (filterDomain.value) params.domain = filterDomain.value
    if (filterCategory.value) params.category = filterCategory.value

    const response = await api.get('/knowledge-cards', { params })
    cards.value = response.cards || []
    total.value = response.total || 0
  } catch (error: any) {
    message.error(error.response?.data?.detail || t('knowledge_card.load_failed'))
  } finally {
    loading.value = false
  }
}

const viewCard = (card: any) => {
  viewingCard.value = card
  showViewModal.value = true
}

const editCard = (card: any) => {
  editingCardId.value = card.id
  Object.assign(formData, {
    name: card.name,
    description: card.description || '',
    domain: card.domain || '',
    category: card.category || '',
    importance: card.importance || 'medium',
    tags: [...(card.tags || [])],
    aliases: [...(card.aliases || [])],
    related_concepts: [...(card.related_concepts || [])],
    attributes: { ...(card.attributes || {}) }
  })
  showUpdateModal.value = true
}

const confirmDelete = (card: any) => {
  dialog.warning({
    title: t('knowledge_card.confirm_delete'),
    content: t('knowledge_card.confirm_delete_message', { name: card.name }),
    positiveText: t('knowledge_card.delete'),
    negativeText: t('knowledge_card.cancel'),
    onPositiveClick: async () => {
      try {
        await api.delete(`/knowledge-cards/${card.id}`)
        message.success(t('knowledge_card.delete_success'))
        await loadCards()
      } catch (error: any) {
        message.error(error.response?.data?.detail || t('knowledge_card.delete_failed'))
      }
    }
  })
}

const handleSubmit = async () => {
  try {
    await formRef.value?.validate()
    submitting.value = true

    const payload = {
      name: formData.name,
      description: formData.description || undefined,
      domain: formData.domain || undefined,
      category: formData.category || undefined,
      importance: formData.importance,
      tags: formData.tags,
      aliases: formData.aliases,
      related_concepts: formData.related_concepts,
      attributes: formData.attributes
    }

    if (isEditing.value) {
      await api.put(`/knowledge-cards/${editingCardId.value}`, payload)
      message.success(t('knowledge_card.update_success'))
    } else {
      await api.post('/knowledge-cards', payload)
      message.success(t('knowledge_card.create_success'))
    }

    closeEditModal()
    await loadCards()
  } catch (error: any) {
    if (error?.errors) {
      // 表单验证错误
      return
    }
    const msg = isEditing.value ? t('knowledge_card.update_failed') : t('knowledge_card.create_failed')
    message.error(error.response?.data?.detail || msg)
  } finally {
    submitting.value = false
  }
}

const closeEditModal = () => {
  showCreateModal.value = false
  showUpdateModal.value = false
  editingCardId.value = null
  formRef.value?.restoreValidation()
  Object.assign(formData, {
    name: '',
    description: '',
    domain: '',
    category: '',
    importance: 'medium',
    tags: [],
    aliases: [],
    related_concepts: [],
    attributes: {}
  })
}

const getImportanceType = (importance: string) => {
  const types: Record<string, any> = {
    low: 'default',
    medium: 'info',
    high: 'warning'
  }
  return types[importance] || 'default'
}

const formatDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString()
  } catch {
    return dateStr
  }
}

onMounted(() => {
  loadCards()
})
</script>

<style scoped>
.knowledge-card-page {
  padding: 24px;
}
</style>

