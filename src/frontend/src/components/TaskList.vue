<template>
  <div class="task-list">
    <Card>
      <template #title>
        <div class="title-section">
          <i class="pi pi-list"></i>
          処理タスク一覧
          <Badge v-if="tasks.length > 0" :value="tasks.length" class="ml-2" />
          <Button
            icon="pi pi-refresh"
            class="p-button-text p-button-sm refresh-btn"
            v-tooltip="'タスク一覧を手動更新'"
            @click="refreshTasks"
            :loading="loading"
          />
        </div>
      </template>

      <template #content>
        <!-- Task Stats -->
        <div v-if="tasks.length > 0" class="task-stats">
          <div class="stat-item">
            <Badge value="処理中" severity="info" />
            <span class="stat-count">{{ taskStats.processing }}</span>
          </div>
          <div class="stat-item">
            <Badge value="完了" severity="success" />
            <span class="stat-count">{{ taskStats.completed }}</span>
          </div>
          <div class="stat-item">
            <Badge value="エラー" severity="danger" />
            <span class="stat-count">{{ taskStats.failed }}</span>
          </div>
        </div>

        <!-- Loading State - 初期化されていない場合のみ表示 -->
        <div v-if="loading && !initialized" class="loading-state">
          <ProgressSpinner
            strokeWidth="4"
            fill="transparent"
            animationDuration="1s"
          />
          <p>タスクを読み込み中...</p>
        </div>

        <!-- Empty State - 初期化済みでタスクが空の場合 -->
        <div v-else-if="initialized && tasks.length === 0 && !loading" class="empty-state">
          <i class="pi pi-inbox empty-icon"></i>
          <h3>タスクがありません</h3>
          <p>動画ファイルをアップロードして議事録生成を開始してください</p>
        </div>

        <!-- Loading overlay for manual refresh - 手動更新時のみ表示 -->
        <div v-else-if="loading && initialized && tasks.length === 0" class="refresh-loading">
          <ProgressSpinner
            strokeWidth="3"
            fill="transparent"
            animationDuration="1s"
            style="width: 24px; height: 24px;"
          />
          <p style="font-size: 0.9rem; margin-top: 0.5rem;">更新中...</p>
        </div>

        <!-- Task Table -->
        <DataTable
          v-else-if="initialized && tasks.length > 0"
          :value="tasks"
          :paginator="true"
          :rows="10"
          :sortField="'upload_timestamp'"
          :sortOrder="-1"
          responsiveLayout="scroll"
          class="task-table"
          :rowHover="true"
        >
          <Column
            field="video_filename"
            header="ファイル名"
            sortable
            class="filename-column"
          >
            <template #body="{ data }">
              <div class="filename-cell">
                <i class="pi pi-file-video file-icon"></i>
                <div class="filename-info">
                  <span class="filename">{{ data.video_filename }}</span>
                  <span class="filesize">{{
                    formatFileSize(data.video_size)
                  }}</span>
                </div>
              </div>
            </template>
          </Column>

          <Column
            field="status"
            header="ステータス"
            sortable
            class="status-column"
          >
            <template #body="{ data }">
              <div class="status-cell">
                <Badge
                  :value="getStatusLabel(data.status)"
                  :severity="getStatusSeverity(data.status)"
                />
                <div
                  v-if="data.status === 'processing' && data.current_step"
                  class="current-step"
                >
                  {{ getStepLabel(data.current_step) }}
                </div>
              </div>
            </template>
          </Column>

          <Column
            field="overall_progress"
            header="進捗"
            class="progress-column"
          >
            <template #body="{ data }">
              <div class="progress-cell">
                <div class="progress-header">
                  <span class="progress-label">進捗</span>
                  <span class="progress-value"
                    >{{ data.overall_progress || 0 }}%</span
                  >
                </div>
                <ProgressBar
                  :value="data.overall_progress || 0"
                  :showValue="false"
                  class="task-progress"
                />
                <small
                  v-if="data.status === 'processing' && data.estimated_time"
                  class="eta"
                >
                  残り約{{ data.estimated_time }}分
                </small>
              </div>
            </template>
          </Column>

          <Column
            field="upload_timestamp"
            header="アップロード日時"
            sortable
            class="timestamp-column"
          >
            <template #body="{ data }">
              <div class="timestamp-cell">
                <span class="date">{{
                  formatDate(data.upload_timestamp)
                }}</span>
                <span class="time">{{
                  formatTime(data.upload_timestamp)
                }}</span>
              </div>
            </template>
          </Column>

          <Column header="アクション" class="actions-column">
            <template #body="{ data }">
              <div class="action-buttons">
                <!-- View Details -->
                <Button
                  icon="pi pi-eye"
                  class="p-button-text p-button-info p-button-sm action-btn"
                  v-tooltip="{
                    value: 'タスクの詳細情報を表示します',
                    showDelay: 300,
                    hideDelay: 100
                  }"
                  @click="viewDetails(data)"
                />

                <!-- View Minutes (completed only) -->
                <Button
                  v-if="data.status === 'completed'"
                  icon="pi pi-file"
                  class="p-button-text p-button-success p-button-sm action-btn"
                  v-tooltip="{
                    value: '生成された議事録を閲覧します',
                    showDelay: 300,
                    hideDelay: 100
                  }"
                  @click="viewMinutes(data)"
                />

                <!-- Retry (failed only) -->
                <Button
                  v-if="data.status === 'failed'"
                  icon="pi pi-refresh"
                  class="p-button-text p-button-warning p-button-sm action-btn"
                  v-tooltip="{
                    value: 'エラーが発生したタスクを再実行します',
                    showDelay: 300,
                    hideDelay: 100
                  }"
                  @click="retryTask(data)"
                  :loading="retryingTasks.has(data.task_id)"
                />

                <!-- Delete -->
                <Button
                  icon="pi pi-trash"
                  class="p-button-text p-button-danger p-button-sm action-btn"
                  v-tooltip="{
                    value: 'タスクを完全に削除します（復元不可）',
                    showDelay: 300,
                    hideDelay: 100
                  }"
                  @click="deleteTask(data)"
                  :disabled="data.status === 'processing'"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Task Detail Modal -->
    <TaskDetailModal
      v-model:visible="showDetailModal"
      :task="selectedTask"
      @retry="retryTask"
      @delete="deleteTask"
      @view-minutes="viewMinutes"
    />

    <!-- Delete Confirmation Dialog -->
    <ConfirmDialog />
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useTasksStore } from '@/stores/tasks'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import TaskDetailModal from './TaskDetailModal.vue'

