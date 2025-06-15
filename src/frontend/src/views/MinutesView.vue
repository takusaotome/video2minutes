<template>
  <div class="minutes-view">
    <!-- Navigation Header -->
    <div class="nav-header">
      <Button
        icon="pi pi-arrow-left"
        label="ダッシュボードに戻る"
        class="p-button-text back-button"
        @click="goBack"
      />

      <div class="breadcrumb">
        <span class="breadcrumb-item">ダッシュボード</span>
        <i class="pi pi-angle-right breadcrumb-separator"></i>
        <span class="breadcrumb-item current">議事録</span>
      </div>
    </div>

    <!-- Task Info Banner -->
    <div v-if="task" class="task-banner">
      <Card class="task-info-card">
        <template #content>
          <div class="task-info">
            <div class="task-details">
              <div class="task-file">
                <i class="pi pi-file-video file-icon"></i>
                <div class="file-details">
                  <h3 class="file-name">{{ task.video_filename }}</h3>
                  <div class="file-meta">
                    <span class="file-size">{{
                      formatFileSize(task.video_size)
                    }}</span>
                    <span class="separator">•</span>
                    <span class="process-date">{{
                      formatDate(task.upload_timestamp)
                    }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="task-status">
              <Badge
                :value="getStatusLabel(task.status)"
                :severity="getStatusSeverity(task.status)"
                class="status-badge"
              />
              <div v-if="task.processing_duration" class="process-time">
                処理時間: {{ task.processing_duration }}
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Loading State -->
    <div v-if="loadingTask" class="loading-state">
      <ProgressSpinner />
      <p>タスク情報を読み込み中...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="taskError" class="error-state">
      <Message severity="error" :closable="false">
        <div class="error-content">
          <i class="pi pi-exclamation-triangle"></i>
          <div>
            <strong>タスクの読み込みに失敗しました</strong>
            <p>{{ taskError }}</p>
          </div>
        </div>
      </Message>
      <div class="error-actions">
        <Button
          label="再読み込み"
          icon="pi pi-refresh"
          @click="loadTask"
          class="p-button-outlined"
        />
        <Button
          label="ダッシュボードに戻る"
          icon="pi pi-arrow-left"
          @click="goBack"
          class="p-button-secondary"
        />
      </div>
    </div>

    <!-- Task Not Completed -->
    <div
      v-else-if="task && task.status !== 'completed'"
      class="not-ready-state"
    >
      <Card>
        <template #content>
          <div class="not-ready-content">
            <div class="not-ready-icon">
              <i
                v-if="task.status === 'processing'"
                class="pi pi-cog spinning"
              ></i>
              <i
                v-else-if="task.status === 'failed'"
                class="pi pi-exclamation-triangle"
              ></i>
              <i v-else class="pi pi-clock"></i>
            </div>

            <div class="not-ready-message">
              <h3 v-if="task.status === 'processing'">議事録を生成中です</h3>
              <h3 v-else-if="task.status === 'failed'">
                処理でエラーが発生しました
              </h3>
              <h3 v-else>議事録の生成を待機中です</h3>

              <p v-if="task.status === 'processing'">
                現在{{ getStepLabel(task.current_step) }}を実行中です。<br />
                処理完了まで今しばらくお待ちください。
              </p>
              <p v-else-if="task.status === 'failed'">
                {{ task.error_message || '処理中にエラーが発生しました。' }}
              </p>
              <p v-else>処理の開始を待機しています。</p>
            </div>

            <div class="not-ready-actions">
              <Button
                v-if="task.status === 'processing'"
                label="処理状況を確認"
                icon="pi pi-eye"
                @click="showTaskDetail"
                class="p-button-outlined"
              />
              <Button
                v-if="task.status === 'failed'"
                label="再実行"
                icon="pi pi-refresh"
                @click="retryTask"
                :loading="retrying"
                class="p-button-warning"
              />
              <Button
                label="ダッシュボードに戻る"
                icon="pi pi-arrow-left"
                @click="goBack"
                class="p-button-secondary"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Minutes Content -->
    <MinutesViewer
      v-else-if="task && task.status === 'completed'"
      :task-id="taskId"
    />

    <!-- Task Detail Modal -->
    <TaskDetailModal
      v-model:visible="showDetailModal"
      :task="task"
      @retry="retryTask"
      @delete="deleteTask"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useTasksStore } from '@/stores/tasks'
