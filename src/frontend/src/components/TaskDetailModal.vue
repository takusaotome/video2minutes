<template>
  <Dialog
    v-model:visible="isVisible"
    :header="task ? `タスク詳細: ${task.video_filename}` : 'タスク詳細'"
    :modal="true"
    :closable="true"
    :draggable="false"
    class="task-detail-modal"
    :style="{ width: '90vw', maxWidth: '800px' }"
  >
    <div v-if="task" class="task-detail-content">
      <!-- Task Overview -->
      <div class="task-overview">
        <div class="overview-item">
          <label>ファイル名:</label>
          <span class="filename">{{ task.video_filename }}</span>
        </div>
        <div class="overview-item">
          <label>ファイルサイズ:</label>
          <span>{{ formatFileSize(task.video_size) }}</span>
        </div>
        <div class="overview-item">
          <label>アップロード日時:</label>
          <span>{{ formatDateTime(task.upload_timestamp) }}</span>
        </div>
        <div class="overview-item">
          <label>現在のステータス:</label>
          <Badge
            :value="getStatusLabel(task.status)"
            :severity="getStatusSeverity(task.status)"
          />
        </div>
        <div v-if="task.status === 'processing'" class="overview-item">
          <label>現在の処理:</label>
          <span>{{ getStepLabel(task.current_step) }}</span>
        </div>
      </div>

      <!-- Progress Timeline -->
      <div class="progress-section">
        <h3>処理進捗</h3>

        <!-- Overall Progress -->
        <div class="overall-progress">
          <div class="progress-header">
            <span>全体進捗</span>
            <span class="progress-percentage"
              >{{ task.overall_progress || 0 }}%</span
            >
          </div>
          <ProgressBar
            :value="task.overall_progress || 0"
            :showValue="false"
            class="overall-progress-bar"
          />
        </div>

        <!-- Step Timeline -->
        <Timeline :value="processSteps" layout="vertical" class="step-timeline">
          <template #marker="{ item }">
            <div class="step-marker" :class="getStepMarkerClass(item)">
              <i :class="getStepIcon(item)"></i>
            </div>
          </template>

          <template #content="{ item }">
            <div class="step-content">
              <div class="step-header">
                <h4>{{ item.label }}</h4>
                <Badge
                  :value="getStepStatusLabel(item.status)"
                  :severity="getStepStatusSeverity(item.status)"
                />
              </div>

              <div v-if="item.status === 'processing'" class="step-progress">
                <div class="step-progress-header">
                  <span class="step-progress-label">進捗</span>
                  <span class="step-progress-value"
                    >{{ item.progress || 0 }}%</span
                  >
                </div>
                <ProgressBar :value="item.progress" :showValue="false" />
                <small v-if="item.estimated_time" class="eta">
                  残り約{{ item.estimated_time }}分
                </small>
              </div>

              <div v-if="item.duration" class="step-duration">
                処理時間: {{ item.duration }}
              </div>

              <div v-if="item.error" class="step-error">
                <i class="pi pi-exclamation-triangle"></i>
                {{ item.error }}
              </div>
            </div>
          </template>
        </Timeline>
      </div>

      <!-- Error Details -->
      <div
        v-if="task.status === 'failed' && task.error_message"
        class="error-section"
      >
        <h3>エラー詳細</h3>
        <Message severity="error" :closable="false" class="error-message">
          <div class="error-content">
            <strong>エラーメッセージ:</strong>
            <pre>{{ task.error_message }}</pre>
          </div>
        </Message>
      </div>

      <!-- Results Preview -->
      <div v-if="task.status === 'completed'" class="results-section">
        <h3>処理結果</h3>
        <div class="result-stats">
          <div class="result-item">
            <label>処理時間:</label>
            <span>{{ calculateTotalDuration(task) }}</span>
          </div>
          <div v-if="task.transcription_length" class="result-item">
            <label>文字起こし文字数:</label>
            <span>{{ task.transcription_length.toLocaleString() }}文字</span>
          </div>
          <div v-if="task.minutes_length" class="result-item">
            <label>議事録文字数:</label>
            <span>{{ task.minutes_length.toLocaleString() }}文字</span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="modal-actions">
        <!-- Retry Button (for failed tasks) -->
        <Button
          v-if="task && task.status === 'failed'"
          label="再実行"
          icon="pi pi-refresh"
          class="p-button-warning"
          @click="handleRetry"
          :loading="retrying"
        />

        <!-- View Minutes Button (for completed tasks) -->
        <Button
          v-if="task && task.status === 'completed'"
          label="議事録を見る"
          icon="pi pi-file"
          class="p-button-success"
          @click="handleViewMinutes"
        />

        <!-- Delete Button -->
        <Button
          v-if="task"
          label="削除"
          icon="pi pi-trash"
          class="p-button-danger p-button-outlined"
          @click="handleDelete"
          :disabled="task.status === 'processing'"
        />

        <!-- Close Button -->
        <Button
          label="閉じる"
          icon="pi pi-times"
          class="p-button-secondary"
          @click="close"
        />
      </div>
    </template>
  </Dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Timeline from 'primevue/timeline'
