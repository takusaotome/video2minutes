<template>
  <div class="left-panel" :style="{ width: panelWidth }">
    <!-- 文字起こしセクション -->
    <div class="transcription-section" :style="{ height: transcriptionHeight }">
      <div class="section-header">
        <h4>
          <i class="pi pi-file-text"></i>
          文字起こし全文
        </h4>
        <Button 
          :icon="transcriptionCollapsed ? 'pi pi-chevron-down' : 'pi pi-chevron-up'"
          class="p-button-text p-button-sm"
          @click="toggleTranscriptionCollapse"
        />
      </div>
      
      <div v-if="!transcriptionCollapsed" class="transcription-content">
        <div 
          class="transcription-text" 
          ref="transcriptionContainer"
          @scroll="handleTranscriptionScroll"
        >
          <div 
            v-if="highlightedText" 
            class="highlighted-section"
            :class="{ 'fade-out': highlightFading }"
          >
            {{ highlightedText }}
          </div>
          <div class="transcription-full-text">
            {{ transcription || '文字起こし結果がありません。' }}
          </div>
        </div>
      </div>
    </div>
    
    <!-- リサイズハンドル -->
    <div 
      v-if="!transcriptionCollapsed && !chatCollapsed"
      class="resize-handle"
      @mousedown="startResize"
      @touchstart="startResize"
    >
      <div class="resize-line"></div>
      <i class="pi pi-grip-horizontal"></i>
    </div>
    
    <!-- チャットセクション -->
    <div class="chat-section" :style="{ height: chatHeight }">
      <div class="section-header" @click="toggleChatCollapse">
        <h4>
          <i class="pi pi-comments"></i>
          会議内容について質問
          <Badge 
            v-if="unreadMessages > 0 && chatCollapsed" 
            :value="unreadMessages" 
            severity="info"
          />
        </h4>
        <div class="header-actions">
          <!-- モード切替トグル -->
          <ToggleButton 
            v-if="!chatCollapsed"
            v-model="isEditMode"
            onLabel="編集"
            offLabel="質問"
            onIcon="pi pi-pencil"
            offIcon="pi pi-question-circle"
            class="mode-toggle"
            size="small"
          />
          <Button 
            :icon="chatCollapsed ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
            class="p-button-text p-button-sm"
          />
        </div>
      </div>
      
      <div v-if="!chatCollapsed" class="chat-content">
        <!-- チャット履歴 -->
        <div class="chat-messages" ref="messagesContainer">
          <div 
            v-for="message in messages" 
            :key="message.message_id"
            class="message-pair"
          >
            <!-- ユーザーメッセージ -->
            <div class="user-message">
              <div class="message-content">{{ message.message }}</div>
              <div class="message-meta">
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
                <Badge 
                  :value="message.intent === 'edit_request' ? '編集' : '質問'" 
                  :severity="message.intent === 'edit_request' ? 'warning' : 'info'"
                  size="small"
                />
              </div>
            </div>
            
            <!-- AI回答 -->
            <div class="assistant-message">
              <div class="message-content">
                <MarkdownRenderer
                  :content="message.response"
                  :show-toc="false"
                  class="chat-markdown"
                />
                
                <!-- 引用箇所 -->
                <div v-if="message.citations && message.citations.length > 0" class="citations">
                  <h5>参照箇所:</h5>
                  <div 
                    v-for="(citation, index) in message.citations"
                    :key="index"
                    class="citation-item"
                    @click="highlightTranscription(citation)"
                  >
                    <blockquote>{{ citation.text }}</blockquote>
                    <small v-if="citation.start_time">
                      時刻: {{ citation.start_time }}
                    </small>
                  </div>
                </div>
                
                <!-- 編集アクション表示 -->
                <div v-if="message.edit_actions && message.edit_actions.length > 0" class="edit-actions">
                  <h5>実行される編集:</h5>
                  <div 
                    v-for="(action, index) in message.edit_actions"
                    :key="index"
                    class="edit-action-item"
                  >
                    <Badge :value="action.action_type" severity="warning" />
                    <span>{{ getEditActionDescription(action) }}</span>
                  </div>
                </div>
              </div>
              <div class="message-meta">
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
                <small v-if="message.tokens_used">{{ message.tokens_used }} tokens</small>
              </div>
            </div>
          </div>
          
          <!-- ローディング -->
          <div v-if="isLoading" class="loading-message">
            <ProgressSpinner size="small" />
            <span>{{ isEditMode ? '編集内容を解析中...' : '回答を生成中...' }}</span>
          </div>
        </div>
        
        <!-- 入力エリア -->
        <div class="chat-input-area">
          <div class="input-container">
            <InputText
              v-model="currentMessage"
              :placeholder="isEditMode ? '議事録の編集指示を入力してください...' : '会議内容について質問してください...'"
              class="chat-input"
              @keydown.enter="handleChatKeyDown"
              @compositionstart="handleChatCompositionStart"
              @compositionend="handleChatCompositionEnd"
              :disabled="isLoading"
            />
            <Button 
              icon="pi pi-send"
              class="send-button"
              @click="handleSendMessage"
              :disabled="isLoading || !currentMessage.trim()"
            />
          </div>
          
          <!-- 使用状況表示 -->
          <div class="chat-usage">
            <small>
              質問: {{ questionCount }} | 編集: {{ editCount }} | トークン: {{ totalTokens }}
            </small>
          </div>
        </div>
        
        <!-- 編集履歴（編集モード時のみ） -->
        <div v-if="isEditMode && editHistory.length > 0" class="edit-history">
          <h5>編集履歴</h5>
          <div 
            v-for="edit in editHistory" 
            :key="edit.edit_id"
            class="edit-history-item"
            :class="{ 'reverted': edit.reverted }"
          >
            <div class="edit-summary">{{ edit.changes_summary.join(', ') }}</div>
            <div class="edit-actions">
              <small class="edit-time">{{ formatTime(edit.timestamp) }}</small>
              <Button 
                label="取り消し"
                class="p-button-text p-button-sm"
                @click="revertEdit(edit.edit_id)"
                :disabled="edit.reverted"
                v-if="!edit.reverted"
              />
              <span v-else class="reverted-label">取り消し済み</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import ToggleButton from 'primevue/togglebutton'