export default {
  name: 'TaskList',
  components: {
    Card,
    DataTable,
    Column,
    Button,
    Badge,
    ProgressBar,
    ProgressSpinner,
    ConfirmDialog,
    TaskDetailModal
  },
  setup() {
    const router = useRouter()
    const toast = useToast()
    const confirm = useConfirm()
    const tasksStore = useTasksStore()

    const showDetailModal = ref(false)
    const selectedTask = ref(null)
    const retryingTasks = ref(new Set())

    const tasks = computed(() => tasksStore.tasks)
    const loading = computed(() => tasksStore.loading)
    const initialized = computed(() => tasksStore.initialized)
    const taskStats = computed(() => tasksStore.taskStats)

    const viewDetails = task => {
      selectedTask.value = task
      showDetailModal.value = true
    }

    const viewMinutes = task => {
      router.push({ name: 'minutes', params: { taskId: task.task_id } })
    }

    const retryTask = async task => {
      retryingTasks.value.add(task.task_id)
      try {
        await tasksStore.retryTask(task.task_id)
        toast.add({
          severity: 'success',
          summary: '再実行開始',
          detail: `${task.video_filename} の処理を再開始しました`,
          life: 3000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: '再実行エラー',
          detail: error.message,
          life: 5000
        })
      } finally {
        retryingTasks.value.delete(task.task_id)
      }
    }

    const deleteTask = task => {
      confirm.require({
        message: `「${task.video_filename}」を削除しますか？\nこの操作は取り消せません。`,
        header: 'タスク削除の確認',
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: '削除',
        rejectLabel: 'キャンセル',
        acceptClass: 'p-button-danger',
        accept: async () => {
          try {
            await tasksStore.deleteTask(task.task_id)
            toast.add({
              severity: 'success',
              summary: '削除完了',
              detail: `${task.video_filename} を削除しました`,
              life: 3000
            })
          } catch (error) {
            toast.add({
              severity: 'error',
              summary: '削除エラー',
              detail: error.message,
              life: 5000
            })
          }
        }
      })
    }

    const refreshTasks = async () => {
      try {
        await tasksStore.forceRefresh()
        toast.add({
          severity: 'info',
          summary: '更新完了',
          detail: 'タスク一覧を更新しました',
          life: 2000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: '更新エラー',
          detail: 'タスク一覧の更新に失敗しました',
          life: 3000
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
        upload: 'アップロード中',
        audio_extraction: '音声抽出中',
        transcription: '文字起こし中',
        minutes_generation: '議事録生成中'
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
      return date.toLocaleDateString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      })
    }

    const formatTime = timestamp => {
      if (!timestamp) return ''
      // UTC文字列をローカルタイムゾーンに変換
      const date = new Date(timestamp)
      return date.toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      })
    }

    // Lifecycle
    onMounted(async () => {
      // 初期化されていない場合のみ初回読み込みを実行
      if (!tasksStore.initialized) {
        await tasksStore.fetchTasks(false) // 初回はローディング表示せずに即座に実行
      }
    })

    onUnmounted(() => {
      // Don't stop polling here since DashboardView manages it
    })

    return {
      tasks,
      loading,
      initialized,
      taskStats,
      showDetailModal,
      selectedTask,
      retryingTasks,
      viewDetails,
      viewMinutes,
      retryTask,
      deleteTask,
      refreshTasks,
      getStatusLabel,
      getStatusSeverity,
      getStepLabel,
      formatFileSize,
      formatDate,
      formatTime
    }
  }
}
</script>