import ProgressBar from 'primevue/progressbar'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { formatDateTime, formatFileSize, formatDuration } from '@/utils/dateUtils.js'

export default {
  name: 'TaskDetailModal',
  components: {
    Dialog,
    Timeline,
    ProgressBar,
    Badge,
    Button,
    Message
  },
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    task: {
      type: Object,
      default: null
    }
  },
  emits: ['update:visible', 'retry', 'delete', 'view-minutes'],
  setup(props, { emit }) {
    const retrying = ref(false)

    const isVisible = computed({
      get: () => props.visible,
      set: value => emit('update:visible', value)
    })

    const processSteps = computed(() => {
      if (!props.task) return []

      const steps = [
        {
          name: 'upload',
          label: 'ファイルアップロード',
          icon: 'pi-cloud-upload'
        },
        {
          name: 'audio_extraction',
          label: '音声抽出',
          icon: 'pi-volume-up'
        },
        {
          name: 'transcription',
          label: '文字起こし',
          icon: 'pi-microphone'
        },
        {
          name: 'minutes_generation',
          label: '議事録生成',
          icon: 'pi-file'
        }
      ]

      // Map steps with actual task data
      return steps.map(step => {
        const stepData = props.task.steps?.find(s => s.name === step.name) || {}
        return {
          ...step,
          status: stepData.status || 'pending',
          progress: stepData.progress || 0,
          started_at: stepData.started_at,
          completed_at: stepData.completed_at,
          duration: stepData.duration,
          error: stepData.error,
          estimated_time: stepData.estimated_time
        }
      })
    })

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

    const getStepStatusLabel = status => {
      const labels = {
        pending: '待機',
        processing: '処理中',
        completed: '完了',
        failed: 'エラー'
      }
      return labels[status] || status
    }

    const getStepStatusSeverity = status => {
      const severities = {
        pending: null,
        processing: 'warning',
        completed: 'success',
        failed: 'danger'
      }
      return severities[status]
    }

    const getStepMarkerClass = step => {
      return {
        'step-pending': step.status === 'pending',
        'step-processing': step.status === 'processing',
        'step-completed': step.status === 'completed',
        'step-failed': step.status === 'failed'
      }
    }

    const getStepIcon = step => {
      return `pi ${step.icon}`
    }

    // 統一された日時フォーマット関数を使用（既にインポート済み）

    const calculateTotalDuration = task => {
      if (!task.processing_started || !task.processing_completed) {
        return '計算中...'
      }

      const start = new Date(task.processing_started)
      const end = new Date(task.processing_completed)
      const durationMs = end - start
      const minutes = Math.floor(durationMs / 60000)
      const seconds = Math.floor((durationMs % 60000) / 1000)

      return `${minutes}分${seconds}秒`
    }

    const close = () => {
      isVisible.value = false
    }

    const handleRetry = async () => {
      if (!props.task) return

      retrying.value = true
      try {
        emit('retry', props.task)
        close()
      } finally {
        retrying.value = false
      }
    }

    const handleDelete = () => {
      if (!props.task) return

      emit('delete', props.task)
      close()
    }

    const handleViewMinutes = () => {
      if (!props.task) return

      emit('view-minutes', props.task)
      close()
    }

    return {
      isVisible,
      retrying,
      processSteps,
      getStatusLabel,
      getStatusSeverity,
      getStepLabel,
      getStepStatusLabel,
      getStepStatusSeverity,
      getStepMarkerClass,
      getStepIcon,
      formatFileSize,
      formatDateTime,
      calculateTotalDuration,
      close,
      handleRetry,
      handleDelete,
      handleViewMinutes
    }
  }
}
</script>

<style scoped>
.task-detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

.task-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-6);
  padding: var(--space-8);
  background: linear-gradient(135deg, white 0%, var(--gray-50) 100%);
  border-radius: var(--radius-xl);
  border: 2px solid var(--gray-200);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-4);
}

.overview-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: white;
  border-radius: var(--radius-lg);
  border: 1px solid var(--gray-100);
  transition: all var(--transition-fast);
}

.overview-item:hover {
  border-color: var(--primary-200);
  box-shadow: var(--shadow-sm);
}

.overview-item label {
  font-weight: 700;
  color: var(--gray-600);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--space-1);
}

