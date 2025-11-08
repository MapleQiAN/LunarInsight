<template>
  <el-container class="main-layout">
    <el-header class="header">
      <div class="header-content">
        <h1 class="title">{{ t('app.title') }}</h1>
        <p class="subtitle">{{ t('app.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-select v-model="currentLang" @change="handleLanguageChange" style="width: 120px">
          <el-option label="中文" value="zh" />
          <el-option label="English" value="en" />
        </el-select>
      </div>
    </el-header>
    <el-container>
      <el-aside width="240px" class="sidebar">
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/">
            <el-icon><DataBoard /></el-icon>
            <span>{{ t('navigation.dashboard') }}</span>
          </el-menu-item>
          <el-menu-item index="/upload">
            <el-icon><Upload /></el-icon>
            <span>{{ t('navigation.upload') }}</span>
          </el-menu-item>
          <el-menu-item index="/graph">
            <el-icon><Share /></el-icon>
            <span>{{ t('navigation.graph_visualization') }}</span>
          </el-menu-item>
          <el-menu-item index="/query">
            <el-icon><Search /></el-icon>
            <span>{{ t('navigation.query') }}</span>
          </el-menu-item>
          <el-menu-item index="/status">
            <el-icon><Document /></el-icon>
            <span>{{ t('navigation.status') }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import { DataBoard, Upload, Share, Search, Document } from '@element-plus/icons-vue'

const route = useRoute()
const { t, locale } = useI18n()
const appStore = useAppStore()

const activeMenu = computed(() => route.path)
const currentLang = ref(locale.value)

const handleLanguageChange = (lang) => {
  appStore.setLanguage(lang)
  locale.value = lang
}
</script>

<style lang="scss" scoped>
.main-layout {
  min-height: 100vh;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

  .header-content {
    .title {
      font-size: 2rem;
      font-weight: 700;
      margin: 0;
      letter-spacing: -0.02em;
    }

    .subtitle {
      font-size: 0.9rem;
      margin: 0.25rem 0 0 0;
      opacity: 0.9;
      letter-spacing: 0.05em;
    }
  }
}

.sidebar {
  background: white;
  border-right: 1px solid #e4e7ed;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);

  .sidebar-menu {
    border-right: none;
    padding-top: 1rem;
  }
}

.main-content {
  padding: 2rem;
  background: #f5f7fa;
}
</style>

