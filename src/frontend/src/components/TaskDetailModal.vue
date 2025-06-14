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
            <span class="progress-percentage">{{ task.progress || 0 }}%</span>
          </div>
          <ProgressBar 
            :value="task.progress || 0" 
            class="overall-progress-bar"
          />
        </div>

        <!-- Step Timeline -->
        <Timeline 
          :value="processSteps" 
          layout="vertical" 
          class="step-timeline"
        >
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
                <ProgressBar :value="item.progress" :showValue="true" />
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
      <div v-if="task.status === 'failed' && task.error_message" class="error-section">
        <h3>エラー詳細</h3>
        <Message 
          severity="error" 
          :closable="false"
          class="error-message"
        >
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
          icon="pi pi-file-text"
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
      set: (value) => emit('update:visible', value)
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
          icon: 'pi-file-text'
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

    const getStatusLabel = (status) => {
      const labels = {
        'pending': '待機中',
        'processing': '処理中',
        'completed': '完了',
        'failed': 'エラー'
      }
      return labels[status] || status
    }

    const getStatusSeverity = (status) => {
      const severities = {
        'pending': 'info',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger'
      }
      return severities[status] || 'info'
    }

    const getStepLabel = (step) => {
      const labels = {
        'upload': 'アップロード中',
        'audio_extraction': '音声抽出中',
        'transcription': '文字起こし中',
        'minutes_generation': '議事録生成中'
      }
      return labels[step] || step
    }

    const getStepStatusLabel = (status) => {
      const labels = {
        'pending': '待機',
        'processing': '処理中',
        'completed': '完了',
        'failed': 'エラー'
      }
      return labels[status] || status
    }

    const getStepStatusSeverity = (status) => {
      const severities = {
        'pending': null,
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger'
      }
      return severities[status]
    }

    const getStepMarkerClass = (step) => {
      return {
        'step-pending': step.status === 'pending',
        'step-processing': step.status === 'processing',
        'step-completed': step.status === 'completed',
        'step-failed': step.status === 'failed'
      }
    }

    const getStepIcon = (step) => {
      return `pi ${step.icon}`
    }

    const formatFileSize = (bytes) => {
      if (!bytes) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const formatDateTime = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const calculateTotalDuration = (task) => {
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
  gap: 2rem;
}

.task-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  padding: 2rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #f1f3f4 100%);
  border-radius: 12px;
  border: 1px solid #e9ecef;
}

.overview-item {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.overview-item label {
  font-weight: 600;
  color: #495057;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.overview-item span {
  font-size: 0.95rem;
  color: #212529;
  font-weight: 500;
}

/* Badge improvements in modal */
:deep(.overview-item .p-badge) {
  font-size: 0.8rem;
  padding: 0.5rem 1rem;
  font-weight: 600;
  align-self: flex-start;
}

.filename {
  font-weight: 500;
  color: #495057;
  word-break: break-all;
}

.progress-section h3 {
  margin: 0 0 1.5rem 0;
  color: #374151;
  font-size: 1.2rem;
  font-weight: 600;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 0.5rem;
}

.overall-progress {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #f1f3f4 100%);
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
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
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
  color: #495057;
  font-size: 1rem;
}

.step-progress {
  margin: 0.5rem 0;
}

.eta {
  display: block;
  margin-top: 0.25rem;
  color: #6c757d;
}

.step-duration {
  font-size: 0.9rem;
  color: #6c757d;
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
  color: #495057;
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
  background: #f8f9fa;
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