<style scoped>
.title-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  color: var(--gray-550);
}

.refresh-btn {
  margin-left: auto;
  color: var(--primary-600) !important;
}

.refresh-btn:hover {
  color: var(--primary-700) !important;
  background: rgba(99, 102, 241, 0.1) !important;
}

.task-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 0;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--gray-50);
  border-radius: var(--radius-md);
  border: 1px solid var(--gray-200);
  font-size: 0.9rem;
  font-weight: 500;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
}

.refresh-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem;
  color: var(--gray-650);
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--gray-650);
}

.empty-icon {
  font-size: 4rem;
  color: #dee2e6;
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0 0 0.5rem 0;
  color: var(--gray-550);
}

.task-table {
  margin-top: 1rem;
}

.filename-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.file-icon {
  font-size: 1.5rem;
  color: var(--primary-500);
  flex-shrink: 0;
}

.filename-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.filename {
  font-weight: 500;
  color: var(--gray-550);
  word-break: break-all;
}

.filesize {
  font-size: 0.85rem;
  color: var(--gray-700);
  font-weight: 500;
}

.status-cell {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: flex-start;
}

.current-step {
  font-size: 0.8rem;
  color: var(--gray-800);
  font-weight: 600;
  line-height: 1.2;
  margin-top: 0.25rem;
}

/* 完了ステータスの色修正 */
:deep(.p-badge.p-badge-success) {
  background-color: var(--success-500) !important;
  color: #ffffff !important;
}

:deep(.status-cell .p-badge) {
  font-size: 0.75rem;
  padding: 0.4rem 0.8rem;
  font-weight: 600;
  white-space: nowrap;
  min-width: 60px;
  text-align: center;
}

.progress-cell {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-1);
}

.progress-label {
  font-size: 0.8rem;
  color: var(--gray-600);
  font-weight: 500;
}

.progress-value {
  font-size: 0.85rem;
  color: var(--primary-600);
  font-weight: 700;
  min-width: 35px;
  text-align: right;
}

.task-progress {
  width: 100%;
  height: 10px;
  border-radius: var(--radius-md);
}

:deep(.task-progress .p-progressbar-value) {
  border-radius: 4px;
}

:deep(.task-progress .p-progressbar) {
  border-radius: 4px;
  background: var(--gray-200);
}

.eta {
  color: var(--gray-800);
  font-size: 0.8rem;
  font-weight: 600;
}

.timestamp-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.date {
  font-weight: 500;
  color: var(--gray-550);
}

