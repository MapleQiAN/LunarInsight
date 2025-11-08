<template>
  <transition name="floater-slide">
    <div v-if="processingStore.floaterVisible && processingStore.hasTasks" class="processing-floater" :class="{ minimized: processingStore.minimized }">
      <!-- Header -->
      <div class="floater-header">
        <div class="header-left">
          <n-icon size="18" :component="RocketOutline" class="header-icon" />
          <span class="header-title">
            处理进度
            <n-badge 
              v-if="processingStore.processingCount > 0"
              :value="processingStore.processingCount" 
              :max="99"
              type="info"
              style="margin-left: 8px"
            />
          </span>
        </div>
        <div class="header-actions">
          <n-button text size="small" @click="processingStore.toggleMinimize">
            <template #icon>
              <n-icon :component="processingStore.minimized ? ChevronUpOutline : ChevronDownOutline" />
            </template>
          </n-button>
          <n-button text size="small" @click="handleClose">
            <template #icon>
              <n-icon :component="CloseOutline" />
            </template>
          </n-button>
        </div>
      </div>

      <!-- Task List -->
      <transition name="expand">
        <div v-if="!processingStore.minimized" class="floater-content">
          <n-scrollbar style="max-height: 400px">
            <div class="task-list">
              <transition-group name="task-slide">
                <div 
                  v-for="task in processingStore.taskList" 
                  :key="task.jobId" 
                  class="task-item"
                  :class="task.status"
                >
                  <!-- Task Header -->
                  <div class="task-header">
                    <div class="task-info">
                      <n-icon 
                        size="16" 
                        class="task-icon"
                        :component="getStatusIcon(task.status)"
                      />
                      <span class="task-filename" :title="task.filename">{{ task.filename }}</span>
                    </div>
                    <n-button 
                      v-if="task.status !== 'processing'"
                      text 
                      size="tiny" 
                      @click="processingStore.removeTask(task.jobId)"
                    >
                      <template #icon>
                        <n-icon :component="CloseOutline" />
                      </template>
                    </n-button>
                  </div>

                  <!-- Progress Bar (processing only) -->
                  <div v-if="task.status === 'processing'" class="task-progress">
                    <div class="progress-info">
                      <span class="progress-message">{{ task.message || '处理中...' }}</span>
                      <span class="progress-percent">{{ task.progress }}%</span>
                    </div>
                    <n-progress
                      type="line"
                      :percentage="task.progress"
                      :show-indicator="false"
                      :height="6"
                      border-radius="3px"
                      :color="getProgressColor(task.status)"
                    />
                  </div>

                  <!-- Status Message (completed/failed) -->
                  <div v-else class="task-status">
                    <span class="status-message">{{ task.message || getStatusMessage(task.status) }}</span>
                  </div>

                  <!-- Stats (completed only) -->
                  <div v-if="task.status === 'completed' && task.stats" class="task-stats">
                    <div class="stat-chip">
                      <span class="stat-label">文本块</span>
                      <span class="stat-value">{{ task.stats.chunks }}</span>
                    </div>
                    <div class="stat-chip">
                      <span class="stat-label">三元组</span>
                      <span class="stat-value">{{ task.stats.triplets }}</span>
                    </div>
                    <div class="stat-chip">
                      <span class="stat-label">概念</span>
                      <span class="stat-value">{{ task.stats.concepts }}</span>
                    </div>
                  </div>
                </div>
              </transition-group>
            </div>
          </n-scrollbar>

          <!-- Footer Actions -->
          <div class="floater-footer">
            <n-button 
              v-if="processingStore.completedCount > 0 || processingStore.failedCount > 0"
              text 
              size="small" 
              @click="processingStore.clearFinishedTasks"
            >
              清除已完成
            </n-button>
            <n-button 
              v-if="processingStore.completedCount > 0"
              type="primary" 
              size="small" 
              @click="handleViewGraph"
            >
              查看图谱
            </n-button>
          </div>
        </div>
      </transition>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useProcessingStore } from '@/stores/processing'
import {
  RocketOutline,
  CloseOutline,
  ChevronUpOutline,
  ChevronDownOutline,
  CheckmarkCircleOutline,
  AlertCircleOutline,
  TimeOutline
} from '@vicons/ionicons5'

const router = useRouter()
const message = useMessage()
const processingStore = useProcessingStore()

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return CheckmarkCircleOutline
    case 'failed':
      return AlertCircleOutline
    default:
      return TimeOutline
  }
}

