import { defineStore } from 'pinia'
import { ref } from 'vue'
import i18n from '@/i18n'

export const useAppStore = defineStore('app', () => {
  const language = ref<string>(localStorage.getItem('language') || 'zh')
  const loading = ref<boolean>(false)

  const setLanguage = (lang: string) => {
    language.value = lang
    i18n.global.locale.value = lang as 'zh' | 'en'
    localStorage.setItem('language', lang)
  }

  return {
    language,
    loading,
    setLanguage
  }
})