import InputText from 'primevue/inputtext'
import Badge from 'primevue/badge'
import ProgressSpinner from 'primevue/progressspinner'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { chatApi } from '@/services/api'

export default {
  name: 'LeftPanel',
  components: {
    Button,
    ToggleButton,
    InputText,
    Badge,
    ProgressSpinner,
    MarkdownRenderer
  },
  props: {
    transcription: {
      type: String,
      default: ''
    },
    minutes: {
      type: String,
      default: ''
    },
    taskId: {
      type: String,
      required: true
    },
    panelWidth: {
      type: String,
      default: '40%'
    }
  },
  emits: ['minutes-updated', 'panel-resize'],
  setup(props, { emit }) {
    // レイアウト状態
    const transcriptionHeight = ref('40px')  // 初期状態で閉じる
    const chatHeight = ref('calc(100% - 50px)')  // チャットエリアを拡大
    const transcriptionCollapsed = ref(true)  // 初期状態で閉じる
    const chatCollapsed = ref(false)
    
    // チャット状態
    const messages = ref([])
    const editHistory = ref([])
    const currentMessage = ref('')
    const isLoading = ref(false)
    const isEditMode = ref(false)
    const unreadMessages = ref(0)
    const totalTokens = ref(0)
    const currentSession = ref(null)
    const sessionInitialized = ref(false)
    
    // IME（日本語入力）の状態管理
    const isChatComposing = ref(false)
    
    // ハイライト状態
    const highlightedText = ref(null)
    const highlightFading = ref(false)
    
    // リサイズ状態
    const isResizing = ref(false)
    const startY = ref(0)
    const startTranscriptionHeight = ref(0)
    
    // 要素参照
    const transcriptionContainer = ref(null)
    const messagesContainer = ref(null)
    
    // 計算プロパティ
    const questionCount = computed(() => {
      return messages.value.filter(m => m.intent === 'question').length
    })
    
    const editCount = computed(() => {
      return messages.value.filter(m => m.intent === 'edit_request').length
    })
    
    // メソッド
    const toggleTranscriptionCollapse = () => {
      transcriptionCollapsed.value = !transcriptionCollapsed.value
      if (transcriptionCollapsed.value) {
        transcriptionHeight.value = '40px'
        chatHeight.value = 'calc(100% - 50px)'
      } else {
        transcriptionHeight.value = '35%'
        chatHeight.value = '65%'
      }
    }
    
    const toggleChatCollapse = () => {
      chatCollapsed.value = !chatCollapsed.value
      if (chatCollapsed.value) {
        chatHeight.value = '40px'
        transcriptionHeight.value = 'calc(100% - 50px)'
        unreadMessages.value = 0
      } else {
        // 文字起こしの現在の状態に応じて調整
        if (transcriptionCollapsed.value) {
          transcriptionHeight.value = '40px'
          chatHeight.value = 'calc(100% - 50px)'
        } else {
          transcriptionHeight.value = '35%'
          chatHeight.value = '65%'
        }
      }
    }
    
    const startResize = (event) => {
      isResizing.value = true
      startY.value = event.clientY || event.touches[0].clientY
      startTranscriptionHeight.value = transcriptionContainer.value?.offsetHeight || 0
      
      document.addEventListener('mousemove', handleResize)
      document.addEventListener('mouseup', stopResize)
      document.addEventListener('touchmove', handleResize)
      document.addEventListener('touchend', stopResize)
    }
    
    const handleResize = (event) => {
      if (!isResizing.value) return
      
      const currentY = event.clientY || event.touches[0].clientY
      const deltaY = currentY - startY.value
      const newHeight = startTranscriptionHeight.value + deltaY
      const totalHeight = transcriptionContainer.value?.parentElement?.offsetHeight || 600
      
      const minHeight = 200
      const maxHeight = totalHeight - 200
      
      if (newHeight >= minHeight && newHeight <= maxHeight) {
        const transcriptionRatio = newHeight / totalHeight
        const chatRatio = 1 - transcriptionRatio
        
        transcriptionHeight.value = `${transcriptionRatio * 100}%`
        chatHeight.value = `${chatRatio * 100}%`
      }
    }
    
    const stopResize = () => {
      isResizing.value = false
      document.removeEventListener('mousemove', handleResize)
      document.removeEventListener('mouseup', stopResize)
      document.removeEventListener('touchmove', handleResize)
      document.removeEventListener('touchend', stopResize)
    }
    
    const highlightTranscription = (citation) => {
      highlightedText.value = citation.text
      highlightFading.value = false
      
      // 3秒後にフェードアウト開始
      setTimeout(() => {
        highlightFading.value = true
        setTimeout(() => {
          highlightedText.value = null
          highlightFading.value = false
        }, 500)
      }, 3000)
      
      // TODO: 文字起こしの該当箇所にスクロール
      scrollToHighlightedText(citation.text)
    }
    
    const scrollToHighlightedText = (text) => {
      if (!transcriptionContainer.value) return
      
      // 簡易的な実装：後で改善
      transcriptionContainer.value.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
      })
    }
    
    const handleSendMessage = async () => {
      if (!currentMessage.value.trim() || isLoading.value) return
      
      const message = currentMessage.value.trim()
      const intent = isEditMode.value ? 'edit_request' : 'question'
      
      currentMessage.value = ''
      isLoading.value = true
      
      try {
        // セッションが初期化されていない場合は作成
        if (!sessionInitialized.value) {
          await initializeChatSession()
        }
        
        // メッセージを送信
        await sendMessage(message, intent)
      } catch (error) {
        console.error('メッセージ送信エラー:', error)
        // エラーメッセージを表示
        const errorMessage = {
          message_id: `error_${Date.now()}`,
          message: message,
          response: `申し訳ございません。メッセージの送信中にエラーが発生しました: ${error.message}`,
          intent: intent,
          timestamp: new Date(),
          citations: [],
          edit_actions: [],
          tokens_used: 0,
          is_error: true
        }
        messages.value.push(errorMessage)
      } finally {
        isLoading.value = false
      }
    }
    
    // セッション初期化
    const initializeChatSession = async () => {
      try {
        console.log('チャットセッションを初期化中...')
        const response = await chatApi.createSession(
          props.taskId,
          props.transcription,
          props.minutes
        )
        
        currentSession.value = response.data
        sessionInitialized.value = true
        console.log('チャットセッション初期化完了:', currentSession.value.session_id)
      } catch (error) {
        console.error('セッション初期化エラー:', error)
        throw new Error('チャットセッションの初期化に失敗しました')
      }
    }
    
    // メッセージ送信
    const sendMessage = async (message, intent) => {
      try {
        console.log('メッセージ送信中:', message, intent)
        const response = await chatApi.sendMessage(
          props.taskId,
          currentSession.value.session_id,
          message,
          intent
        )
        
        const messageData = response.data
        console.log('API回答受信:', messageData)
        
        // メッセージをUI用の形式に変換
        const newMessage = {
          message_id: messageData.message_id,
          message: message,
          response: messageData.response,
          intent: intent,
          timestamp: messageData.timestamp ? new Date(messageData.timestamp) : new Date(),
          citations: messageData.citations || [],
          edit_actions: messageData.edit_actions || [],
          tokens_used: messageData.tokens_used || 0
        }
        
        messages.value.push(newMessage)
        totalTokens.value += newMessage.tokens_used
        
        if (chatCollapsed.value) {
          unreadMessages.value++
        }
        
        // 編集アクションがある場合は議事録を更新
        if (messageData.updated_minutes) {
          emit('minutes-updated', messageData.updated_minutes)
        }
        
        // メッセージエリアを最下部にスクロール
        setTimeout(() => {
          if (messagesContainer.value) {
            messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
          }
        }, 100)
        
        return newMessage
      } catch (error) {
        console.error('メッセージ送信API呼び出しエラー:', error)
        throw error
      }
    }
    
    const formatTime = (timestamp) => {
      try {
        const date = new Date(timestamp)
        if (isNaN(date.getTime())) {
          return '--:--'
        }
        return date.toLocaleTimeString('ja-JP', {
          hour: '2-digit',
          minute: '2-digit'
        })
      } catch (error) {
        console.warn('日付フォーマットエラー:', timestamp, error)
        return '--:--'
      }
    }
    
    const getEditActionDescription = (action) => {
      switch (action.action_type) {
        case 'replace_text':
          return `「${action.target}」を「${action.replacement}」に置換`
        case 'add_action_item':
          return `アクションアイテム追加: ${action.content?.task || ''}`
        case 'update_action_item':
          return `アクションアイテム更新`
        default:
          return action.action_type
      }
    }
    
    const revertEdit = async (editId) => {
      try {
        // TODO: API実装後に実際の処理に置き換え
        const editIndex = editHistory.value.findIndex(e => e.edit_id === editId)
        if (editIndex !== -1) {
          editHistory.value[editIndex].reverted = true
        }
        
        // TODO: トースト表示
        console.log('編集を取り消しました')
      } catch (error) {
        console.error('編集取り消しエラー:', error)
      }
    }
    
    const handleTranscriptionScroll = () => {
      // TODO: スクロール位置の保存や連携機能
    }
    
    // IME（日本語入力）のハンドリング
    const handleChatCompositionStart = () => {
      isChatComposing.value = true
    }
    
    const handleChatCompositionEnd = () => {
      isChatComposing.value = false
    }
    
    const handleChatKeyDown = (event) => {
      // IME変換中の場合は何もしない
      if (isChatComposing.value) {
        return
      }
      
      // Enterキーが押された場合のみ送信
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        handleSendMessage()
      }
    }
    
    // ウォッチャー
    watch(chatCollapsed, (newValue) => {
      if (!newValue) {
        unreadMessages.value = 0
      }
    })
    
    return {
      // 状態
      transcriptionHeight,
      chatHeight,
      transcriptionCollapsed,
      chatCollapsed,
      messages,
      editHistory,
      currentMessage,
      isLoading,
      isEditMode,
      unreadMessages,
      totalTokens,
      highlightedText,
      highlightFading,
      
      // 要素参照
      transcriptionContainer,
      messagesContainer,
      
      // 計算プロパティ
      questionCount,
      editCount,
      
      // メソッド
      toggleTranscriptionCollapse,
      toggleChatCollapse,
      startResize,
      highlightTranscription,
      handleSendMessage,
      handleChatCompositionStart,
      handleChatCompositionEnd,
      handleChatKeyDown,
      formatTime,
      getEditActionDescription,
      revertEdit,
      handleTranscriptionScroll
    }
  }
}
</script>

