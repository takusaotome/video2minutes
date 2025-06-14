<template>
  <div class="minutes-viewer">
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>議事録を読み込み中...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <Message severity="error" :closable="false">
        <div class="error-content">
          <i class="pi pi-exclamation-triangle"></i>
          <div>
            <strong>議事録の読み込みに失敗しました</strong>
            <p>{{ error }}</p>
          </div>
        </div>
      </Message>
      <Button
        label="再読み込み"
        icon="pi pi-refresh"
        @click="loadMinutes"
        class="retry-button"
      />
    </div>

    <div v-else-if="minutes" class="minutes-content">
      <!-- Header -->
      <div class="minutes-header">
        <div class="header-info">
          <h1 class="minutes-title">
            <i class="pi pi-file"></i>
            議事録
          </h1>
          <div class="file-info">
            <span class="filename">{{ minutes.video_filename }}</span>
            <span class="date">{{ formatDate(minutes.created_at) }}</span>
          </div>
        </div>
        
        <div class="header-actions">
          <Button
            label="コピー"
            icon="pi pi-copy"
            @click="copyToClipboard"
            class="p-button-outlined"
            v-tooltip="'議事録をクリップボードにコピー'"
          />
          <SplitButton
            label="ダウンロード"
            icon="pi pi-download"
            :model="downloadOptions"
            @click="downloadMarkdown"
            class="download-button"
          />
        </div>
      </div>

      <!-- Content Layout -->
      <div class="content-layout">
        <!-- Sidebar Toggle (Mobile) -->
        <Button
          v-if="isMobile"
          :icon="showTranscript ? 'pi pi-times' : 'pi pi-align-left'"
          :label="showTranscript ? '文字起こしを閉じる' : '文字起こしを表示'"
          @click="toggleTranscript"
          class="transcript-toggle p-button-outlined"
        />

        <!-- Transcript Sidebar -->
        <div 
          v-show="!isMobile || showTranscript" 
          class="transcript-sidebar"
          :class="{ 'mobile-overlay': isMobile && showTranscript }"
        >
          <Card class="transcript-card">
            <template #title>
              <div class="transcript-header">
                <i class="pi pi-microphone"></i>
                文字起こし全文
                <Button
                  v-if="isMobile"
                  icon="pi pi-times"
                  class="p-button-text p-button-sm close-transcript"
                  @click="toggleTranscript"
                />
              </div>
            </template>
            
            <template #content>
              <ScrollPanel class="transcript-scroll">
                <div class="transcript-content">
                  <pre class="transcript-text">{{ minutes.transcription }}</pre>
                </div>
              </ScrollPanel>
            </template>
          </Card>
        </div>

        <!-- Minutes Main Content -->
        <div class="minutes-main">
          <Card class="minutes-card">
            <template #title>
              <div class="minutes-card-header">
                <i class="pi pi-file"></i>
                生成された議事録
                <div class="minutes-stats">
                  <small>{{ wordCount }}文字</small>
                </div>
              </div>
            </template>
            
            <template #content>
              <MarkdownRenderer 
                :content="minutes.minutes"
                :show-toc="true"
                @word-count="updateWordCount"
              />
            </template>
          </Card>
        </div>
      </div>
    </div>

    <!-- Copy Success Toast -->
    <Toast />
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useToast } from 'primevue/usetoast'
import { minutesApi } from '@/services/api'
import Card from 'primevue/card'
import Button from 'primevue/button'
import SplitButton from 'primevue/splitbutton'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import ScrollPanel from 'primevue/scrollpanel'
import Toast from 'primevue/toast'
import MarkdownRenderer from './MarkdownRenderer.vue'

