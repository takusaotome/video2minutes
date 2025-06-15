<template>
  <div class="floating-chat-container" :class="{ 'chat-open': isOpen, 'chat-maximized': isMaximized }">
    <!-- Chat Panel -->
    <div class="floating-chat-panel" v-if="isOpen">
      <div class="chat-panel-header">
        <h3>
          <i class="pi pi-comments"></i>
          会議内容について質問
        </h3>
        <div class="header-actions">
          <Button
            :icon="isMaximized ? 'pi pi-window-minimize' : 'pi pi-window-maximize'"
            @click="toggleMaximize"
            class="p-button-text p-button-rounded p-button-sm"
          />
          <Button
            icon="pi pi-times"
            @click="close"
            class="p-button-text p-button-rounded p-button-sm"
          />
        </div>
      </div>
      
      <div class="chat-panel-body">
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
                    @click="$emit('highlight-citation', citation)"
                  >
                    <blockquote>{{ citation.text }}</blockquote>
                    <small v-if="citation.start_time">
                      時刻: {{ citation.start_time }}
                    </small>
                  </div>
                </div>
              </div>
              <div class="message-meta">
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
              </div>
            </div>
          </div>
          
          <!-- ローディング -->
          <div v-if="isLoading" class="loading-message">
            <ProgressSpinner size="small" />
            <span>回答を生成中...</span>
          </div>
        </div>
        
        <!-- 入力エリア -->
        <div class="chat-input-area">
          <div class="input-container">
            <InputText
              v-model="currentMessage"
              placeholder="会議内容について質問してください..."
              class="chat-input"
              @keydown.enter="handleKeyDown"
              @compositionstart="handleCompositionStart"
              @compositionend="handleCompositionEnd"
              :disabled="isLoading"
            />
            <Button 
              icon="pi pi-send"
              class="send-button"
              @click="sendMessage"
              :disabled="isLoading || !currentMessage.trim()"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, nextTick, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { chatApi } from '@/services/api'

export default {
  name: 'FloatingChat',
  components: {
    Button,
    InputText,
    ProgressSpinner,
    MarkdownRenderer
  },
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    taskId: {
      type: String,
      required: true
    },
    transcription: {
      type: String,
      default: ''
    },
    minutes: {
      type: String,
      default: ''
    }
  },
  emits: ['close', 'update-unread', 'highlight-citation'],
  setup(props, { emit }) {
    const messages = ref([])
    const currentMessage = ref('')
    const isLoading = ref(false)
    const messagesContainer = ref(null)
    const currentSession = ref(null)
    const sessionInitialized = ref(false)
    
    // IME（日本語入力）の状態管理
    const isComposing = ref(false)
    
    // 最大化状態管理
    const isMaximized = ref(false)
    
    // セッション初期化
    const initializeChatSession = async () => {
      if (!props.taskId) {
        throw new Error('タスクIDが設定されていません')
      }
      
      try {
        console.log('フローティングチャット: セッション初期化中...')
        const response = await chatApi.createSession(
          props.taskId,
          props.transcription || '',
          props.minutes || ''
        )
        
        currentSession.value = response.data
        sessionInitialized.value = true
        console.log('フローティングチャット: セッション初期化完了', currentSession.value.session_id)
      } catch (error) {
        console.error('セッション初期化エラー:', error)
        throw new Error('チャットセッションの初期化に失敗しました')
      }
    }
    
    // メッセージ送信
    const sendMessage = async () => {
      if (!currentMessage.value.trim() || isLoading.value) return
      
      const message = currentMessage.value.trim()
      currentMessage.value = ''
      isLoading.value = true
      
      try {
        // セッションが初期化されていない場合は作成
        if (!sessionInitialized.value) {
          await initializeChatSession()
        }
        
        // メッセージを送信
        if (!currentSession.value?.session_id) {
          throw new Error('セッションが初期化されていません')
        }
        
        const response = await chatApi.sendMessage(
          props.taskId,
          currentSession.value.session_id,
          message,
          'question'
        )
        
        const messageData = response.data
        
        // メッセージを追加
        const newMessage = {
          message_id: messageData.message_id,
          message: message,
          response: messageData.response,
          timestamp: messageData.timestamp ? new Date(messageData.timestamp) : new Date(),
          citations: messageData.citations || []
        }
        
        messages.value.push(newMessage)
        
        // スクロール
        await nextTick()
        scrollToBottom()
        
      } catch (error) {
        console.error('メッセージ送信エラー:', error)
        // エラーメッセージを表示
        const errorMessage = {
          message_id: `error_${Date.now()}`,
          message: message,
          response: `申し訳ございません。メッセージの送信中にエラーが発生しました: ${error.message}`,
          timestamp: new Date(),
          citations: [],
          is_error: true
        }
        messages.value.push(errorMessage)
      } finally {
        isLoading.value = false
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
    
    const scrollToBottom = () => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    }
    
    // IME（日本語入力）のハンドリング
    const handleCompositionStart = () => {
      isComposing.value = true
    }
    
    const handleCompositionEnd = () => {
      isComposing.value = false
    }
    
    const handleKeyDown = (event) => {
      // IME変換中の場合は何もしない
      if (isComposing.value) {
        return
      }
      
      // Enterキーが押された場合のみ送信
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        sendMessage()
      }
    }
    
    const close = () => {
      isMaximized.value = false
      emit('close')
    }
    
    const toggleMaximize = () => {
      isMaximized.value = !isMaximized.value
    }
    
    // パネルが開かれたときにセッションを初期化
    watch(() => props.isOpen, async (newValue) => {
      if (newValue && !sessionInitialized.value && props.taskId) {
        try {
          await initializeChatSession()
        } catch (error) {
          console.error('セッション初期化エラー:', error)
        }
      }
      
      // パネルが閉じられた時は最大化状態もリセット
      if (!newValue) {
        isMaximized.value = false
      }
    })
    
    return {
      messages,
      currentMessage,
      isLoading,
      messagesContainer,
      isMaximized,
      sendMessage,
      formatTime,
      handleCompositionStart,
      handleCompositionEnd,
      handleKeyDown,
      close,
      toggleMaximize
    }
  }
}
</script>