<style scoped>
.left-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--surface-border);
  background: var(--surface-ground);
}

.transcription-section {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--surface-ground);
  border-radius: 8px;
  border: 1px solid var(--surface-border);
}

.chat-section {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 450px;
  background: var(--surface-ground);
  border-radius: 8px;
  border: 1px solid var(--surface-border);
  margin-top: 16px; /* 文字起こしとの間に十分な余白 */
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
  cursor: pointer;
  transition: background-color 0.2s;
}

.section-header:hover {
  background: var(--surface-hover);
}

.section-header h4 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-color);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.mode-toggle {
  font-size: 0.8rem;
  height: 2rem;
  min-width: 4.5rem;
}

/* 最強力なセレクターで質問ボタンの文字色を強制 */
.mode-toggle.mode-toggle :deep(.p-component.p-togglebutton[data-p-highlight="false"] .p-button.p-component) {
  color: #000000 !important;
  background: #ffffff !important;
  border-color: var(--gray-400) !important;
  height: 2rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 700 !important;
}

.mode-toggle.mode-toggle :deep(.p-component.p-togglebutton[data-p-highlight="false"] .p-button.p-component .p-button-label) {
  color: #000000 !important;
  font-weight: 700 !important;
}

.mode-toggle.mode-toggle :deep(.p-component.p-togglebutton[data-p-highlight="false"] .p-button.p-component .p-button-icon) {
  color: #000000 !important;
}

