import axios, { type AxiosInstance, type InternalAxiosRequestConfig, type AxiosResponse } from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    // 使用 Naive UI 的全局消息 API
    if (window.$message) {
      window.$message.error(message)
    } else {
      console.error(message)
    }
    return Promise.reject(error)
  }
)

// 取消任务
export const cancelJob = (jobId: string) => {
  return api.delete(`/ingest/cancel/${jobId}`)
}

export default api

