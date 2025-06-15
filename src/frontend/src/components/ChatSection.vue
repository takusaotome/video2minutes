<template>
  <div class="chat-section">
    <!-- チャットメッセージエリア -->
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
            {{ message.response }}
            
            <!-- 引用箇所 -->
            <div v-if="message.citations && message.citations.length > 0" class="citations">
              <h5>参照箇所:</h5>
              <div 
                v-for="(citation, index) in message.citations"
                :key="index"
                class="citation-item"
                @click="$emit('citation-click', citation)"
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
      <div v-if="loading" class="loading-message">
        <ProgressSpinner size="small" />
        <span>{{ loadingText }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import Badge from 'primevue/badge'
import ProgressSpinner from 'primevue/progressspinner'

export default {
  name: 'ChatSection',
  components: {
    Badge,
    ProgressSpinner
  },
  props: {
    messages: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    loadingText: {
      type: String,
      default: '回答を生成中...'
    }
  },
  emits: ['citation-click'],
  setup(props, { emit }) {
    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit'
      })
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
    
    return {
      formatTime,
      getEditActionDescription
    }
  }
}
</script>

<style scoped>
.chat-section {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message-pair {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.user-message,
.assistant-message {
  padding: 0.75rem;
  border-radius: 8px;
  max-width: 90%;
}

.user-message {
  align-self: flex-end;
  background: var(--primary-color);
  color: var(--primary-color-text);
}

.assistant-message {
  align-self: flex-start;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
}

.message-content {
  margin-bottom: 0.5rem;
  white-space: pre-wrap;
  word-wrap: break-word;
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

/* レスポンシブ対応 */
@media (max-width: 768px) {
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
</style>