.overview-item span {
  font-size: 1rem;
  color: var(--gray-800);
  font-weight: 600;
  line-height: 1.4;
}

/* Badge improvements in modal - 日本語対応 */
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

:deep(.overview-item .p-badge) {
  font-size: 0.8rem;
  padding: 0.5rem 1rem;
  font-weight: 600;
  align-self: flex-start;
}

/* 処理中ステータスの色修正 - 白文字に統一 */
:deep(.p-badge.p-badge-warning) {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
  border-color: #fbbf24 !important;
  color: #ffffff !important;
  box-shadow: 0 2px 4px rgba(245, 158, 11, 0.2) !important;
}

/* 完了ステータスの色修正 */
:deep(.p-badge.p-badge-success) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border-color: #34d399 !important;
  color: #ffffff !important;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2) !important;
}

/* エラーステータスの色修正 */
:deep(.p-badge.p-badge-danger) {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
  border-color: #f87171 !important;
  color: #ffffff !important;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2) !important;
}

/* 情報ステータスの色修正 */
:deep(.p-badge.p-badge-info) {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
  border-color: #60a5fa !important;
  color: #ffffff !important;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2) !important;
}

/* ステップヘッダー内のBadgeも同様に適用 */
:deep(.step-header .p-badge.p-badge-warning) {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
  border-color: #fbbf24 !important;
  color: #ffffff !important;
}

:deep(.step-header .p-badge.p-badge-success) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border-color: #34d399 !important;
  color: #ffffff !important;
}

:deep(.step-header .p-badge.p-badge-danger) {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
  border-color: #f87171 !important;
  color: #ffffff !important;
}

:deep(.step-header .p-badge.p-badge-info) {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
  border-color: #60a5fa !important;
  color: #ffffff !important;
}

.filename {
  font-weight: 500;
  color: var(--gray-550);
  word-break: break-all;
}

.progress-section h3 {
  margin: 0 0 1.5rem 0;
  color: var(--gray-700);
  font-size: 1.2rem;
  font-weight: 600;
  border-bottom: 2px solid var(--gray-200);
  padding-bottom: 0.5rem;
}

.overall-progress {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, var(--gray-600-light) 0%, var(--gray-625-light) 100%);
  border-radius: 12px;
  border: 1px solid #e9ecef;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.progress-percentage {
  font-weight: 600;
  color: #6366f1;
}

.overall-progress-bar {
  height: 12px;
}

.step-timeline {
  margin-top: 1rem;
}

:deep(.step-timeline .p-timeline-event-marker) {
  border: none;
  padding: 0;
}

.step-marker {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: bold;
  border: 3px solid;
  background: white;
}

.step-marker.step-pending {
  border-color: #dee2e6;
  color: #6c757d;
}

.step-marker.step-processing {
  border-color: #ffc107;
  color: #ffc107;
  animation: pulse 2s infinite;
}

.step-marker.step-completed {
  border-color: #28a745;
  color: #28a745;
  background: #d4edda;
}

.step-marker.step-failed {
  border-color: #dc3545;
  color: #dc3545;
  background: #f8d7da;
}

@keyframes pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

.step-content {
  padding-left: 1rem;
  margin-bottom: 1rem;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.step-header h4 {
  margin: 0;
  color: var(--gray-550);
  font-size: 1rem;
}

.step-progress {
  margin: 0.5rem 0;
}

.step-progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.step-progress-label {
  font-size: 0.9rem;
  color: var(--gray-600);
  font-weight: 500;
}

.step-progress-value {
  font-size: 0.9rem;
  color: var(--primary-600);
  font-weight: 600;
}

.eta {
  display: block;
  margin-top: 0.25rem;
  color: var(--gray-650);
}

.step-duration {
  font-size: 0.9rem;
  color: var(--gray-650);
  margin-top: 0.5rem;
}

.step-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #dc3545;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.error-section h3 {
  margin: 0 0 1rem 0;
  color: var(--gray-550);
  font-size: 1.1rem;
}

.error-message {
  margin: 0;
}

.error-content pre {
  margin: 0.5rem 0 0 0;
  white-space: pre-wrap;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.results-section h3 {
  margin: 0 0 1rem 0;
  color: #495057;
  font-size: 1.1rem;
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  padding: 1rem;
  background: var(--gray-600-light);
  border-radius: 8px;
}

.result-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.result-item label {
  font-weight: 600;
  color: #6c757d;
  font-size: 0.9rem;
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  :deep(.task-detail-modal .p-dialog) {
    width: 95vw !important;
    margin: 1rem;
  }

  .task-overview {
    grid-template-columns: 1fr;
  }

  .result-stats {
    grid-template-columns: 1fr;
  }

  .step-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .modal-actions {
    justify-content: center;
  }
}
</style>
