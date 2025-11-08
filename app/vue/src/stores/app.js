import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

export const useAppStore = defineStore('app', () => {
  const { locale } = useI18n()
  const language = ref(localStorage.getItem('language') || 'zh')
  const loading = ref(false)

  const setLanguage = (lang) => {
    language.value = lang
    locale.value = lang
    localStorage.setItem('language', lang)
  }

  return {
    language,
    loading,
    setLanguage
  }
})

