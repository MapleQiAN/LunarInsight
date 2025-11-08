<template>
  <n-config-provider :locale="naiveLocale" :date-locale="naiveDateLocale" :theme="theme">
    <n-global-style />
    <n-message-provider>
      <n-notification-provider>
        <n-dialog-provider>
          <AppContent />
        </n-dialog-provider>
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { NConfigProvider, NMessageProvider, NNotificationProvider, NDialogProvider, NGlobalStyle, zhCN, enUS, dateZhCN, dateEnUS, useMessage } from 'naive-ui'
import AppContent from './components/AppContent.vue'

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
  background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
}

.app-container {
  min-height: 100vh;
  width: 100%;
}

// Global Card Styles
:deep(.n-card) {
  border-radius: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  &.n-card--hoverable:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12) !important;
  }

  .n-card-header {
    font-weight: 700;
    font-size: 18px;
    padding: 20px 24px;
    border-bottom: 2px solid #f1f5f9;
  }

  .n-card__content {
    padding: 24px;
  }
}

// Global Button Styles - 月色奢华VIP金主题
:deep(.n-button) {
  border-radius: 10px;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none !important;

  &:focus {
    outline: none !important;
  }

  &.n-button--primary-type {
    background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%) !important;
    border: none !important;
    color: white;

    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #c9a668 0%, #9a7509 100%) !important;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(212, 175, 55, 0.4);
    }

    &:active:not(:disabled) {
      background: linear-gradient(135deg, #b8860b 0%, #8b6914 100%) !important;
      transform: translateY(0);
    }

    &:focus:not(:disabled) {
      box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.3);
    }
  }

  &.n-button--default-type {
    background: white;
    border: 1px solid #e0e0e0 !important;
    color: #666;

    &:hover:not(:disabled) {
      background: #fafafa;
      border-color: #d4af37 !important;
      color: #d4af37;
      transform: translateY(-2px);
    }

    &:active:not(:disabled) {
      background: #f0f0f0;
      transform: translateY(0);
    }

    &:focus:not(:disabled) {
      border-color: #d4af37 !important;
      box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.2);
    }
  }

  &.n-button--success-type {
    background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
    border: none !important;
    color: white;

    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #73d13d 0%, #52c41a 100%) !important;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(82, 196, 26, 0.4);
    }
  }

  &.n-button--warning-type {
    background: linear-gradient(135deg, #faad14 0%, #d48806 100%) !important;
    border: none !important;
    color: white;

    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #ffc53d 0%, #faad14 100%) !important;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(250, 173, 20, 0.4);
    }
  }

  &.n-button--error-type {
    background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%) !important;
    border: none !important;
    color: white;

    &:hover:not(:disabled) {
      background: linear-gradient(135deg, #ff7875 0%, #ff4d4f 100%) !important;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(255, 77, 79, 0.4);
    }
  }

  &.n-button--text-type {
    border: none !important;
    background: transparent;

    &.n-button--primary-type {
      color: #d4af37;

      &:hover:not(:disabled) {
        background: rgba(212, 175, 55, 0.1) !important;
        color: #b8860b;
        transform: none;
      }
    }

    &.n-button--error-type {
      color: #ff4d4f;

      &:hover:not(:disabled) {
        background: rgba(255, 77, 79, 0.1) !important;
        color: #cf1322;
        transform: none;
      }
    }
  }
}

// Global Input Styles
:deep(.n-input),
:deep(.n-input-number),
:deep(.n-select),
:deep(.n-date-picker) {
  .n-input__input-el,
  .n-input-number-input__input-el,
  .n-base-selection {
    border-radius: 10px;
  }
}

// Global Tag Styles
:deep(.n-tag) {
  font-weight: 600;
  padding: 6px 14px;

  &.n-tag--round {
    border-radius: 16px;
  }
}

// Global Alert Styles
:deep(.n-alert) {
  border-radius: 12px;
  border-left-width: 4px;
  font-weight: 500;
}

// Global Table Styles
:deep(.n-data-table) {
  .n-data-table-th {
    background: #f8fafc;
    font-weight: 700;
    color: #1e293b;
  }

  .n-data-table-td {
    padding: 16px 12px;
  }

  .n-data-table-tr:hover .n-data-table-td {
    background: rgba(99, 102, 241, 0.05);
  }
}

// Global Spin Styles
:deep(.n-spin) {
  .n-spin-description {
    margin-top: 12px;
    font-weight: 600;
    color: #64748b;
  }
}

// Scrollbar Styles - 月色奢华VIP金主题
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 5px;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
  border-radius: 5px;
  
  &:hover {
    background: linear-gradient(135deg, #c9a668 0%, #9a7509 100%);
  }
}

// Selection Colors - 月色奢华VIP金主题
::selection {
  background: rgba(212, 175, 55, 0.3);
  color: inherit;
}

::-moz-selection {
  background: rgba(212, 175, 55, 0.3);
  color: inherit;
}

// Utility Classes - 月色奢华VIP金主题
.text-gradient {
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.card-shadow {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.hover-lift {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    transform: translateY(-4px);
  }
}
</style>

