import { createI18n } from 'vue-i18n'
import zh from './locales/zh.json'
import en from './locales/en.json'

export type MessageSchema = typeof zh

const messages = {
  zh,
  en
}

const i18n = createI18n<[MessageSchema], 'zh' | 'en'>({
  legacy: false,
  locale: localStorage.getItem('language') || 'zh',
  fallbackLocale: 'zh',
  messages
})

export default i18n

