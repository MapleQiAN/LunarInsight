import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getJobStatus } from '@/api/services'
import type { JobStatus } from '@/api/services'
import { cancelJob } from '@/api/index'

export interface ProcessingTask {
  jobId: string
  documentId: string
  filename: string
  status: 'processing' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message: string
  stats?: {
    chunks: number
    triplets: number
    concepts: number
  }
  aiMode?: boolean
  aiStats?: {
    totalTokens?: number
    promptTokens?: number
    completionTokens?: number
    model?: string
  }
  insights?: string[]
  createdAt: number
}

export const useProcessingStore = defineStore('processing', () => {
  // 当前处理中的任务列表
  const tasks = ref<Map<string, ProcessingTask>>(new Map())
  
  // 轮询定时器
  const pollTimers = ref<Map<string, number>>(new Map())
  
  // 浮窗是否显示
  const floaterVisible = ref(false)
  
  // 是否最小化
  const minimized = ref(false)

  // 计算属性：是否有任务
  const hasTasks = computed(() => tasks.value.size > 0)
  
  // 计算属性：处理中的任务数量
  const processingCount = computed(() => {
    return Array.from(tasks.value.values()).filter(
      task => task.status === 'processing'
    ).length
  })
  
  // 计算属性：已完成的任务数量
  const completedCount = computed(() => {
    return Array.from(tasks.value.values()).filter(
      task => task.status === 'completed'
    ).length
  })
  
  // 计算属性：失败的任务数量
  const failedCount = computed(() => {
    return Array.from(tasks.value.values()).filter(
      task => task.status === 'failed'
    ).length
  })
  
  // 计算属性：任务列表（按创建时间倒序）
  const taskList = computed(() => {
    return Array.from(tasks.value.values())
      .sort((a, b) => b.createdAt - a.createdAt)
  })

  // 添加任务
  const addTask = (task: Omit<ProcessingTask, 'createdAt'>) => {
    const fullTask = {
      ...task,
      createdAt: Date.now()
    }
    tasks.value.set(task.jobId, fullTask)
    floaterVisible.value = true
    startPolling(task.jobId)
  }

  // 更新任务
  const updateTask = (jobId: string, updates: Partial<ProcessingTask>) => {
    const task = tasks.value.get(jobId)
    if (task) {
      tasks.value.set(jobId, { ...task, ...updates })
    }
  }

  // 删除任务
  const removeTask = (jobId: string) => {
    stopPolling(jobId)
    tasks.value.delete(jobId)
    if (tasks.value.size === 0) {
      floaterVisible.value = false
    }
  }

  // 清除所有已完成和失败的任务
  const clearFinishedTasks = () => {
    const toRemove: string[] = []
    tasks.value.forEach((task, jobId) => {
      if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
        toRemove.push(jobId)
      }
    })
    toRemove.forEach(jobId => removeTask(jobId))
  }

  // 取消任务
  const cancelTask = async (jobId: string) => {
    try {
      await cancelJob(jobId)
      
      // 更新本地任务状态
      const task = tasks.value.get(jobId)
      if (task) {
        updateTask(jobId, {
          status: 'cancelled',
          message: '任务已取消'
        })
        stopPolling(jobId)
      }
      
      return true
    } catch (error) {
      console.error(`Failed to cancel job ${jobId}:`, error)
      return false
    }
  }

  // 开始轮询任务状态
  const startPolling = (jobId: string) => {
    // 如果已有定时器，先清除
    stopPolling(jobId)
    
    const poll = async () => {
      try {
        const status: JobStatus = await getJobStatus(jobId)
        const task = tasks.value.get(jobId)
        
        if (!task) return
        
        updateTask(jobId, {
          progress: status.progress || 0,
          message: status.message || '',
          stats: status.stats,
          aiMode: status.ai_mode,
          aiStats: status.ai_stats ? {
            totalTokens: status.ai_stats.total_tokens,
            promptTokens: status.ai_stats.prompt_tokens,
            completionTokens: status.ai_stats.completion_tokens,
            model: status.ai_stats.model
          } : undefined,
          insights: status.insights
        })
        
        if (status.status === 'completed') {
          updateTask(jobId, { status: 'completed' })
          stopPolling(jobId)
        } else if (status.status === 'failed') {
          updateTask(jobId, { 
            status: 'failed',
            message: status.error || status.message || '处理失败'
          })
          stopPolling(jobId)
        } else if (status.status === 'cancelled') {
          updateTask(jobId, { 
            status: 'cancelled',
            message: status.message || '任务已取消'
          })
          stopPolling(jobId)
        }
      } catch (error) {
        console.error(`Failed to poll job ${jobId}:`, error)
      }
    }
    
    // 立即执行一次
    poll()
    
    // 每秒轮询
    const timer = window.setInterval(poll, 1000)
    pollTimers.value.set(jobId, timer)
  }

  // 停止轮询
  const stopPolling = (jobId: string) => {
    const timer = pollTimers.value.get(jobId)
    if (timer) {
      clearInterval(timer)
      pollTimers.value.delete(jobId)
    }
  }

  // 停止所有轮询
  const stopAllPolling = () => {
    pollTimers.value.forEach((timer) => clearInterval(timer))
    pollTimers.value.clear()
  }

  // 切换浮窗显示
  const toggleFloater = () => {
    floaterVisible.value = !floaterVisible.value
  }

  // 显示浮窗
  const showFloater = () => {
    floaterVisible.value = true
  }

  // 隐藏浮窗
  const hideFloater = () => {
    floaterVisible.value = false
  }

  // 切换最小化
  const toggleMinimize = () => {
    minimized.value = !minimized.value
  }

  return {
    tasks,
    floaterVisible,
    minimized,
    hasTasks,
    processingCount,
    completedCount,
    failedCount,
    taskList,
    addTask,
    updateTask,
    removeTask,
    clearFinishedTasks,
    cancelTask,
    startPolling,
    stopPolling,
    stopAllPolling,
    toggleFloater,
    showFloater,
    hideFloater,
    toggleMinimize
  }
})