export default {
  name: 'MinutesViewer',
  components: {
    Card,
    Button,
    SplitButton,
    Message,
    ProgressSpinner,
    ScrollPanel,
    Toast,
    MarkdownRenderer
  },
  props: {
    taskId: {
      type: String,
      required: true
    }
  },
  emits: ['back'],
  setup(props, { emit }) {
    const toast = useToast()
    
    const minutes = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const showTranscript = ref(false)
    const windowWidth = ref(window.innerWidth)
    const wordCount = ref(0)

    const isMobile = computed(() => windowWidth.value < 768)

    const downloadOptions = ref([
      {
        label: 'Markdown (.md)',
        icon: 'pi pi-file',
        command: () => downloadMarkdown()
      },
      {
        label: 'テキスト (.txt)',
        icon: 'pi pi-file',
        command: () => downloadText()
      },
      {
        label: 'PDF',
        icon: 'pi pi-file-pdf',
        command: () => downloadPDF()
      }
    ])

    const loadMinutes = async () => {
      loading.value = true
      error.value = null
      
      try {
        // Use the API service
        const response = await minutesApi.getTaskResult(props.taskId)
        minutes.value = response.data
      } catch (err) {
        error.value = err.message
        console.error('Failed to load minutes:', err)
      } finally {
        loading.value = false
      }
    }

    const formatDate = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    }


    const copyToClipboard = async () => {
      if (!minutes.value) return
      
      try {
        await navigator.clipboard.writeText(minutes.value.minutes)
        toast.add({
          severity: 'success',
          summary: 'コピー完了',
          detail: '議事録をクリップボードにコピーしました',
          life: 3000
        })
      } catch (err) {
        toast.add({
          severity: 'error',
          summary: 'コピー失敗',
          detail: 'クリップボードへのコピーに失敗しました',
          life: 3000
        })
      }
    }

    const downloadMarkdown = () => {
      if (!minutes.value) return
      
      const content = `# 議事録\n\n**ファイル名:** ${minutes.value.video_filename}\n**作成日時:** ${formatDate(minutes.value.created_at)}\n\n---\n\n${minutes.value.minutes}`
      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `議事録_${minutes.value.video_filename.replace(/\.[^/.]+$/, "")}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    const downloadText = () => {
      if (!minutes.value) return
      
      const content = `議事録\n\nファイル名: ${minutes.value.video_filename}\n作成日時: ${formatDate(minutes.value.created_at)}\n\n${'-'.repeat(50)}\n\n${minutes.value.minutes}`
      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `議事録_${minutes.value.video_filename.replace(/\.[^/.]+$/, "")}.txt`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    const downloadPDF = () => {
      toast.add({
        severity: 'info',
        summary: 'PDF機能',
        detail: 'PDF出力機能は今後実装予定です',
        life: 3000
      })
    }

    const toggleTranscript = () => {
      showTranscript.value = !showTranscript.value
    }

    const updateWordCount = (count) => {
      wordCount.value = count
    }

    const handleResize = () => {
      windowWidth.value = window.innerWidth
      if (!isMobile.value) {
        showTranscript.value = false
      }
    }

    // Lifecycle
    onMounted(() => {
      loadMinutes()
      window.addEventListener('resize', handleResize)
    })

    onBeforeUnmount(() => {
      window.removeEventListener('resize', handleResize)
    })

    return {
      minutes,
      loading,
      error,
      showTranscript,
      isMobile,
      wordCount,
      downloadOptions,
      loadMinutes,
      formatDate,
      copyToClipboard,
      downloadMarkdown,
      downloadText,
      downloadPDF,
      toggleTranscript,
      updateWordCount
    }
  }
}
</script>

<style scoped>
.minutes-viewer {
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeIn 0.6s ease-out;
}

.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-5);
  padding: var(--space-12);
  text-align: center;
  background: white;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--gray-200);
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.error-content i {
  font-size: 1.75rem;
  color: var(--error-500);
  margin-top: var(--space-1);
}

.retry-button {
  margin-top: var(--space-5);
}

.minutes-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-8);
  margin-bottom: var(--space-8);
  padding: var(--space-8);
  background: linear-gradient(135deg, white 0%, var(--gray-50) 100%);
  border-radius: var(--radius-xl);
  border: 2px solid var(--gray-200);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
}

.minutes-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 20% 30%, rgba(99, 102, 241, 0.05) 0%, transparent 60%);
  pointer-events: none;
}

.header-info {
  flex: 1;
}

.minutes-title {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin: 0 0 var(--space-3) 0;
  font-size: 2.25rem;
  color: var(--gray-800);
  font-weight: 800;
  position: relative;
  z-index: 1;
}

.minutes-title i {
  color: var(--primary-500);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  position: relative;
  z-index: 1;
}

.filename {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--primary-600);
  word-break: break-all;
}

.date {
  font-size: 1rem;
  color: var(--gray-700);
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: var(--space-3);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.download-button {
  min-width: 150px;
}

.transcript-toggle {
  width: 100%;
  margin-bottom: var(--space-5);
  border-radius: var(--radius-lg);
}

.content-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: var(--space-8);
  position: relative;
}

.transcript-sidebar {
  position: sticky;
  top: var(--space-8);
  height: fit-content;
  max-height: calc(100vh - 6rem);
}

.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.6);
  padding: var(--space-4);
  overflow-y: auto;
  backdrop-filter: blur(8px);
}

.mobile-overlay .transcript-card {
  background: white;
  margin-top: var(--space-8);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
}

.transcript-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: 1.2rem;
  color: var(--gray-800);
  font-weight: 600;
  position: relative;
}

.transcript-header i {
  color: var(--primary-500);
}

.close-transcript {
  position: absolute;
  right: -var(--space-2);
  top: -var(--space-2);
}

.transcript-scroll {
  height: 450px;
  border-radius: var(--radius-md);
}

.transcript-content {
  padding: var(--space-4);
}

.transcript-text {
  font-family: var(--font-family-mono);
  font-size: 0.95rem;
  line-height: 1.7;
  color: var(--gray-700);
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: var(--gray-50);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--gray-200);
}

.minutes-main {
  min-width: 0;
}

.minutes-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  font-size: 1.2rem;
  color: var(--gray-800);
  font-weight: 600;
}

.minutes-card-header i {
  color: var(--primary-500);
}

.minutes-stats {
  font-size: 0.95rem;
  color: var(--primary-800);
  font-weight: 600;
  background: var(--primary-50);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--primary-200);
}

.minutes-text {
  font-size: 1.1rem;
  line-height: 1.8;
  color: var(--gray-800);
}

:deep(.minutes-text h1) {
  font-size: 1.75rem;
  color: var(--gray-800);
  margin: var(--space-6) 0 var(--space-4) 0;
  padding-bottom: var(--space-3);
  border-bottom: 3px solid var(--primary-200);
  font-weight: 700;
}

:deep(.minutes-text h2) {
  font-size: 1.5rem;
  color: var(--gray-800);
  margin: var(--space-5) 0 var(--space-3) 0;
  font-weight: 600;
}

:deep(.minutes-text h3) {
  font-size: 1.25rem;
  color: var(--gray-800);
  margin: var(--space-4) 0 var(--space-2) 0;
  font-weight: 600;
}

:deep(.minutes-text p) {
  margin: 0 0 var(--space-4) 0;
  color: var(--gray-700);
}

:deep(.minutes-text ul) {
  margin: 0 0 var(--space-4) var(--space-6);
  padding: 0;
}

:deep(.minutes-text li) {
  margin: var(--space-2) 0;
  line-height: 1.7;
  color: var(--gray-700);
}

:deep(.minutes-text strong) {
  font-weight: 700;
  color: var(--gray-800);
}

:deep(.minutes-text em) {
  font-style: italic;
  color: var(--gray-600);
  font-weight: 500;
}

/* Mobile Responsive */
@media (max-width: 1024px) {
  .content-layout {
    grid-template-columns: 300px 1fr;
    gap: 1.5rem;
  }
  
  .transcript-scroll {
    height: 350px;
  }
}

@media (max-width: 768px) {
  .minutes-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }
  
  .header-actions {
    justify-content: center;
  }
  
  .content-layout {
    display: block;
  }
  
  .transcript-sidebar {
    position: static;
    max-height: none;
  }
  
  .minutes-title {
    font-size: 1.5rem;
  }
}

@media (max-width: 480px) {
  .header-actions {
    flex-direction: column;
  }
  
  .download-button {
    min-width: auto;
  }
  
  :deep(.minutes-text) {
    font-size: 0.95rem;
  }
}
</style>