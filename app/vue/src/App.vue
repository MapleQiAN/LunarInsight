<template>
  <el-config-provider :locale="elementLocale">
    <div id="app" class="app-container">
      <router-view />
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'

const { locale } = useI18n()

const elementLocale = computed(() => {
  return locale.value === 'zh' ? zhCn : en
})
</script>

<style lang="scss">
#app {
  font-family: 'Noto Serif SC', serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  background: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}
</style>