.time {
  font-size: 0.85rem;
  color: var(--gray-700);
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

:deep(.action-buttons .p-button.action-btn) {
  padding: 0.5rem;
  font-size: 0.9rem;
  border-radius: var(--radius-md);
  min-width: 36px;
  height: 36px;
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
}

:deep(.action-buttons .p-button.action-btn::before) {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.2),
    transparent
  );
  transition: left 0.5s ease;
}

:deep(.action-buttons .p-button.action-btn:hover::before) {
  left: 100%;
}

:deep(.action-buttons .p-button.action-btn:hover) {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

:deep(.action-buttons .p-button.action-btn .p-button-icon) {
  font-size: 1rem;
  transition: all var(--transition-fast);
}

:deep(.action-buttons .p-button.action-btn:hover .p-button-icon) {
  transform: scale(1.1);
}

/* Specific action button colors */
:deep(.action-buttons .p-button-info.action-btn) {
  color: var(--primary-600);
  background: rgba(99, 102, 241, 0.1);
}

:deep(.action-buttons .p-button-info.action-btn:hover) {
  background: rgba(99, 102, 241, 0.2);
  color: var(--primary-700);
}

:deep(.action-buttons .p-button-success.action-btn) {
  color: var(--success-600);
  background: rgba(16, 185, 129, 0.1);
}

:deep(.action-buttons .p-button-success.action-btn:hover) {
  background: rgba(16, 185, 129, 0.2);
  color: var(--success-700);
}

:deep(.action-buttons .p-button-warning.action-btn) {
  color: var(--warning-600);
  background: rgba(245, 158, 11, 0.1);
}

:deep(.action-buttons .p-button-warning.action-btn:hover) {
  background: rgba(245, 158, 11, 0.2);
  color: var(--warning-700);
}

:deep(.action-buttons .p-button-danger.action-btn) {
  color: var(--error-600);
  background: rgba(239, 68, 68, 0.1);
}

:deep(.action-buttons .p-button-danger.action-btn:hover) {
  background: rgba(239, 68, 68, 0.2);
  color: var(--error-700);
}

:deep(.action-buttons .p-button-danger.action-btn:disabled) {
  opacity: 0.4;
  transform: none;
  box-shadow: none;
}

/* DataTable Styling */
:deep(.task-table .p-datatable-thead > tr > th) {
  padding: 1rem 0.75rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--gray-700);
  background: var(--gray-600-light);
  border-bottom: 2px solid var(--gray-200);
}

:deep(.task-table .p-datatable-tbody > tr > td) {
  padding: 1rem 0.75rem;
  vertical-align: top;
  border-bottom: 1px solid var(--gray-200);
}

:deep(.task-table .p-datatable-tbody > tr:hover) {
  background: var(--gray-600-light);
}

/* Column widths */
:deep(.task-table .filename-column) {
  min-width: 250px;
  width: 35%;
}

:deep(.task-table .status-column) {
  min-width: 140px;
  width: 15%;
}

:deep(.task-table .progress-column) {
  min-width: 120px;
  width: 15%;
}

:deep(.task-table .timestamp-column) {
  min-width: 130px;
  width: 15%;
}

:deep(.task-table .actions-column) {
  min-width: 140px;
  width: 20%;
  text-align: center;
}

@media (max-width: 1024px) {
  .filename-column {
    min-width: 200px;
  }

  .status-column,
  .progress-column {
    min-width: 120px;
  }

  .timestamp-column {
    min-width: 100px;
  }

  .actions-column {
    min-width: 120px;
  }
}

@media (max-width: 768px) {
  .task-stats {
    flex-direction: column;
    gap: 0.5rem;
  }

  .stat-item {
    justify-content: space-between;
  }

  :deep(.task-table) {
    font-size: 0.9rem;
  }

  .action-buttons {
    flex-direction: column;
    gap: 0.25rem;
  }
}

/* TaskListカードの統一余白設定 */
.task-list :deep(.p-card) {
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--gray-200);
  background: white;
  transition: all var(--transition-normal);
}

.task-list :deep(.p-card-title) {
  padding: 20px 24px 0 24px;
  margin: 0 0 16px 0;
  color: var(--gray-900);
  font-weight: 600;
  font-size: 1.2rem;
}

.task-list :deep(.p-card-content) {
  padding: 0 24px 24px 24px;
  color: var(--gray-700);
}
</style>