<style scoped>
.floating-chat-container {
  position: fixed;
  bottom: 100px;
  right: 30px;
  z-index: 1001;
}

.floating-chat-panel {
  width: 400px;
  height: 600px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  animation: slideUp 0.3s ease-out;
  transition: all 0.3s ease-out;
}

/* 最大化時のスタイル */
.chat-maximized {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1002;
}

.chat-maximized .floating-chat-panel {
  width: calc(100vw - 40px);
  height: calc(100vh - 40px);
  top: 20px;
  right: 20px;
  bottom: 20px;
  left: 20px;
  position: fixed;
  z-index: 1002;
  max-width: none;
  max-height: none;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* 最大化時の背景オーバーレイ */
.chat-maximized::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1001;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.chat-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--gray-200);
  border-radius: 12px 12px 0 0;
  background: var(--primary-50);
}

.chat-panel-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--gray-800);
}

.chat-panel-header i {
  color: var(--primary-500);
}

.header-actions {
  display: flex;
  gap: 4px;
}

.chat-panel-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-pair {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-message,
.assistant-message {
  padding: 12px 16px;
  border-radius: 12px;
  max-width: 85%;
}

.user-message {
  align-self: flex-end;
  background: var(--primary-500);
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant-message {
  align-self: flex-start;
  background: var(--gray-100);
  border-bottom-left-radius: 4px;
}

.message-content {
  font-size: 0.95rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message-meta {
  margin-top: 4px;
  font-size: 0.75rem;
  opacity: 0.7;
}

.citations {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--gray-300);
}

.citations h5 {
  margin: 0 0 8px 0;
  font-size: 0.85rem;
  color: var(--gray-700);
}

.citation-item {
  margin-bottom: 8px;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.citation-item:hover {
  background: var(--gray-200);
}

.citation-item blockquote {
  margin: 0 0 4px 0;
  padding: 4px 0 4px 12px;
  border-left: 3px solid var(--primary-300);
  font-size: 0.85rem;
  font-style: italic;
}

.citation-item small {
  color: var(--gray-600);
  font-size: 0.75rem;
}

.loading-message {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 16px;
  color: var(--gray-600);
}

.chat-input-area {
  padding: 16px;
  border-top: 1px solid var(--gray-200);
  background: var(--gray-50);
}

.input-container {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}

/* PrimeVueのInputTextコンポーネント用の詳細スタイル */
.input-container :deep(.p-inputtext),
.input-container :deep(input[type="text"]) {
  padding: 12px 16px !important;
  border-radius: 8px !important;
  border: 1px solid var(--gray-300) !important;
  font-size: 0.95rem !important;
  width: 100% !important;
  box-sizing: border-box !important;
  text-indent: 0 !important;
  padding-left: 16px !important;
}

/* プレースホルダーのスタイリング - より具体的なセレクター */
.input-container :deep(input::placeholder),
.input-container :deep(.p-inputtext::placeholder) {
  color: var(--gray-500) !important;
  padding-left: 0 !important;
  text-indent: 0 !important;
  opacity: 1 !important;
}

.input-container :deep(input::-webkit-input-placeholder) {
  color: var(--gray-500) !important;
  padding-left: 0 !important;
  text-indent: 0 !important;
  opacity: 1 !important;
}

.input-container :deep(input::-moz-placeholder) {
  color: var(--gray-500) !important;
  padding-left: 0 !important;
  text-indent: 0 !important;
  opacity: 1 !important;
}

.input-container :deep(input:-ms-input-placeholder) {
  color: var(--gray-500) !important;
  padding-left: 0 !important;
  text-indent: 0 !important;
  opacity: 1 !important;
}

.send-button {
  flex-shrink: 0;
}

/* グローバルスタイルで確実に適用 */
:global(.chat-input-area .p-inputtext) {
  padding: 12px 16px !important;
  text-indent: 0 !important;
}

:global(.chat-input-area .p-inputtext::placeholder) {
  padding-left: 0 !important;
  text-indent: 0 !important;
  color: var(--gray-500) !important;
}

:global(.chat-input-area input::placeholder) {
  padding-left: 0 !important;
  text-indent: 0 !important;
  color: var(--gray-500) !important;
}

/* レスポンシブ対応 */
@media (max-width: 768px) {
  .floating-chat-panel {
    width: calc(100vw - 20px);
    height: calc(100vh - 120px);
    right: 10px;
    bottom: 10px;
  }
  
  .floating-chat-container {
    right: 0;
    bottom: 0;
  }
  
  /* モバイルでの最大化時 */
  .chat-maximized .floating-chat-panel {
    width: calc(100vw - 20px);
    height: calc(100vh - 20px);
    top: 10px;
    right: 10px;
    bottom: 10px;
    left: 10px;
    border-radius: 12px;
  }
}

/* スクロールバーのスタイル */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: var(--gray-100);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--gray-400);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: var(--gray-500);
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