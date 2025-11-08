<template>
  <n-layout class="main-layout">
    <!-- Top Header with Navigation -->
    <n-layout-header bordered class="header">
      <!-- Logo -->
      <div class="header-logo">
        <div class="logo-icon">
          <n-icon size="32"><cube-outline /></n-icon>
        </div>
        <div class="logo-text">
          <h2 class="logo-title">{{ t('app.title') }}</h2>
        </div>
      </div>

      <!-- Navigation Menu -->
      <div class="header-nav">
        <div
          v-for="item in menuOptions"
          :key="item.key"
          :class="['nav-item', { active: activeKey === item.key }]"
          @click="handleMenuSelect(item.key)"
        >
          {{ item.label }}
        </div>
      </div>

      <!-- Right Actions -->
      <div class="header-right">
        <n-space :size="12">
          <!-- Language Selector -->
          <n-dropdown trigger="hover" :options="languageOptions" @select="handleLanguageChange">
            <n-button text class="header-btn">
              <template #icon>
                <n-icon><globe-outline /></n-icon>
              </template>
              {{ currentLangLabel }}
            </n-button>
          </n-dropdown>

          <!-- Notifications -->
          <n-badge :value="0" :max="99" :show-zero="false">
            <n-button text class="header-btn">
              <template #icon>
                <n-icon size="20"><notifications-outline /></n-icon>
              </template>
            </n-button>
          </n-badge>

          <!-- User Menu -->
          <n-dropdown trigger="hover" :options="userMenuOptions" @select="handleUserMenuSelect">
            <n-button text class="header-btn">
              <n-avatar round size="small" src="https://07akioni.oss-cn-beijing.aliyuncs.com/07akioni.jpeg" />
            </n-button>
          </n-dropdown>
        </n-space>
      </div>
    </n-layout-header>

    <!-- Main Content Area -->
    <n-layout>
      <!-- Content -->
      <n-layout-content :native-scrollbar="false" class="main-content">
        <div class="content-wrapper">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </n-layout-content>
    </n-layout>

    <!-- Global Processing Floater -->
    <processing-floater />
  </n-layout>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import ProcessingFloater from '@/components/ProcessingFloater.vue'
import {
  CubeOutline,
  GlobeOutline,
  NotificationsOutline
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const appStore = useAppStore()

const activeKey = ref(route.path)

// Menu Options
const menuOptions = computed(() => [
  {
    label: t('navigation.dashboard'),
    key: '/'
  },
  {
    label: t('navigation.knowledge_build'),
    key: '/knowledge'
  },
  {
    label: t('navigation.knowledge_card'),
    key: '/knowledge-card'
  },
  {
    label: t('navigation.graph_visualization'),
    key: '/graph'
  },
  {
    label: t('navigation.query'),
    key: '/query'
  },
  {
    label: t('navigation.status'),
    key: '/status'
  }
])

// Language Options
const currentLangLabel = computed(() => locale.value === 'zh' ? '中文' : 'English')
const languageOptions = [
  {
    label: '中文',
    key: 'zh'
  },
  {
    label: 'English',
    key: 'en'
  }
]

// User Menu Options
const userMenuOptions = computed(() => [
  {
    label: t('common.profile'),
    key: 'profile'
  },
  {
    label: t('common.settings'),
    key: 'settings'
  },
  {
    type: 'divider'
  },
  {
    label: t('common.logout'),
    key: 'logout'
  }
])

// Menu Select Handler
const handleMenuSelect = (key) => {
  activeKey.value = key
  router.push(key)
}

// Language Change Handler
const handleLanguageChange = (key) => {
  appStore.setLanguage(key)
  locale.value = key
}

// User Menu Handler
const handleUserMenuSelect = (key) => {
  if (key === 'settings') {
    router.push('/settings')
  } else if (key === 'profile') {
    // TODO: implement profile page
    console.log('Profile not implemented yet')
  } else if (key === 'logout') {
    // TODO: implement logout
    console.log('Logout not implemented yet')
  }
}

// Watch route changes
watch(() => route.path, (newPath) => {
  activeKey.value = newPath
}, { immediate: true })
</script>

<style lang="scss" scoped>
.main-layout {
  min-height: 100vh;
  background: #f5f7fa;
  position: relative;
}

.header {
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 1000;

  .header-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;

    .logo-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
      border-radius: 10px;
      color: white;
      box-shadow: 0 4px 12px rgba(212, 175, 55, 0.3);
    }

    .logo-text {
      .logo-title {
        margin: 0;
        font-size: 20px;
        font-weight: 700;
        color: #111827;
      }
    }
  }

  .header-nav {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    justify-content: center;

    .nav-item {
      padding: 10px 20px;
      font-size: 14px;
      font-weight: 500;
      color: #6b7280;
      cursor: pointer;
      border-radius: 8px;
      transition: all 0.2s;
      white-space: nowrap;

      &:hover {
        color: #111827;
        background: #f3f4f6;
      }

      &.active {
        color: #b8860b;
        background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(218, 165, 32, 0.1) 100%);
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(212, 175, 55, 0.2);
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;

    :deep(.header-btn) {
      color: #6b7280;
      font-size: 14px;
      font-weight: 500;

      &:hover {
        color: #111827;
        background: #f3f4f6;
      }
    }

    :deep(.n-avatar) {
      border: 2px solid #e5e7eb;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        border-color: #d4af37;
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(212, 175, 55, 0.3);
      }
    }
  }
}

.main-content {
  padding: 0;
  min-height: calc(100vh - 70px);
  background: #f5f7fa;
  
  .content-wrapper {
    width: 100%;
    height: 100%;
  }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>