/* さらに詳細なセレクター */
.mode-toggle :deep(.p-togglebutton[data-p-highlight="false"] .p-button[data-pc-section="box"]) {
  color: #000000 !important;
  background: #ffffff !important;
}

.mode-toggle :deep(.p-togglebutton[data-p-highlight="false"] .p-button[data-pc-section="box"] .p-button-label[data-pc-section="label"]) {
  color: #000000 !important;
}

.mode-toggle :deep(.p-togglebutton[data-p-highlight="false"] .p-button[data-pc-section="box"] .p-button-icon[data-pc-section="icon"]) {
  color: #000000 !important;
}

/* 全てのスタイルの集約 - 最終手段 */
.mode-toggle :deep(*) {
  --text-color: #000000 !important;
  --surface-0: #ffffff !important;
}

.mode-toggle :deep(.p-button-label),
.mode-toggle :deep(.p-button-icon) {
  color: #000000 !important;
  fill: #000000 !important;
}

/* ホバー状態 */
.mode-toggle :deep(.p-togglebutton:not([data-p-highlight="true"]):hover .p-button) {
  background: var(--gray-100) !important;
  border-color: var(--gray-500);
  color: #000000 !important;
}

.mode-toggle :deep(.p-togglebutton:not([data-p-highlight="true"]):hover .p-button .p-button-label) {
  color: #000000 !important;
}

