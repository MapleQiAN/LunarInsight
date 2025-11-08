<template>
  <n-layout class="main-layout" has-sider>
    <!-- Sidebar -->
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      :native-scrollbar="false"
      class="sidebar"
    >
      <div class="sidebar-header">
        <div v-if="!collapsed" class="logo-container">
          <h2 class="logo-title">{{ t('app.title') }}</h2>
          <p class="logo-subtitle">LunarInsight</p>
        </div>
        <div v-else class="logo-collapsed">
          <span class="logo-icon">月</span>
        </div>
      </div>
      
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        @update:value="handleMenuSelect"
      />
    </n-layout-sider>

    <!-- Main Content Area -->
    <n-layout>
      <!-- Header -->
      <n-layout-header bordered class="header">
        <div class="header-left">
          <n-breadcrumb>
            <n-breadcrumb-item v-for="(item, index) in breadcrumbs" :key="index">
              {{ item }}
            </n-breadcrumb-item>
          </n-breadcrumb>
        </div>
        
        <div class="header-right">
          <n-space :size="16">
            <!-- Language Selector -->
            <n-dropdown trigger="hover" :options="languageOptions" @select="handleLanguageChange">
              <n-button text>
                <template #icon>
                  <n-icon><globe-outline /></n-icon>
                </template>
                {{ currentLangLabel }}
              </n-button>
            </n-dropdown>

            <!-- Notifications -->
            <n-badge :value="0" :max="99">
              <n-button text>
                <template #icon>
                  <n-icon size="20"><notifications-outline /></n-icon>
                </template>
              </n-button>
            </n-badge>

            <!-- User Menu -->
            <n-dropdown trigger="hover" :options="userMenuOptions" @select="handleUserMenuSelect">
              <n-button text>
                <n-avatar round size="small" src="https://07akioni.oss-cn-beijing.aliyuncs.com/07akioni.jpeg" />
              </n-button>
            </n-dropdown>
          </n-space>
        </div>
      </n-layout-header>

      <!-- Tab Bar -->
      <div class="tab-bar" v-if="tabs.length > 0">
        <n-tabs
          type="card"
          :value="activeTab"
          closable
          @update:value="handleTabChange"
          @close="handleTabClose"
        >
          <n-tab
            v-for="tab in tabs"
            :key="tab.path"
            :name="tab.path"
            :tab="tab.title"
          />
        </n-tabs>
      </div>

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

      <!-- Footer -->
      <n-layout-footer bordered class="footer">
        <div class="footer-content">
          <span>© 2024 LunarInsight. All rights reserved.</span>
          <n-space :size="16">
            <a href="https://github.com" target="_blank">GitHub</a>
            <a href="#">Documentation</a>
            <a href="#">Support</a>
          </n-space>
        </div>
      </n-layout-footer>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { h, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { NIcon } from 'naive-ui'
import {
  StatsChartOutline,
  CloudUploadOutline,
  GitNetworkOutline,
  SearchOutline,
  TimeOutline,
  GlobeOutline,
  NotificationsOutline,
  PersonCircleOutline,
  LogOutOutline,
  SettingsOutline
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const appStore = useAppStore()

const collapsed = ref(false)
const activeKey = ref(route.path)
const activeTab = ref(route.path)
const tabs = ref([])

// Helper to render icons
const renderIcon = (icon) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

// Menu Options
const menuOptions = computed(() => [
  {
    label: t('navigation.dashboard'),
    key: '/',
    icon: renderIcon(StatsChartOutline)
  },
  {
    label: t('navigation.upload'),
    key: '/upload',
    icon: renderIcon(CloudUploadOutline)
  },
  {
    label: t('navigation.graph_visualization'),
    key: '/graph',
    icon: renderIcon(GitNetworkOutline)
  },
  {
    label: t('navigation.query'),
    key: '/query',
    icon: renderIcon(SearchOutline)
  },
  {
    label: t('navigation.status'),
    key: '/status',
    icon: renderIcon(TimeOutline)
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
const userMenuOptions = [
  {
    label: t('common.edit'),
    key: 'profile',
    icon: renderIcon(PersonCircleOutline)
  },
  {
    label: t('common.edit'),
    key: 'settings',
    icon: renderIcon(SettingsOutline)
  },
  {
    type: 'divider'
  },
  {
    label: 'Logout',
    key: 'logout',
    icon: renderIcon(LogOutOutline)
  }
]

// Breadcrumbs
const breadcrumbs = computed(() => {
  const paths = route.path.split('/').filter(Boolean)
  if (paths.length === 0) return [t('navigation.dashboard')]
  
  return paths.map((path) => {
    const menuItem = menuOptions.value.find(item => item.key === `/${path}`)
    return menuItem ? menuItem.label : path
  })
})

// Tab Management
const addTab = (path) => {
  const menuItem = menuOptions.value.find(item => item.key === path)
  if (menuItem && !tabs.value.find(tab => tab.path === path)) {
    tabs.value.push({
      path: path,
      title: menuItem.label
    })
  }
}

const handleTabChange = (path) => {
  activeTab.value = path
  router.push(path)
}

const handleTabClose = (path) => {
  const index = tabs.value.findIndex(tab => tab.path === path)
  if (index !== -1) {
    tabs.value.splice(index, 1)
    if (path === activeTab.value && tabs.value.length > 0) {
      const newActiveTab = tabs.value[Math.max(0, index - 1)]
      router.push(newActiveTab.path)
    }
  }
}

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
  console.log('User menu selected:', key)
  // Handle user menu actions
}

// Watch route changes
watch(() => route.path, (newPath) => {
  activeKey.value = newPath
  activeTab.value = newPath
  addTab(newPath)
}, { immediate: true })
</script>

<style lang="scss" scoped>
.main-layout {
  min-height: 100vh;
}

.sidebar {
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  
  .sidebar-header {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    border-bottom: 1px solid #efeff5;
    
    .logo-container {
      text-align: center;
      
      .logo-title {
        font-size: 20px;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px;
      }
      
      .logo-subtitle {
        font-size: 12px;
        margin: 4px 0 0 0;
        color: #999;
        letter-spacing: 1px;
      }
    }
    
    .logo-collapsed {
      .logo-icon {
        font-size: 24px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }
    }
  }
}

.header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  
  .header-left {
    flex: 1;
  }
  
  .header-right {
    display: flex;
    align-items: center;
  }
}

.tab-bar {
  padding: 8px 16px 0;
  background: #fff;
  border-bottom: 1px solid #efeff5;
}

.main-content {
  padding: 16px;
  min-height: calc(100vh - 64px - 53px - 64px); // header + tabs + footer
  
  .content-wrapper {
    max-width: 1600px;
    margin: 0 auto;
  }
}

.footer {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  
  .footer-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    font-size: 14px;
    color: #666;
    
    a {
      color: #666;
      text-decoration: none;
      transition: color 0.3s;
      
      &:hover {
        color: #18a058;
      }
    }
  }
}

// Transitions
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>

