<template>
  <n-config-provider :locale="naiveLocale" :date-locale="naiveDateLocale" :theme="theme">
    <n-global-style />
    <n-message-provider>
      <n-notification-provider>
        <n-dialog-provider>
          <div id="app" class="app-container">
            <router-view />
          </div>
        </n-dialog-provider>
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { NConfigProvider, NMessageProvider, NNotificationProvider, NDialogProvider, NGlobalStyle, zhCN, enUS, dateZhCN, dateEnUS } from 'naive-ui'

const { locale } = useI18n()
const theme = ref(null) // null for light theme, darkTheme for dark theme

const naiveLocale = computed(() => {
  return locale.value === 'zh' ? zhCN : enUS
})

const naiveDateLocale = computed(() => {
  return locale.value === 'zh' ? dateZhCN : dateEnUS
})
</script>

<style lang="scss">
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Noto Serif SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  background: #f5f7fa;
}

.app-container {
  min-height: 100vh;
  width: 100%;
}
</style>

