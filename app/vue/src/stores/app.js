import { defineStore } from 'pinia'
import { ref } from 'vue'
import i18n from '@/i18n'

export const useAppStore = defineStore('app', () => {
  const language = ref(localStorage.getItem('language') || 'zh')
  const loading = ref(false)

  const setLanguage = (lang) => {
    language.value = lang
    i18n.global.locale.value = lang
    localStorage.setItem('language', lang)
  }

  return {
    language,
    loading,
    setLanguage
  }
})