.mode-toggle :deep(.p-togglebutton:not([data-p-highlight="true"]):hover .p-button .p-button-icon) {
  color: #000000 !important;
}

.mode-toggle :deep(.p-button.p-highlight) {
  background: var(--primary-600);
  border-color: var(--primary-600);
  color: white;
  font-weight: 600;
}

.mode-toggle :deep(.p-button.p-highlight:hover) {
  background: var(--primary-700);
  border-color: var(--primary-700);
  color: white;
}

.mode-toggle :deep(.p-togglebutton-label) {
  font-weight: 500;
  color: inherit;
}

.transcription-content,
.chat-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 350px;
  height: 100%;
}

.transcription-text {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  line-height: 1.6;
  color: var(--text-color);
}

.highlighted-section {
  background: var(--yellow-100);
  border: 2px solid var(--yellow-300);
  padding: 0.5rem;
  margin-bottom: 1rem;
  border-radius: 6px;
  transition: opacity 0.5s;
}

.highlighted-section.fade-out {
  opacity: 0;
}

.transcription-full-text {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.resize-handle {
  height: 8px;
  background: var(--surface-border);
  cursor: ns-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.resize-handle:hover {
  background: var(--primary-color);
}

.resize-line {
  width: 60px;
  height: 2px;
  background: var(--surface-400);
  border-radius: 1px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 300px;
  height: 100%;
}

.message-pair {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  margin-bottom: 1.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--surface-border);
}

.message-pair:last-child {
  border-bottom: none;
  margin-bottom: 1rem;
}

.user-message,
.assistant-message {
  padding: 0.875rem;
  border-radius: 12px;
  max-width: 95%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 0.25rem;
}

.user-message {
  align-self: flex-end;
  background: var(--primary-color);
  color: var(--primary-color-text);
  border-bottom-right-radius: 4px;
}

.assistant-message {
  align-self: flex-start;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-bottom-left-radius: 4px;
}

.message-content {
  margin-bottom: 0.5rem;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.5;
  font-size: 0.95rem;
}

.message-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  opacity: 0.7;
}