const getStatusMessage = (status: string) => {
  switch (status) {
    case 'completed':
      return '处理完成'
    case 'failed':
      return '处理失败'
    default:
      return '处理中'
  }
}

const getProgressColor = (status: string) => {
  switch (status) {
    case 'completed':
      return '#18a058'
    case 'failed':
      return '#d03050'
    default:
      return '#c2a474'
  }
}

const handleClose = () => {
  if (processingStore.processingCount > 0) {
    message.warning('仍有任务正在处理中')
    return
  }
  processingStore.hideFloater()
}

const handleViewGraph = () => {
  router.push('/graph')
}
</script>

<style lang="scss" scoped>
.processing-floater {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 420px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 255, 255, 0.95) 100%);
  border-radius: 16px;
  box-shadow: 
    0 12px 48px rgba(0, 0, 0, 0.12),
    0 4px 16px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(194, 164, 116, 0.2);
  backdrop-filter: blur(20px);
  z-index: 2000;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &.minimized {
    .floater-content {
      display: none;
    }
  }

  &:hover {
    box-shadow: 
      0 16px 56px rgba(0, 0, 0, 0.15),
      0 6px 20px rgba(0, 0, 0, 0.1);
  }

  .floater-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(194, 164, 116, 0.15);
    background: linear-gradient(135deg, rgba(194, 164, 116, 0.08) 0%, rgba(155, 135, 245, 0.05) 100%);

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .header-icon {
        color: #c2a474;
      }

      .header-title {
        font-size: 14px;
        font-weight: 600;
        color: #1e293b;
        display: flex;
        align-items: center;
      }
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 4px;

      :deep(.n-button) {
        color: #64748b;

        &:hover {
          color: #1e293b;
          background: rgba(0, 0, 0, 0.05);
        }
      }
    }
  }

  .floater-content {
    overflow: hidden;
    animation: expand 0.3s ease-out;

    .task-list {
      padding: 12px;

      .task-item {
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(194, 164, 116, 0.15);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

        &:last-child {
          margin-bottom: 0;
        }

        &:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
          transform: translateY(-2px);
        }

        &.processing {
          border-color: rgba(194, 164, 116, 0.3);
          background: linear-gradient(135deg, rgba(194, 164, 116, 0.05) 0%, rgba(155, 135, 245, 0.05) 100%);
        }

        &.completed {
          border-color: rgba(24, 160, 88, 0.2);
          background: rgba(24, 160, 88, 0.05);
        }

        &.failed {
          border-color: rgba(208, 48, 80, 0.2);
          background: rgba(208, 48, 80, 0.05);
        }

        .task-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;

          .task-info {
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
            min-width: 0;

            .task-icon {
              flex-shrink: 0;

              &.processing {
                color: #c2a474;
              }

              &.completed {
                color: #18a058;
              }

              &.failed {
                color: #d03050;
              }
            }

            .task-filename {
              font-size: 13px;
              font-weight: 600;
              color: #1e293b;
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }
          }
        }

        .task-progress {
          .progress-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;

            .progress-message {
              font-size: 12px;
              color: #64748b;
              font-weight: 500;
            }

            .progress-percent {
              font-size: 12px;
              font-weight: 700;
              color: #c2a474;
            }
          }
        }

        .task-status {
          .status-message {
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
          }
        }

        .task-stats {
          display: flex;
          gap: 6px;
          margin-top: 8px;

          .stat-chip {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 6px;
            border: 1px solid rgba(194, 164, 116, 0.2);

            .stat-label {
              font-size: 11px;
              color: #64748b;
              font-weight: 500;
            }

            .stat-value {
              font-size: 12px;
              font-weight: 700;
              color: #c2a474;
            }
          }
        }
      }
    }
  }

  .floater-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid rgba(194, 164, 116, 0.15);
    background: rgba(248, 250, 252, 0.5);

    :deep(.n-button) {
      font-size: 12px;
    }
  }
}

// Animations
.floater-slide-enter-active,
.floater-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.floater-slide-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.floater-slide-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.task-slide-enter-active,
.task-slide-leave-active {
  transition: all 0.3s ease;
}

.task-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.task-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

@keyframes expand {
  from {
    max-height: 0;
    opacity: 0;
  }
  to {
    max-height: 500px;
    opacity: 1;
  }
}

// Responsive
@media (max-width: 768px) {
  .processing-floater {
    width: calc(100vw - 48px);
    right: 24px;
    left: 24px;
  }
}
</style>

