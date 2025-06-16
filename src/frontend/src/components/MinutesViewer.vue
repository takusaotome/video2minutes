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

    <div v-else-if="minutes" class="minutes-content" data-testid="minutes-content">
      <!-- Header -->
      <div class="minutes-header">
        <div class="header-info">
          <h1 class="minutes-title">
            <i class="pi pi-file"></i>
            議事録
          </h1>
          <div class="file-info">
            <span class="filename" :title="minutes.video_filename">{{ truncateFilename(minutes.video_filename) }}</span>
            <span class="date">{{ formatDate(getCreationTimestamp()) }}</span>
          </div>
        </div>

        <div class="header-actions">
          <Button
            label="再生成"
            icon="pi pi-refresh"
            @click="regenerateMinutes"
            class="p-button-outlined p-button-warning"
            v-tooltip="'文字起こしから議事録を再生成'"
            :loading="isRegenerating"
          />
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
            data-testid="download-button"
          />
        </div>
      </div>

      <!-- Main Content Area -->
      <div class="main-content">
        <!-- Meeting Details and Minutes -->
        <div class="content-area">
          <div class="minutes-main">
            <!-- Meeting Details Card -->
            <Card class="meeting-details-card">
              <template #title>
                <div class="meeting-details-header">
                  <div class="header-title">
                    <i class="pi pi-calendar"></i>
                    会議詳細
                  </div>
                  <div class="header-actions">
                    <Button
                      v-if="!isEditing"
                      icon="pi pi-pencil"
                      label="編集"
                      @click="startEditing"
                      class="p-button-outlined p-button-sm"
                    />
                    <div v-else class="edit-actions">
                      <Button
                        icon="pi pi-check"
                        label="保存"
                        @click="saveMeetingDetails"
                        class="p-button-sm p-button-success"
                        :disabled="!hasUnsavedChanges"
                      />
                      <Button
                        icon="pi pi-times"
                        label="キャンセル"
                        @click="cancelEditing"
                        class="p-button-sm p-button-outlined"
                      />
                    </div>
                  </div>
                </div>
              </template>

              <template #content>
                <div class="meeting-details-content">
                  <!-- Meeting Name -->
                  <div class="detail-field">
                    <label class="field-label">会議名</label>
                    <div v-if="!isEditing" class="field-display">
                      {{ meetingName || '未設定' }}
                    </div>
                    <InputText
                      v-else
                      v-model="meetingName"
                      @update:modelValue="onMeetingDetailsChange"
                      placeholder="会議名を入力"
                      class="meeting-name-input"
                    />
                  </div>

                  <!-- Meeting Date -->
                  <div class="detail-field">
                    <label class="field-label">開催日時</label>
                    <div v-if="!isEditing" class="field-display">
                      {{ meetingDate ? formatDate(meetingDate) : '未設定' }}
                    </div>
                    <Calendar
                      v-else
                      v-model="meetingDate"
                      @update:modelValue="onMeetingDetailsChange"
                      showTime
                      hourFormat="24"
                      dateFormat="yy/mm/dd"
                      placeholder="開催日時を選択"
                      class="meeting-date-input"
                    />
                  </div>

                  <!-- Attendees -->
                  <div class="detail-field">
                    <label class="field-label">出席者</label>
                    <div v-if="!isEditing" class="field-display">
                      <div v-if="attendees.length === 0" class="no-attendees">
                        未設定
                      </div>
                      <div v-else class="attendees-list">
                        <span
                          v-for="(attendee, index) in attendees"
                          :key="index"
                          class="attendee-chip"
                        >
                          {{ attendee }}
                        </span>
                      </div>
                    </div>
                    <Chips
                      v-else
                      v-model="attendees"
                      @update:modelValue="onMeetingDetailsChange"
                      placeholder="出席者名を入力してEnterキーで追加"
                      class="attendees-input"
                      :allowDuplicate="false"
                      separator=","
                    />
                  </div>
                </div>
              </template>
            </Card>

            <!-- Minutes Content Card -->
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
                  :content="minutesWithUpdatedInfo"
                  :show-toc="false"
                  @word-count="updateWordCount"
                />
              </template>
            </Card>
          </div>
        </div>
      </div>

      <!-- Floating Chat Button -->
      <Button
        icon="pi pi-comments"
        @click="toggleFloatingChat"
        class="floating-chat-button"
        v-tooltip="{
          value: tooltipContent,
          showDelay: 300,
          hideDelay: 100,
          position: 'left',
          class: 'chat-tooltip'
        }"
      >
        <Badge v-if="unreadMessages > 0" :value="unreadMessages" severity="danger" class="chat-badge" />
      </Button>
      
      <!-- Floating Chat Panel -->
      <FloatingChat
        v-if="minutes"
        :is-open="showFloatingChat"
        :task-id="taskId"
        :transcription="minutes.transcription || ''"
        :minutes="minutes.minutes || ''"
        @close="toggleFloatingChat"
        @update-unread="updateUnreadMessages"
        @highlight-citation="highlightCitation"
      />
    </div>

    <!-- Copy Success Toast -->
    <Toast />
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { minutesApi } from '@/services/api'
import Card from 'primevue/card'
import Button from 'primevue/button'
import SplitButton from 'primevue/splitbutton'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import ScrollPanel from 'primevue/scrollpanel'
import Toast from 'primevue/toast'
import InputText from 'primevue/inputtext'
import Calendar from 'primevue/calendar'
import Chips from 'primevue/chips'
import Badge from 'primevue/badge'
import MarkdownRenderer from './MarkdownRenderer.vue'
import LeftPanel from './LeftPanel.vue'
import FloatingChat from './FloatingChat.vue'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'

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
    InputText,
    Calendar,
    Chips,
    Badge,
    MarkdownRenderer,
    LeftPanel,
    FloatingChat
  },
  props: {
    taskId: {
      type: String,
      required: true
    }
  },
  emits: ['back'],
  data() {
    return {
      currentMinutes: null
    }
  },
  setup(props) {
    const toast = useToast()

    const minutes = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const showTranscript = ref(false)
    const windowWidth = ref(window.innerWidth)
    const wordCount = ref(0)
    
    // Meeting details editing
    const meetingName = ref('')
    const meetingDate = ref(null)
    const attendees = ref([])
    const isEditing = ref(false)
    const hasUnsavedChanges = ref(false)
    
    // New layout states
    const showSidebar = ref(false)
    const showFloatingChat = ref(false)
    const unreadMessages = ref(0)
    
    // Regeneration state
    const isRegenerating = ref(false)
    
    // Tooltip content for chat button
    const tooltipContent = computed(() => {
      if (unreadMessages.value > 0) {
        return `会議内容について質問\n${unreadMessages.value}件の未読メッセージがあります`
      }
      return '会議内容について質問\nAIに会議の詳細を聞いてみましょう'
    })

    const isMobile = computed(() => windowWidth.value < 768)

    // Generate minutes content with updated meeting details inserted
    const minutesWithUpdatedInfo = computed(() => {
      if (!minutes.value) return ''
      
      // Start with cleaned content (remove all existing meeting information)
      let content = cleanMinutesContent.value
      
      // Prepare updated meeting information
      const meetingNameText = meetingName.value || '未設定'
      const meetingDateText = meetingDate.value ? formatDate(meetingDate.value) : '未設定'
      const attendeesText = attendees.value.length > 0 ? attendees.value.join('、') : '未設定'
      
      // Increment all existing section numbers by 1 to make room for meeting info as section 1
      content = content.replace(/^### (\d+)\. /gm, (match, number) => {
        return `### ${parseInt(number) + 1}. `
      })
      
      // Create the new meeting info section as section 1
      const meetingInfoHeader = `### 1. 会議情報

**会議名:** ${meetingNameText}  
**開催日時:** ${meetingDateText}  
**出席者:** ${attendeesText}

---

`
      
      // Insert at the beginning of the content
      if (content.trim()) {
        // Check if content starts with a main title (# or ##), not section headers (###)
        if (/^#{1,2}\s/.test(content.trim())) {
          // Insert after the main title only
          content = content.replace(/^(#{1,2}[^\n]*\n)/i, `$1\n${meetingInfoHeader}`)
        } else {
          // Insert at the very beginning (before any section headers like ###)
          content = meetingInfoHeader + content
        }
      } else {
        // If content is empty, just use the meeting info
        content = meetingInfoHeader
      }
      
      // Clean up multiple newlines
      content = content.replace(/\n{3,}/g, '\n\n')
      content = content.trim()
      
      return content
    })
    
    // Keep the clean version for backward compatibility
    const cleanMinutesContent = computed(() => {
      if (!minutes.value) return ''
      
      // Remove any existing meeting details from the minutes content
      let content = minutes.value.minutes
      
      // Remove common meeting detail patterns
      content = content.replace(/^#\s*議事録\s*\n/i, '')

      // Most aggressive: Remove any numbered section that contains "会議情報" and everything until the next numbered section
      content = content.replace(/^\d+\.\s*会議情報[\s\S]*?(?=\d+\.|$)/gm, '')
      
      // Also handle with whitespace at the beginning
      content = content.replace(/^\s*\d+\.\s*会議情報[\s\S]*?(?=^\s*\d+\.|$)/gm, '')
      
      // Remove entire numbered sections containing meeting info (with lookahead for next section or heading)
      content = content.replace(/^\s*\d+\.\s*(?:会議情報|会議概要|基本情報)[\s\S]*?(?=^\s*\d+\.|^\s*#{1,6}\s+|$)/gmi, '')
      
      // Remove any remaining bullet points that mention meeting details
      content = content.replace(/^\s*[-*]\s*\*\*(?:会議名|開催日時?|開催日|出席者|参加者)\*\*[:：].*$/gm, '')
      content = content.replace(/^\s*[-*]\s*(?:会議名|開催日時?|開催日|出席者|参加者)[:：].*$/gm, '')
      
      // Remove meeting info section headers
      content = content.replace(/^#{1,6}\s*(?:会議情報|会議概要|基本情報)\s*\n/gmi, '')
      
      // Lines with no bullet (standalone)
      content = content.replace(/^\*\*(?:会議名|開催日時?|開催日|出席者|参加者)[:：].*\n/gm, '')
      content = content.replace(/^(?:会議名|開催日時?|開催日|出席者|参加者)[:：].*\n/gm, '')

      // Bullet list lines
      content = content.replace(/^\s*[-*]\s*\*\*(?:会議名|開催日時?|開催日|出席者|参加者)[:：].*\n/gm, '')
      content = content.replace(/^\s*[-*]\s*(?:会議名|開催日時?|開催日|出席者|参加者)[:：].*\n/gm, '')

      // Remove any remaining meeting detail lines within sections
      content = content.replace(/^\s*[-*]\s*\*\*(?:会議名|開催日時?|開催日|出席者|参加者)\*\*[:：].*$/gm, '')
      
      // Remove horizontal rules that might be left over
      content = content.replace(/^---+\s*\n/gm, '')
      
      // Clean up multiple newlines and empty sections
      content = content.replace(/\n{3,}/g, '\n\n')
      
      // Remove empty numbered list items
      content = content.replace(/^\s*\d+\.\s*\n/gm, '')
      
      // Renumber remaining sections to maintain sequential order
      let sectionNumber = 1
      content = content.replace(/^###?\s*\d+\.\s*/gm, () => {
        return `### ${sectionNumber++}. `
      })
      
      content = content.trim()
      
      return content
    })
    

    // Generate complete content for downloads (includes meeting details)
    const completeMinutesForDownload = computed(() => {
      if (!minutes.value) return ''
      
      // Add file info to the updated minutes content
      const fileInfo = `**ファイル名:** ${minutes.value.video_filename}  
**作成日時:** ${formatDate(getCreationTimestamp())}  

`
      
      // Insert file info at the beginning
      let content = minutesWithUpdatedInfo.value
      if (content.includes('#### 会議情報')) {
        // Insert file info before meeting info
        content = content.replace('#### 会議情報', `${fileInfo}#### 会議情報`)
      } else if (content.startsWith('# ')) {
        // Insert after the main title
        content = content.replace(/^(#[^\n]*\n)/, `$1\n${fileInfo}`)
      } else {
        // Insert at the beginning
        content = fileInfo + content
      }
      
      return content
    })

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
      },
      {
        separator: true
      },
      {
        label: '文字起こし全文 (.txt)',
        icon: 'pi pi-file-text',
        command: () => downloadTranscription()
      }
    ])

    const loadMinutes = async () => {
      loading.value = true
      error.value = null

      try {
        // Use the API service
        const response = await minutesApi.getTaskResult(props.taskId)
        minutes.value = response.data
        
        // Initialize meeting details by extracting from minutes content
        initializeMeetingDetails()
        hasUnsavedChanges.value = false
      } catch (err) {
        error.value = err.message
        console.error('Failed to load minutes:', err)
      } finally {
        loading.value = false
      }
    }

    const formatDate = timestamp => {
      if (!timestamp) {
        // If no timestamp provided, use current time as fallback
        timestamp = new Date().toISOString()
      }
      // UTC文字列をローカルタイムゾーンに変換
      const date = new Date(timestamp)
      if (isNaN(date.getTime())) return '日時形式エラー'
      return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      })
    }

    // Get the most appropriate creation timestamp
    const getCreationTimestamp = () => {
      if (!minutes.value) return new Date().toISOString()
      
      // Priority order: created_at > upload_timestamp > current time
      return minutes.value.created_at || 
             minutes.value.upload_timestamp || 
             new Date().toISOString()
    }

    const truncateFilename = (filename, maxLength = 50) => {
      if (!filename) return '未設定'
      if (filename.length <= maxLength) return filename
      
      const extension = filename.split('.').pop()
      const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'))
      const truncatedName = nameWithoutExt.substring(0, maxLength - extension.length - 4)
      
      return `${truncatedName}...${extension}`
    }

    const copyToClipboard = async () => {
      if (!minutes.value) return

      try {
        await navigator.clipboard.writeText(minutesWithUpdatedInfo.value)
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

      // Add file info to the complete content for download
      const fileInfo = `**ファイル名:** ${minutes.value.video_filename}  
**作成日時:** ${formatDate(getCreationTimestamp())}  

`
      
      const content = completeMinutesForDownload.value.replace('# 議事録\n\n', `# 議事録\n\n${fileInfo}`)

      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `議事録_${minutes.value.video_filename.replace(/\.[^/.]+$/, '')}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    const downloadText = () => {
      if (!minutes.value) return

      // Convert markdown to plain text format
      let textContent = minutesWithUpdatedInfo.value
      
      // Remove markdown formatting
      textContent = textContent.replace(/#{1,6}\s+/g, '') // Remove headers
      textContent = textContent.replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold
      textContent = textContent.replace(/\*(.*?)\*/g, '$1') // Remove italic
      textContent = textContent.replace(/\[(.*?)\]\(.*?\)/g, '$1') // Remove links
      textContent = textContent.replace(/^-\s+/gm, '• ') // Convert bullets
      textContent = textContent.replace(/^\d+\.\s+/gm, (match) => {
        return match
      })
      
      // Add file information at the top
      const fileInfo = `議事録

ファイル名: ${minutes.value.video_filename}
作成日時: ${formatDate(getCreationTimestamp())}

${'-'.repeat(50)}

`

      const content = fileInfo + textContent

      const blob = new Blob([content], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `議事録_${minutes.value.video_filename.replace(/\.[^/.]+$/, '')}.txt`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    const downloadPDF = async () => {
      if (!minutes.value) return

      toast.add({
        severity: 'info',
        summary: 'PDF生成中',
        detail: 'PDFを生成しています...',
        life: 3000
      })

      try {
        // Find the existing rendered markdown content
        const markdownRenderer = document.querySelector('.markdown-renderer .markdown-content')
        
        if (!markdownRenderer) {
          throw new Error('レンダリングされたマークダウンコンテンツが見つかりません')
        }

        // Create a temporary container for PDF content
        const tempContainer = document.createElement('div')
        tempContainer.style.position = 'absolute'
        tempContainer.style.left = '-9999px'
        tempContainer.style.top = '-9999px'
        tempContainer.style.width = '800px'
        tempContainer.style.padding = '40px'
        tempContainer.style.backgroundColor = 'white'
        tempContainer.style.fontFamily = '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Yu Gothic", "Meiryo", sans-serif'

        // Create minimal header for PDF (only file info, not meeting info)
        const header = document.createElement('div')
        header.style.marginBottom = '30px'
        header.style.borderBottom = '2px solid var(--gray-200)'
        header.style.paddingBottom = '20px'
        
        header.innerHTML = `
          <h1 style="color: var(--gray-700); font-size: 24px; margin: 0 0 15px 0; font-weight: bold;">議事録</h1>
          <div style="color: var(--gray-500); font-size: 12px;">
            <div style="margin-bottom: 5px;"><strong>ファイル名:</strong> ${minutes.value.video_filename}</div>
            <div><strong>作成日時:</strong> ${formatDate(getCreationTimestamp())}</div>
          </div>
        `

        // Clone the rendered markdown content
        const markdownClone = markdownRenderer.cloneNode(true)
        
        // Remove only the duplicate title from markdown content
        const removeDuplicateTitle = (element) => {
          // Remove the first heading if it's just "議事録" (since we have it in PDF header)
          const h1Elements = element.querySelectorAll('h1')
          h1Elements.forEach(h1 => {
            if (h1.textContent.trim() === '議事録') {
              h1.remove()
            }
          })
          
          // Remove any standalone file info lines at the very beginning (but keep meeting info section)
          const allElements = element.children
          for (let i = 0; i < allElements.length; i++) {
            const el = allElements[i]
            const text = el.textContent || ''
            
            // Only remove standalone file info lines (not within a section)
            if ((text.includes('ファイル名：') || text.includes('作成日時：')) && 
                !text.includes('会議名：') && !text.includes('開催日時：') && !text.includes('出席者：')) {
              el.remove()
              i-- // Adjust index after removal
            } else if (text.trim() === '' || text.trim() === '---') {
              // Remove empty elements or dividers at the beginning
              const nextEl = allElements[i + 1]
              if (nextEl && !nextEl.textContent.includes('1. 会議情報')) {
                el.remove()
                i--
              } else {
                break
              }
            } else {
              // Stop removing once we hit actual content
              break
            }
          }
        }
        
        removeDuplicateTitle(markdownClone)
        
        // Apply PDF-specific styles to the cloned content
        const applyPDFStyles = (element) => {
          element.style.color = 'var(--gray-700)'
          element.style.fontSize = '14px'
          element.style.lineHeight = '1.6'
          
          // Style headings
          const h1Elements = element.querySelectorAll('h1')
          h1Elements.forEach(h1 => {
            h1.style.fontSize = '20px'
            h1.style.fontWeight = 'bold'
            h1.style.color = 'var(--gray-800)'
            h1.style.marginTop = '24px'
            h1.style.marginBottom = '16px'
            h1.style.borderBottom = '2px solid var(--gray-200)'
            h1.style.paddingBottom = '8px'
          })

          const h2Elements = element.querySelectorAll('h2')
          h2Elements.forEach(h2 => {
            h2.style.fontSize = '18px'
            h2.style.fontWeight = 'bold'
            h2.style.color = 'var(--gray-800)'
            h2.style.marginTop = '20px'
            h2.style.marginBottom = '12px'
          })

          const h3Elements = element.querySelectorAll('h3')
          h3Elements.forEach(h3 => {
            h3.style.fontSize = '16px'
            h3.style.fontWeight = 'bold'
            h3.style.color = 'var(--gray-800)'
            h3.style.marginTop = '16px'
            h3.style.marginBottom = '8px'
          })

          // Style paragraphs
          const pElements = element.querySelectorAll('p')
          pElements.forEach(p => {
            p.style.marginBottom = '12px'
            p.style.color = 'var(--gray-700)'
          })

          // Style lists
          const ulElements = element.querySelectorAll('ul')
          ulElements.forEach(ul => {
            ul.style.marginBottom = '12px'
            ul.style.paddingLeft = '20px'
          })

          const olElements = element.querySelectorAll('ol')
          olElements.forEach(ol => {
            ol.style.marginBottom = '12px'
            ol.style.paddingLeft = '20px'
          })

          const liElements = element.querySelectorAll('li')
          liElements.forEach(li => {
            li.style.marginBottom = '4px'
            li.style.color = 'var(--gray-700)'
          })

          // Style strong and em
          const strongElements = element.querySelectorAll('strong')
          strongElements.forEach(strong => {
            strong.style.fontWeight = 'bold'
            strong.style.color = 'var(--gray-800)'
          })

          const emElements = element.querySelectorAll('em')
          emElements.forEach(em => {
            em.style.fontStyle = 'italic'
            em.style.color = 'var(--gray-600)'
          })

          // Style code blocks
          const codeElements = element.querySelectorAll('code')
          codeElements.forEach(code => {
            code.style.backgroundColor = 'var(--gray-100)'
            code.style.padding = '2px 4px'
            code.style.borderRadius = '4px'
            code.style.fontFamily = 'monospace'
            code.style.fontSize = '12px'
          })

          const preElements = element.querySelectorAll('pre')
          preElements.forEach(pre => {
            pre.style.backgroundColor = 'var(--gray-100)'
            pre.style.padding = '12px'
            pre.style.borderRadius = '6px'
            pre.style.overflow = 'visible'
            pre.style.whiteSpace = 'pre-wrap'
            pre.style.fontFamily = 'monospace'
            pre.style.fontSize = '12px'
            pre.style.marginBottom = '12px'
          })

          // Style tables
          const tableElements = element.querySelectorAll('table')
          tableElements.forEach(table => {
            table.style.borderCollapse = 'collapse'
            table.style.width = '100%'
            table.style.marginBottom = '12px'
          })

          const thElements = element.querySelectorAll('th')
          thElements.forEach(th => {
            th.style.border = '1px solid var(--gray-300)'
            th.style.padding = '8px'
            th.style.backgroundColor = 'var(--gray-50)'
            th.style.fontWeight = 'bold'
          })

          const tdElements = element.querySelectorAll('td')
          tdElements.forEach(td => {
            td.style.border = '1px solid var(--gray-300)'
            td.style.padding = '8px'
          })

          // Remove any interactive elements that don't work in PDF
          const buttonElements = element.querySelectorAll('button')
          buttonElements.forEach(button => button.remove())
        }

        applyPDFStyles(markdownClone)

        // Assemble the final content
        tempContainer.appendChild(header)
        tempContainer.appendChild(markdownClone)
        document.body.appendChild(tempContainer)

        // Generate PDF using html2canvas and jsPDF
        const canvas = await html2canvas(tempContainer, {
          scale: 2,
          useCORS: true,
          allowTaint: true,
          backgroundColor: '#ffffff',
          height: tempContainer.scrollHeight,
          windowHeight: tempContainer.scrollHeight
        })

        // Remove temporary container
        document.body.removeChild(tempContainer)

        const imgData = canvas.toDataURL('image/png')
        const pdf = new jsPDF('p', 'mm', 'a4')
        
        const imgWidth = 210 // A4 width in mm
        const pageHeight = 295 // A4 height in mm
        const imgHeight = (canvas.height * imgWidth) / canvas.width
        let heightLeft = imgHeight

        let position = 0

        // Add first page
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
        heightLeft -= pageHeight

        // Add additional pages if needed
        while (heightLeft >= 0) {
          position = heightLeft - imgHeight
          pdf.addPage()
          pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
          heightLeft -= pageHeight
        }

        // Download the PDF
        const filename = `議事録_${minutes.value.video_filename.replace(/\.[^/.]+$/, '')}.pdf`
        pdf.save(filename)

        toast.add({
          severity: 'success',
          summary: 'PDF生成完了',
          detail: 'PDFファイルをダウンロードしました',
          life: 3000
        })
      } catch (error) {
        console.error('PDF generation failed:', error)
        toast.add({
          severity: 'error',
          summary: 'PDF生成エラー',
          detail: 'PDFの生成に失敗しました',
          life: 3000
        })
      }
    }

    const downloadTranscription = () => {
      if (!minutes.value?.transcription) return

      try {
        const content = minutes.value.transcription
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        const filename = minutes.value.video_filename.replace(/\.[^/.]+$/, '')
        link.download = `文字起こし_${filename}.txt`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)

        toast.add({
          severity: 'success',
          summary: 'ダウンロード完了',
          detail: '文字起こし全文をダウンロードしました',
          life: 3000
        })
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'ダウンロード失敗',
          detail: '文字起こしのダウンロードに失敗しました',
          life: 3000
        })
      }
    }
    
    const regenerateMinutes = async () => {
      if (!minutes.value || isRegenerating.value) return
      
      // 確認ダイアログを表示
      const confirmed = window.confirm(
        '現在の議事録を破棄して、文字起こしから再生成しますか？\n' +
        'この操作は取り消せません。'
      )
      
      if (!confirmed) return
      
      isRegenerating.value = true
      
      try {
        toast.add({
          severity: 'info',
          summary: '再生成開始',
          detail: '議事録を再生成しています...',
          life: 5000
        })
        
        // 再生成APIを呼び出し
        const response = await minutesApi.regenerateMinutes(props.taskId)
        
        // タスクIDが返ってくる場合は、ステータスをポーリング
        if (response.data.task_id) {
          // 新しいタスクの完了を待つ
          await pollTaskStatus(response.data.task_id)
        } else {
          // 直接結果が返ってくる場合
          minutes.value = response.data
          initializeMeetingDetails()
        }
        
        toast.add({
          severity: 'success',
          summary: '再生成完了',
          detail: '議事録が正常に再生成されました',
          life: 3000
        })
        
      } catch (error) {
        console.error('再生成エラー:', error)
        toast.add({
          severity: 'error',
          summary: '再生成エラー',
          detail: error.response?.data?.detail || '議事録の再生成に失敗しました',
          life: 5000
        })
      } finally {
        isRegenerating.value = false
      }
    }
    
    // タスクステータスのポーリング
    const pollTaskStatus = async (taskId) => {
      const maxAttempts = 60 // 最大60回（5分）
      let attempts = 0
      
      while (attempts < maxAttempts) {
        try {
          const statusResponse = await minutesApi.getTaskStatus(taskId)
          const status = statusResponse.data.status
          
          if (status === 'completed') {
            // 結果を取得
            const resultResponse = await minutesApi.getTaskResult(taskId)
            minutes.value = resultResponse.data
            initializeMeetingDetails()
            return
          } else if (status === 'failed') {
            throw new Error('タスクが失敗しました')
          }
          
          // 5秒待つ
          await new Promise(resolve => setTimeout(resolve, 5000))
          attempts++
          
        } catch (error) {
          console.error('ステータス確認エラー:', error)
          throw error
        }
      }
      
      throw new Error('タスクがタイムアウトしました')
    }

    const toggleTranscript = () => {
      showTranscript.value = !showTranscript.value
    }
    
    const toggleSidebar = () => {
      showSidebar.value = !showSidebar.value
    }
    
    const toggleFloatingChat = () => {
      showFloatingChat.value = !showFloatingChat.value
      if (!showFloatingChat.value) {
        unreadMessages.value = 0
      }
    }
    
    const updateUnreadMessages = (count) => {
      unreadMessages.value = count
    }
    
    const highlightCitation = (citation) => {
      // サイドバーを開いて引用箇所をハイライト
      showSidebar.value = true
      // TODO: 実際のハイライト処理を実装
    }

    const updateWordCount = count => {
      wordCount.value = count
    }

    const handleResize = () => {
      windowWidth.value = window.innerWidth
      if (!isMobile.value) {
        showTranscript.value = false
      }
    }

    // Extract meeting details from minutes content
    const initializeMeetingDetails = () => {
      // First, try to load from localStorage
      const storageKey = `meeting_details_${props.taskId}`
      const savedDetails = localStorage.getItem(storageKey)
      
      console.log('Loading meeting details with key:', storageKey)
      console.log('Saved details from localStorage:', savedDetails)
      
      if (savedDetails) {
        try {
          const parsed = JSON.parse(savedDetails)
          console.log('Parsed meeting details:', parsed)
          console.log('Parsed attendees:', parsed.attendees, 'Type:', typeof parsed.attendees)
          
          meetingName.value = parsed.meeting_name || ''
          meetingDate.value = new Date(parsed.meeting_date)
          attendees.value = parsed.attendees || []
          
          console.log('Set attendees.value to:', attendees.value)
          return
        } catch (error) {
          console.warn('Failed to parse saved meeting details:', error)
        }
      }
      
      // If no saved data, extract from minutes content
      if (!minutes.value?.minutes) {
        meetingName.value = ''
        meetingDate.value = new Date()
        attendees.value = []
        return
      }

      const content = minutes.value.minutes
      
      // Extract meeting name
      const namePatterns = [
        /(?:会議名|件名|タイトル)[:：]\s*([^\n]+)/i,
        /\*\*(?:会議名|件名|タイトル)[:：]\*\*\s*([^\n]+)/i
      ]
      
      let extractedName = ''
      for (const pattern of namePatterns) {
        const match = content.match(pattern)
        if (match && match[1] && !match[1].includes('未設定') && !match[1].includes('未記載')) {
          extractedName = match[1].trim()
          break
        }
      }
      
      meetingName.value = extractedName
      
      // Extract meeting date
      const datePatterns = [
        /^(?:\s*[-*]\s*)?\*\*(?:開催日時?|会議日時?|開催日|会議日|日時)[:：]\*\*\s*([^\n]+)/m,
        /^(?:\s*[-*]\s*)?(?:開催日時?|会議日時?|開催日|会議日|日時)[:：]\s*([^\n]+)/m
      ]
      
      let extractedDate = null
      for (const pattern of datePatterns) {
        const match = content.match(pattern)
        if (match && match[1] && !match[1].includes('未記載') && !match[1].includes('未設定')) {
          const dateStr = match[1].trim()
          // Try to parse various date formats
          const parsedDate = parseJapaneseDate(dateStr)
          if (parsedDate) {
            extractedDate = parsedDate
            break
          }
        }
      }
      
      meetingDate.value = extractedDate || new Date()
      
      // Extract attendees
      const attendeePatterns = [
        /^(?:\s*[-*]\s*)?\*\*(?:出席者|参加者)[:：]\*\*\s*([^\n]+)/m,
        /^(?:\s*[-*]\s*)?(?:出席者|参加者)[:：]\s*([^\n]+)/m
      ]
      
      let extractedAttendees = []
      for (const pattern of attendeePatterns) {
        const match = content.match(pattern)
        if (match && match[1] && !match[1].includes('未設定') && !match[1].includes('未記載')) {
          const attendeesStr = match[1].trim()
          // Split by common separators and clean up
          extractedAttendees = attendeesStr
            .split(/[、,，;；]/)
            .map(name => name.trim())
            .filter(name => name && name !== '他' && name !== 'など')
          break
        }
      }
      
      console.log('Extracted attendees from content:', extractedAttendees)
      attendees.value = extractedAttendees
    }

    // Parse Japanese date formats
    const parseJapaneseDate = (dateStr) => {
      try {
        // Handle various Japanese date formats
        let normalizedDate = dateStr
          .replace(/年/g, '/')
          .replace(/月/g, '/')
          .replace(/日/g, '')
          .replace(/\s+/g, ' ')
          .trim()
        
        // Try to parse the normalized date
        const parsed = new Date(normalizedDate)
        if (!isNaN(parsed.getTime())) {
          return parsed
        }
        
        // If that fails, try some other common patterns
        const patterns = [
          /(\d{4})\/(\d{1,2})\/(\d{1,2})/,
          /(\d{1,2})\/(\d{1,2})\/(\d{4})/,
          /(\d{4})-(\d{1,2})-(\d{1,2})/
        ]
        
        for (const pattern of patterns) {
          const match = normalizedDate.match(pattern)
          if (match) {
            const [, year, month, day] = match
            const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day))
            if (!isNaN(date.getTime())) {
              return date
            }
          }
        }
        
        return null
      } catch (error) {
        return null
      }
    }

    // Meeting details editing functions
    const startEditing = () => {
      isEditing.value = true
    }

    const cancelEditing = () => {
      // Reset to original extracted values
      initializeMeetingDetails()
      isEditing.value = false
      hasUnsavedChanges.value = false
    }

    const saveMeetingDetails = async () => {
      try {
        // Debug logging
        console.log('Saving meeting details...')
        console.log('attendees.value:', attendees.value)
        console.log('attendees type:', typeof attendees.value, 'Is Array:', Array.isArray(attendees.value))
        if (Array.isArray(attendees.value) && attendees.value.length > 0) {
          console.log('First attendee:', attendees.value[0], 'Type:', typeof attendees.value[0])
        }
        
        // Update the local minutes object
        minutes.value.meeting_name = meetingName.value
        minutes.value.meeting_date = meetingDate.value
        minutes.value.attendees = attendees.value
        
        // Save to localStorage for persistence
        const storageKey = `meeting_details_${props.taskId}`
        const meetingDetails = {
          meeting_name: meetingName.value,
          meeting_date: meetingDate.value,
          attendees: attendees.value,
          updated_at: new Date().toISOString()
        }
        
        console.log('Saving to localStorage with key:', storageKey)
        console.log('Meeting details to save:', meetingDetails)
        console.log('attendees.value before save:', attendees.value)
        console.log('attendees is Array?', Array.isArray(attendees.value))
        
        localStorage.setItem(storageKey, JSON.stringify(meetingDetails))
        
        // Verify the save
        const savedData = localStorage.getItem(storageKey)
        console.log('Data saved to localStorage:', savedData)
        const parsedSaved = JSON.parse(savedData)
        console.log('Parsed saved attendees:', parsedSaved.attendees)
        
        // Here you would typically save to the backend
        // await minutesApi.updateMeetingDetails(props.taskId, {
        //   meeting_date: meetingDate.value,
        //   attendees: attendees.value
        // })

        isEditing.value = false
        hasUnsavedChanges.value = false
        
        toast.add({
          severity: 'success',
          summary: '保存完了',
          detail: '開催日時と出席者が更新されました',
          life: 3000
        })
      } catch (error) {
        console.error('Failed to save meeting details:', error)
        toast.add({
          severity: 'error',
          summary: '保存エラー',
          detail: '開催日時と出席者の保存に失敗しました',
          life: 3000
        })
      }
    }

    const onMeetingDetailsChange = (value) => {
      console.log('onMeetingDetailsChange called with value:', value)
      console.log('Current attendees.value:', attendees.value)
      hasUnsavedChanges.value = true
    }

    // Watch attendees for debugging and real-time updates
    watch(attendees, (newValue, oldValue) => {
      console.log('Attendees watch triggered')
      console.log('Old value:', oldValue)
      console.log('New value:', newValue)
      console.log('New value type:', typeof newValue, 'Is Array:', Array.isArray(newValue))
      
      // Mark as changed for real-time preview
      if (isEditing.value) {
        hasUnsavedChanges.value = true
      }
    }, { deep: true })
    
    // Watch meeting name for real-time updates
    watch(meetingName, (newValue, oldValue) => {
      console.log('Meeting name watch triggered')
      console.log('Old value:', oldValue)
      console.log('New value:', newValue)
      
      // Mark as changed for real-time preview
      if (isEditing.value) {
        hasUnsavedChanges.value = true
      }
    })
    
    // Watch meeting date for real-time updates
    watch(meetingDate, (newValue, oldValue) => {
      console.log('Meeting date watch triggered')
      console.log('Old value:', oldValue)
      console.log('New value:', newValue)
      
      // Mark as changed for real-time preview
      if (isEditing.value) {
        hasUnsavedChanges.value = true
      }
    })
    
    // Handle minutes update from chat
    const handleMinutesUpdate = (updatedMinutes) => {
      if (minutes.value) {
        minutes.value.minutes = updatedMinutes
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
      cleanMinutesContent,
      minutesWithUpdatedInfo,
      completeMinutesForDownload,
      downloadOptions,
      loadMinutes,
      formatDate,
      getCreationTimestamp,
      truncateFilename,
      copyToClipboard,
      downloadMarkdown,
      downloadText,
      downloadPDF,
      downloadTranscription,
      regenerateMinutes,
      isRegenerating,
      toggleTranscript,
      updateWordCount,
      handleMinutesUpdate,
      // Meeting details editing
      meetingName,
      meetingDate,
      attendees,
      isEditing,
      hasUnsavedChanges,
      startEditing,
      cancelEditing,
      saveMeetingDetails,
      onMeetingDetailsChange,
      // New layout methods
      showSidebar,
      showFloatingChat,
      unreadMessages,
      tooltipContent,
      toggleSidebar,
      toggleFloatingChat,
      updateUnreadMessages,
      highlightCitation
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

/* Global Card styling for consistency */
.minutes-viewer :deep(.p-card) {
  box-sizing: border-box;
}

.minutes-viewer :deep(.p-card-body) {
  padding: 0;
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
  gap: 32px;
  margin: 0 24px 32px 24px;
  padding: 32px;
  background: linear-gradient(135deg, white 0%, var(--gray-50) 100%);
  border-radius: var(--radius-xl);
  border: 2px solid var(--gray-200);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
  width: calc(100% - 48px);
  box-sizing: border-box;
}

.minutes-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(
    circle at 20% 30%,
    rgba(99, 102, 241, 0.05) 0%,
    transparent 60%
  );
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

/* 新しいレイアウトスタイル */
.main-content {
  position: relative;
  width: 100%;
  max-width: 100%;
  padding: 0;
}

/* サイドバー関連のスタイルは削除 */

.content-area {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  min-height: calc(100vh - 300px);
}

.floating-chat-button {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 60px;
  height: 60px;
  border-radius: 30px;
  background: var(--primary-500);
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  font-size: 1.5rem;
}

.floating-chat-button:hover {
  background: var(--primary-600);
  transform: scale(1.1);
}

.floating-chat-button .chat-badge {
  position: absolute;
  top: -5px;
  right: -5px;
}

/* 旧レイアウトスタイル（非推奨） */
.content-layout {
  display: grid;
  grid-template-columns: 45% 55%;
  gap: 24px;
  position: relative;
  padding: 0 24px;
  align-items: start;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  min-height: calc(100vh - 300px);
}

/* 新しいカラム構造 */
.left-column,
.right-column {
  margin: 0 !important;
  padding: 0 !important;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.left-column {
  padding-left: 0;
}

.right-column {
  padding-right: 0;
  height: auto;
}

/* 上端を確実に揃える */
.left-column .transcript-sidebar,
.right-column .minutes-main {
  margin-top: 0 !important;
  padding-top: 0 !important;
}

.left-column .transcript-card,
.right-column .meeting-details-card {
  margin-top: 0 !important;
}

.left-panel-container {
  position: sticky;
  top: 32px;
  height: calc(100vh - 200px);
  width: 100%;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.transcript-sidebar :deep(.p-card) {
  margin: 0 !important;
}

.transcript-sidebar :deep(.p-card-body) {
  padding: 0 !important;
  margin: 0 !important;
}

.transcript-sidebar :deep(.p-card-caption) {
  margin: 0 !important;
}

.transcript-sidebar :deep(.p-card-title) {
  padding: 16px 20px !important;
  margin: 0 !important;
  height: 72px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--gray-200);
  box-sizing: border-box;
}

.transcript-sidebar :deep(.p-card-content) {
  padding: 0 !important;
  margin: 0 !important;
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

.transcript-card {
  width: 100%;
  height: fit-content;
  box-sizing: border-box;
  margin: 0 !important;
  flex: 1;
  align-self: flex-start;
}

.transcript-card :deep(.p-card) {
  width: 100%;
  background: #f8f9fa;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--gray-200);
}

.transcript-card :deep(.p-card-content) {
  padding: 0;
}

.transcript-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: 1.2rem;
  color: var(--gray-800);
  font-weight: 600;
  position: relative;
  width: 100%;
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
  padding: 20px;
}

.transcript-text {
  font-family: var(--font-family-mono);
  font-size: 16px;
  line-height: 1.8;
  color: var(--gray-700);
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: var(--gray-50);
  padding: 20px;
  border-radius: var(--radius-md);
  border: 1px solid var(--gray-200);
}

.minutes-main {
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin: 0 !important;
  padding: 0;
  align-self: start;
  min-height: calc(100vh - 200px);
  height: auto;
  overflow-y: visible;
}

.minutes-main > * {
  margin: 0 !important;
}

/* 会議詳細カードと議事録カードの統一スタイル */
.meeting-details-card,
.minutes-card {
  width: 100%;
  margin: 0 !important;
  box-sizing: border-box;
  max-width: 100%;
  overflow: hidden;
  align-self: flex-start;
  flex-shrink: 0;
}

/* 会議詳細カードの高さ自動調整 */
.meeting-details-card {
  min-height: 280px;
  height: auto;
  overflow: visible;
  flex-shrink: 0;
}

/* 議事録カードの可変高さ */
.minutes-card {
  flex: 1 1 auto;
  min-height: 400px;
  overflow: visible;
  height: auto;
}

/* Debug: 上端位置を視覚的に確認するためのデバッグスタイル */
.debug-alignment {
  position: relative;
}

.debug-alignment::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: red;
  z-index: 9999;
}

.meeting-details-card :deep(.p-card),
.minutes-card :deep(.p-card) {
  width: 100%;
  max-width: 100%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.meeting-details-card :deep(.p-card-content) {
  padding: 20px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: visible;
  height: auto;
}


/* 会議詳細カード固有のスタイル */
.meeting-details-card :deep(.p-card) {
  background: #f0f7ff;
  border: 1px solid rgba(99, 102, 241, 0.1);
  margin: 0 !important;
}

.meeting-details-card :deep(.p-card-body) {
  padding: 0 !important;
  margin: 0 !important;
}

.meeting-details-card :deep(.p-card-caption) {
  margin: 0 !important;
}

.meeting-details-card :deep(.p-card-title) {
  padding: 16px 20px !important;
  margin: 0 !important;
  height: 72px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--gray-200);
  box-sizing: border-box;
}

.meeting-details-card :deep(.p-card-content) {
  padding: 20px !important;
  margin: 0 !important;
}

/* 議事録カード固有のスタイル */
.minutes-card :deep(.p-card) {
  background: white;
  border: 1px solid var(--gray-200);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.minutes-card :deep(.p-card-body) {
  padding: 0 !important;
  margin: 0 !important;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.minutes-card :deep(.p-card-caption) {
  margin: 0 !important;
}

.minutes-card :deep(.p-card-title) {
  padding: 16px 20px !important;
  margin: 0 !important;
  height: 72px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--gray-200);
  box-sizing: border-box;
}

.minutes-card :deep(.p-card-content) {
  padding: 20px !important;
  margin: 0 !important;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.minutes-card :deep(.markdown-renderer) {
  width: 100%;
  max-width: 100%;
  overflow: visible;
  height: auto;
  min-height: 100%;
}

/* カスタムスクロールバー */
.minutes-main,
.minutes-card :deep(.p-card-content) {
  scrollbar-width: thin;
  scrollbar-color: var(--gray-400) var(--gray-100);
}

.minutes-main::-webkit-scrollbar,
.minutes-card :deep(.p-card-content)::-webkit-scrollbar {
  width: 8px;
}

.minutes-main::-webkit-scrollbar-track,
.minutes-card :deep(.p-card-content)::-webkit-scrollbar-track {
  background: var(--gray-100);
  border-radius: 4px;
}

.minutes-main::-webkit-scrollbar-thumb,
.minutes-card :deep(.p-card-content)::-webkit-scrollbar-thumb {
  background: var(--gray-400);
  border-radius: 4px;
  transition: background 0.2s ease;
}

.minutes-main::-webkit-scrollbar-thumb:hover,
.minutes-card :deep(.p-card-content)::-webkit-scrollbar-thumb:hover {
  background: var(--gray-500);
}

/* 議事録内のテーブルとコンテンツの幅制限 */
.minutes-card :deep(.markdown-renderer table) {
  width: 100%;
  max-width: 100%;
  table-layout: fixed;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.minutes-card :deep(.markdown-renderer td),
.minutes-card :deep(.markdown-renderer th) {
  word-wrap: break-word;
  overflow-wrap: break-word;
  max-width: 0;
}

.minutes-card :deep(.markdown-renderer pre) {
  max-width: 100%;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.minutes-card :deep(.markdown-renderer code) {
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.minutes-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  font-size: 1.2rem;
  color: var(--gray-800);
  font-weight: 600;
  width: 100%;
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

/* Meeting Details Styles */
.meeting-details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  font-size: 1.2rem;
  color: var(--gray-800);
  font-weight: 600;
  width: 100%;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.header-title i {
  color: var(--primary-500);
}

.edit-actions {
  display: flex;
  gap: var(--space-2);
}

.meeting-details-content {
  display: grid;
  gap: var(--space-5);
}

.detail-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field-label {
  font-weight: 600;
  color: var(--gray-700);
  font-size: 0.95rem;
}

.field-display {
  padding: var(--space-3);
  background: var(--gray-50);
  border-radius: var(--radius-md);
  border: 1px solid var(--gray-200);
  min-height: 42px;
  display: flex;
  align-items: center;
  font-size: 1rem;
  color: var(--gray-800);
}

.no-attendees {
  color: var(--gray-500);
  font-style: italic;
}

.attendees-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.attendee-chip {
  background: var(--primary-100);
  color: var(--primary-800);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-size: 0.9rem;
  font-weight: 500;
  border: 1px solid var(--primary-200);
}

.meeting-name-input,
.meeting-date-input,
.attendees-input {
  width: 100%;
}

:deep(.meeting-date-input .p-inputtext) {
  width: 100%;
}

:deep(.attendees-input .p-chips-multiple-container) {
  min-height: 42px;
  padding: var(--space-2);
}

:deep(.attendees-input .p-chips-token) {
  background: var(--primary-100);
  color: var(--primary-800);
  border: 1px solid var(--primary-200);
}

:deep(.attendees-input .p-chips-input-token input) {
  padding: var(--space-2);
  min-width: 200px;
}

/* フローティングチャットボタンのスタイル */
.floating-chat-button {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%);
  color: white;
  border: none;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15), 0 4px 8px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.floating-chat-button:hover {
  transform: scale(1.1) translateY(-2px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2), 0 6px 12px rgba(0, 0, 0, 0.15);
  background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-700) 100%);
}

.floating-chat-button:active {
  transform: scale(1.05) translateY(-1px);
}

.chat-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 20px;
  height: 20px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 700;
  animation: pulse-badge 2s infinite;
}

@keyframes pulse-badge {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

/* カスタムツールチップスタイル */
:deep(.chat-tooltip) {
  background: linear-gradient(135deg, var(--gray-900) 0%, var(--gray-800) 100%) !important;
  color: white !important;
  border: 1px solid var(--gray-700) !important;
  border-radius: 12px !important;
  padding: 16px 20px !important;
  font-size: 0.9rem !important;
  font-weight: 500 !important;
  line-height: 1.6 !important;
  white-space: pre-line !important;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2), 0 4px 8px rgba(0, 0, 0, 0.1) !important;
  max-width: 300px !important;
  text-align: left !important;
  backdrop-filter: blur(8px) !important;
  letter-spacing: 0.02em !important;
}

:deep(.chat-tooltip .p-tooltip-arrow) {
  border-left-color: var(--gray-800) !important;
}

:deep(.chat-tooltip.p-tooltip-right .p-tooltip-arrow) {
  border-right-color: var(--gray-800) !important;
}

:deep(.chat-tooltip.p-tooltip-top .p-tooltip-arrow) {
  border-top-color: var(--gray-800) !important;
}

:deep(.chat-tooltip.p-tooltip-bottom .p-tooltip-arrow) {
  border-bottom-color: var(--gray-800) !important;
}

/* 新しいレイアウトのレスポンシブ対応 */
@media (max-width: 768px) {
  .floating-chat-button {
    bottom: 20px;
    right: 20px;
    width: 56px;
    height: 56px;
    font-size: 1.3rem;
  }
  
  .content-area {
    padding: 0 16px;
  }
  
  :deep(.chat-tooltip) {
    max-width: 260px !important;
    font-size: 0.85rem !important;
    padding: 14px 18px !important;
    line-height: 1.5 !important;
  }
}

/* 旧レイアウトのレスポンシブ対応（後方互換性のため残す） */
@media (max-width: 1200px) {
  .content-layout {
    grid-template-columns: 40% 60%;
    gap: 20px;
    padding: 0;
  }
  
  .left-column {
    padding-left: 16px;
  }
  
  .right-column {
    padding-right: 16px;
  }
  
  .minutes-main {
    gap: 18px;
    height: calc(100vh - 250px);
  }
  
  .minutes-header {
    margin: 0 16px 32px 16px;
  }
}

@media (max-width: 1024px) {
  .content-layout {
    grid-template-columns: 45% 55%;
    gap: 16px;
  }

  .left-column {
    padding-left: 16px;
  }

  .right-column {
    padding-right: 16px;
  }

  .transcript-scroll {
    height: 350px;
  }
  
  .minutes-main {
    gap: 16px;
    height: calc(100vh - 250px);
  }
  
  .minutes-header {
    margin: 0 16px 32px 16px;
  }
}

@media (max-width: 768px) {
  .minutes-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
    padding: 20px;
    margin: 0 16px 20px 16px;
  }

  .header-actions {
    justify-content: center;
  }

  .content-layout {
    display: block;
    padding: 0;
  }

  .left-column,
  .right-column {
    padding: 0 16px;
  }

  .transcript-sidebar {
    position: static;
    max-height: none;
    margin-bottom: 20px;
  }

  .minutes-title {
    font-size: 1.5rem;
  }

  .meeting-details-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-3);
  }

  .edit-actions {
    justify-content: center;
  }
  
  .minutes-main {
    gap: 16px;
    height: auto;
  }
  
  .meeting-details-card,
  .minutes-card {
    margin-bottom: 0;
    width: 100%;
    min-height: auto;
    max-height: none;
  }
  
  .meeting-details-card {
    min-height: 200px;
  }
  
  .minutes-card {
    min-height: 300px;
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