.citations {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.citations h5 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.citation-item {
  margin-bottom: 0.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.citation-item:hover {
  background: var(--surface-hover);
}

.citation-item blockquote {
  margin: 0 0 0.25rem 0;
  padding: 0.5rem;
  background: var(--surface-100);
  border-left: 3px solid var(--primary-color);
  font-style: italic;
}

.edit-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.edit-actions h5 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.edit-action-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.loading-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
  padding: 1rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.chat-input-area {
  padding: 1.25rem;
  border-top: 2px solid var(--surface-border);
  background: var(--surface-card);
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.08);
  border-radius: 0 0 8px 8px;
}

.input-container {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  min-height: 2.5rem;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}

/* PrimeVueのInputTextコンポーネント用の詳細スタイル */
.input-container :deep(.p-inputtext),
.input-container :deep(input[type="text"]) {
  padding: 12px 16px !important;
  border-radius: 8px !important;
  border: 1px solid var(--surface-border) !important;
  font-size: 0.95rem !important;
  width: 100% !important;
  box-sizing: border-box !important;
  min-height: 2.5rem !important;
  text-indent: 0 !important;
  padding-left: 16px !important;
}

/* プレースホルダーのスタイリング - より具体的なセレクター */
.input-container :deep(input::placeholder),
.input-container :deep(.p-inputtext::placeholder) {
  color: var(--text-color-secondary) !important;
  padding-left: 0 !important;
  text-indent: 0 !important;
  opacity: 1 !important;
}

.input-container :deep(input::-webkit-input-placeholder) {
  color: var(--text-color-secondary) !important;
  padding-left: 0 !important;
  text-indent: 0 !important;
  opacity: 1 !important;
}

.input-container :deep(input::-moz-placeholder) {
  color: var(--text-color-secondary) !important;
  padding-left: 0 !important;
  text-indent: 0 !important;
  opacity: 1 !important;
}

.input-container :deep(input:-ms-input-placeholder) {
  color: var(--text-color-secondary) !important;
  padding-left: 0 !important;
  text-indent: 0 !important;
  opacity: 1 !important;
}

.send-button {
  min-width: 2.75rem;
  height: 2.5rem;
}

/* グローバルスタイルで確実に適用 */
:global(.chat-input-area .p-inputtext) {
  padding: 12px 16px !important;
  text-indent: 0 !important;
}

:global(.chat-input-area .p-inputtext::placeholder) {
  padding-left: 0 !important;
  text-indent: 0 !important;
  color: var(--text-color-secondary) !important;
}

:global(.chat-input-area input::placeholder) {
  padding-left: 0 !important;
  text-indent: 0 !important;
  color: var(--text-color-secondary) !important;
}

.chat-usage {
  text-align: center;
  color: var(--text-color-secondary);
}

.edit-history {
  padding: 1rem;
  border-top: 1px solid var(--surface-border);
  background: var(--surface-50);
}

.edit-history h5 {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.edit-history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  margin-bottom: 0.5rem;
  background: var(--surface-card);
  border-radius: 6px;
  border: 1px solid var(--surface-border);
}

.edit-history-item.reverted {
  opacity: 0.6;
  background: var(--surface-100);
}

.edit-summary {
  flex: 1;
  font-size: 0.9rem;
}

.edit-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.edit-time {
  color: var(--text-color-secondary);
}

.reverted-label {
  color: var(--text-color-secondary);
  font-style: italic;
}

/* レスポンシブ対応 */
@media (max-width: 768px) {
  .left-panel {
    width: 100% !important;
  }
  
  .section-header h4 {
    font-size: 0.9rem;
  }
  
  .transcription-text,
  .chat-messages {
    padding: 0.5rem;
  }
  
  .message-pair {
    gap: 0.25rem;
  }
  
  .user-message,
  .assistant-message {
    padding: 0.5rem;
    max-width: 95%;
  }
}

/* Markdown renderer styling for chat messages */
.chat-markdown :deep(.markdown-content) {
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--gray-700);
  background: transparent !important;
  padding: 0 !important;
  margin: 0 !important;
}

