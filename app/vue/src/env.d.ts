/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  // 可以在这里添加更多环境变量
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Naive UI 全局消息类型
interface Window {
  $message?: {
    error: (msg: string) => void
    success: (msg: string) => void
    warning: (msg: string) => void
    info: (msg: string) => void
  }
}