import MinutesViewer from '@/components/MinutesViewer.vue'
import TaskDetailModal from '@/components/TaskDetailModal.vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'

export default {
  name: 'MinutesView',
  components: {
    MinutesViewer,
    TaskDetailModal,
    Card,
    Button,
    Badge,
    Message,
    ProgressSpinner
  },
  props: {
    taskId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const route = useRoute()
    const router = useRouter()
    const toast = useToast()
    const tasksStore = useTasksStore()

    const task = ref(null)
    const loadingTask = ref(false)
    const taskError = ref(null)
    const showDetailModal = ref(false)
    const retrying = ref(false)

    const loadTask = async () => {
      loadingTask.value = true
      taskError.value = null

      try {
        // First check if task exists in store
        let taskData = tasksStore.getTaskById(props.taskId)

        if (!taskData) {
          // If not in store, fetch from API
          await tasksStore.fetchTasks()
          taskData = tasksStore.getTaskById(props.taskId)
        }

        if (!taskData) {
          // If still not found, fetch specific task status
          taskData = await tasksStore.fetchTaskStatus(props.taskId)
        }

        if (!taskData) {
          throw new Error('指定されたタスクが見つかりません')
        }

        task.value = taskData

        // If task is processing, start real-time updates
        if (taskData.status === 'processing') {
          tasksStore.connectToTask(props.taskId)
        }
      } catch (error) {
        taskError.value = error.message
        console.error('Failed to load task:', error)
      } finally {
        loadingTask.value = false
      }
    }

    const goBack = () => {
      router.push({ name: 'dashboard' })
    }

    const showTaskDetail = () => {
      showDetailModal.value = true
    }

    const retryTask = async () => {
      if (!task.value) return

      retrying.value = true
      try {
        await tasksStore.retryTask(props.taskId)

        toast.add({
          severity: 'success',
          summary: '再実行開始',
          detail: '処理を再開始しました',
          life: 3000
        })

        // Reload task data
        await loadTask()
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: '再実行エラー',
          detail: error.message,
          life: 5000
        })
      } finally {
        retrying.value = false
      }
    }

    const deleteTask = async () => {
      if (!task.value) return

      try {
        await tasksStore.deleteTask(props.taskId)

        toast.add({
          severity: 'success',
          summary: '削除完了',
          detail: 'タスクを削除しました',
          life: 3000
        })

        // Navigate back to dashboard
        goBack()
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: '削除エラー',
          detail: error.message,
          life: 5000
        })
      }
    }

    const getStatusLabel = status => {
      const labels = {
        pending: '待機中',
        processing: '処理中',
        completed: '完了',
        failed: 'エラー'
      }
      return labels[status] || status
    }

    const getStatusSeverity = status => {
      const severities = {
        pending: 'info',
        processing: 'warning',
        completed: 'success',
        failed: 'danger'
      }
      return severities[status] || 'info'
    }

    const getStepLabel = step => {
      const labels = {
        upload: 'アップロード',
        audio_extraction: '音声抽出',
        transcription: '文字起こし',
        minutes_generation: '議事録生成'
      }
      return labels[step] || step
    }

    const formatFileSize = bytes => {
      if (!bytes) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const formatDate = timestamp => {
      if (!timestamp) return ''
      // UTC文字列をローカルタイムゾーンに変換
      const date = new Date(timestamp)
      return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      })
    }

    // Watch for task updates in the store
    watch(
      () => tasksStore.getTaskById(props.taskId),
      newTask => {
        if (newTask) {
          task.value = newTask
        }
      },
      { deep: true }
    )

    // Load task on mount
    onMounted(() => {
      loadTask()
    })

    return {
      task,
      loadingTask,
      taskError,
      showDetailModal,
      retrying,
      loadTask,
      goBack,
      showTaskDetail,
      retryTask,
      deleteTask,
      getStatusLabel,
      getStatusSeverity,
      getStepLabel,
      formatFileSize,
      formatDate
    }
  }
}
</script>

<style scoped>
.minutes-view {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  animation: fadeIn 0.6s ease-out;
}

.nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-6) calc(var(--space-6) - 8px) var(--space-6) var(--space-6);
  margin: 0 24px var(--space-6) 24px;
  border-bottom: 2px solid var(--gray-200);
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.back-button {
  font-size: 1rem;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.back-button:hover {
  transform: translateX(-2px);
  color: var(--primary-600);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.95rem;
  color: var(--gray-700);
  font-weight: 500;
}

.breadcrumb-item.current {
  color: var(--gray-800);
  font-weight: 600;
}

.breadcrumb-separator {
  font-size: 0.85rem;
  color: var(--gray-600);
}

.task-banner {
  margin: 0 24px var(--space-6) 24px;
  animation: slideUp 0.6s ease-out 0.1s both;
}

.task-info-card {
  border: 1px solid var(--gray-200);
  box-shadow: var(--shadow-lg);
  background: white;
}

.task-info-card :deep(.p-card-content) {
  padding-right: calc(var(--space-6) - 8px);
}

.task-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-8);
  padding: 0 8px 0 0;
}

.task-file {
  display: flex;
  align-items: center;
  gap: var(--space-5);
}

.file-icon {
  font-size: 3rem;
  color: var(--primary-500);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.file-name {
  margin: 0 0 var(--space-2) 0;
  color: var(--gray-800);
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.3;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--gray-800);
  font-size: 1rem;
  font-weight: 500;
}

.separator {
  color: var(--gray-300);
  font-weight: bold;
}

.task-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-3);
}

/* Badge styling improvements - 日本語対応 */
:deep(.p-badge) {
  /* 日本語テキストのはみ出し修正 */
  line-height: 1.2 !important;
  height: auto !important;
  min-height: 1.5rem;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0.4rem 0.8rem !important;
}

/* 完了ステータスの色修正 */
:deep(.p-badge.p-badge-success) {
  background-color: #10b981 !important;
  color: #ffffff !important;
}

.status-badge {
  font-size: 1.1rem;
  padding: var(--space-3) var(--space-5);
  font-weight: 600;
  border-radius: var(--radius-md);
}

.process-time {
  font-size: 0.9rem;
  color: var(--gray-800);
  font-weight: 500;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-5);
  padding: var(--space-12);
  text-align: center;
  background: white;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--gray-200);
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  text-align: left;
}

.error-content i {
  font-size: 1.75rem;
  color: var(--error-500);
  margin-top: var(--space-1);
}

.error-actions {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-5);
  flex-wrap: wrap;
  justify-content: center;
}

.not-ready-state {
  margin-top: var(--space-8);
  animation: slideUp 0.6s ease-out 0.2s both;
}

.not-ready-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-8);
  padding: var(--space-12);
  text-align: center;
}

.not-ready-icon {
  font-size: 5rem;
  color: var(--gray-500);
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
}

.not-ready-icon .spinning {
  animation: spin 2s linear infinite;
  color: var(--primary-500);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.not-ready-message h3 {
  margin: 0 0 var(--space-4) 0;
  color: var(--gray-800);
  font-size: 1.75rem;
  font-weight: 700;
}

.not-ready-message p {
  margin: 0;
  color: var(--gray-700);
  line-height: 1.7;
  max-width: 600px;
  font-size: 1.1rem;
}

.not-ready-actions {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
  justify-content: center;
}

/* Responsive Design */
@media (max-width: 768px) {
  .nav-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
    margin: 0 16px var(--space-6) 16px;
  }

  .task-banner {
    margin: 0 16px var(--space-6) 16px;
  }

  .task-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .task-status {
    align-items: flex-start;
    width: 100%;
  }

  .file-name {
    font-size: 1.1rem;
  }

  .file-meta {
    flex-wrap: wrap;
  }

  .not-ready-content {
    padding: 2rem 1rem;
  }

  .not-ready-message h3 {
    font-size: 1.25rem;
  }

  .not-ready-actions {
    flex-direction: column;
    width: 100%;
  }

  .error-actions {
    flex-direction: column;
    width: 100%;
  }
}

@media (max-width: 480px) {
  .minutes-view {
    gap: 1rem;
  }

  .task-file {
    flex-direction: column;
    text-align: center;
    gap: 0.75rem;
  }

  .file-icon {
    font-size: 2rem;
  }

  .not-ready-icon {
    font-size: 3rem;
  }
}
</style>