.chat-markdown :deep(.markdown-renderer) {
  background: transparent !important;
  padding: 0 !important;
  margin: 0 !important;
}

.chat-markdown :deep(.markdown-content-wrapper) {
  background: transparent !important;
  padding: 0 !important;
  margin: 0 !important;
}

.chat-markdown :deep(.p-card.markdown-card) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

.chat-markdown :deep(.p-card-body) {
  background: transparent !important;
  padding: 0 !important;
  margin: 0 !important;
}

.chat-markdown :deep(.p-card-content) {
  background: transparent !important;
  padding: 0 !important;
  margin: 0 !important;
}

.chat-markdown :deep(.markdown-content h1),
.chat-markdown :deep(.markdown-content h2),
.chat-markdown :deep(.markdown-content h3),
.chat-markdown :deep(.markdown-content h4),
.chat-markdown :deep(.markdown-content h5),
.chat-markdown :deep(.markdown-content h6) {
  font-size: 1rem;
  font-weight: 600;
  color: var(--gray-800);
  margin: 0.5rem 0 0.25rem 0;
  line-height: 1.3;
}

.chat-markdown :deep(.markdown-content p) {
  margin: 0 0 0.5rem 0;
  color: var(--gray-700);
}

.chat-markdown :deep(.markdown-content ul),
.chat-markdown :deep(.markdown-content ol) {
  margin: 0.25rem 0 0.5rem 1rem;
  padding-left: 0.5rem;
}

.chat-markdown :deep(.markdown-content li) {
  margin: 0.125rem 0;
  color: var(--gray-700);
}

.chat-markdown :deep(.markdown-content strong) {
  font-weight: 600;
  color: var(--gray-800);
}

.chat-markdown :deep(.markdown-content em) {
  font-style: italic;
  color: var(--gray-600);
}

.chat-markdown :deep(.markdown-content code) {
  background: var(--gray-100);
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
}

.chat-markdown :deep(.markdown-content pre) {
  background: var(--gray-100);
  padding: 0.5rem;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.5rem 0;
  font-size: 0.85rem;
}

.chat-markdown :deep(.markdown-content blockquote) {
  border-left: 3px solid var(--primary-300);
  padding-left: 0.75rem;
  margin: 0.5rem 0;
  color: var(--gray-600);
  font-style: italic;
}

.chat-markdown :deep(.markdown-content table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.chat-markdown :deep(.markdown-content th),
.chat-markdown :deep(.markdown-content td) {
  border: 1px solid var(--gray-300);
  padding: 0.25rem 0.5rem;
  text-align: left;
}

.chat-markdown :deep(.markdown-content th) {
  background: var(--gray-50);
  font-weight: 600;
}
</style>