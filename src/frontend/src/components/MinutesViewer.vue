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
            <i class="pi pi-file-text"></i>
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
                <i class="pi pi-file-text"></i>
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
}

.loading-state, .error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  text-align: center;
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.error-content i {
  font-size: 1.5rem;
  color: #dc3545;
  margin-top: 0.25rem;
}

.retry-button {
  margin-top: 1rem;
}

.minutes-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 2rem;
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  border: 1px solid #dee2e6;
}

.header-info {
  flex: 1;
}

.minutes-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  color: #495057;
  font-weight: 700;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.filename {
  font-size: 1.1rem;
  font-weight: 500;
  color: #6366f1;
}

.date {
  font-size: 0.95rem;
  color: #6c757d;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  flex-shrink: 0;
}

.download-button {
  min-width: 140px;
}

.transcript-toggle {
  width: 100%;
  margin-bottom: 1rem;
}

.content-layout {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 2rem;
  position: relative;
}

.transcript-sidebar {
  position: sticky;
  top: 2rem;
  height: fit-content;
  max-height: calc(100vh - 4rem);
}

.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  padding: 1rem;
  overflow-y: auto;
}

.mobile-overlay .transcript-card {
  background: white;
  margin-top: 2rem;
}

.transcript-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  color: #495057;
  position: relative;
}

.close-transcript {
  position: absolute;
  right: -0.5rem;
  top: -0.5rem;
}

.transcript-scroll {
  height: 400px;
}

.transcript-content {
  padding: 0.5rem;
}

.transcript-text {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
  color: #495057;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.minutes-main {
  min-width: 0;
}

.minutes-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  font-size: 1.1rem;
  color: #495057;
}

.minutes-stats {
  font-size: 0.9rem;
  color: #6c757d;
}

.minutes-text {
  font-size: 1rem;
  line-height: 1.8;
  color: #333;
}

:deep(.minutes-text h1) {
  font-size: 1.5rem;
  color: #495057;
  margin: 1.5rem 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e9ecef;
}

:deep(.minutes-text h2) {
  font-size: 1.3rem;
  color: #495057;
  margin: 1.25rem 0 0.75rem 0;
}

:deep(.minutes-text h3) {
  font-size: 1.1rem;
  color: #495057;
  margin: 1rem 0 0.5rem 0;
}

:deep(.minutes-text p) {
  margin: 0 0 1rem 0;
}

:deep(.minutes-text ul) {
  margin: 0 0 1rem 1.5rem;
  padding: 0;
}

:deep(.minutes-text li) {
  margin: 0.5rem 0;
  line-height: 1.6;
}

:deep(.minutes-text strong) {
  font-weight: 600;
  color: #495057;
}

:deep(.minutes-text em) {
  font-style: italic;
  color: #6c757d;
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