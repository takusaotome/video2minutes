<template>
  <div class="chat-input-wrapper">
    <!-- 入力コンテナ -->
    <div class="input-container">
      <InputText
        v-model="currentMessage"
        :placeholder="placeholder"
        class="chat-input"
        @keyup.enter="handleSendMessage"
        :disabled="disabled"
        maxlength="2000"
      />
      <Button 
        icon="pi pi-send"
        class="send-button"
        @click="handleSendMessage"
        :disabled="disabled || !currentMessage.trim()"
        :loading="disabled"
      />
    </div>
    
    <!-- 文字数カウンター -->
    <div class="input-footer">
      <small class="char-counter" :class="{ 'warning': currentMessage.length > 1800 }">
        {{ currentMessage.length }}/2000
      </small>
      <small v-if="editMode" class="mode-indicator">
        <i class="pi pi-pencil"></i>
        編集モード
      </small>
      <small v-else class="mode-indicator">
        <i class="pi pi-question-circle"></i>
        質問モード
      </small>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

export default {
  name: 'ChatInput',
  components: {
    InputText,
    Button
  },
  props: {
    placeholder: {
      type: String,
      default: '質問を入力してください...'
    },
    disabled: {
      type: Boolean,
      default: false
    },
    editMode: {
      type: Boolean,
      default: false
    }
  },
  emits: ['send-message'],
  setup(props, { emit }) {
    const currentMessage = ref('')
    
    const handleSendMessage = () => {
      if (!currentMessage.value.trim() || props.disabled) return
      
      const message = currentMessage.value.trim()
      currentMessage.value = ''
      
      emit('send-message', message)
    }
    
    return {
      currentMessage,
      handleSendMessage
    }
  }
}
</script>

<style scoped>
.chat-input-wrapper {
  padding: 1rem;
  border-top: 1px solid var(--surface-border);
  background: var(--surface-card);
}

.input-container {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.chat-input {
  flex: 1;
  border-radius: 20px;
  padding: 0.75rem 1rem;
  border: 1px solid var(--surface-border);
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(var(--primary-color-rgb), 0.2);
}

.send-button {
  min-width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.char-counter {
  transition: color 0.2s;
}

.char-counter.warning {
  color: var(--orange-500);
  font-weight: 600;
}

.mode-indicator {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 12px;
  background: var(--surface-100);
}

.mode-indicator i {
  font-size: 0.7rem;
}

/* レスポンシブ対応 */
@media (max-width: 768px) {
  .chat-input-wrapper {
    padding: 0.75rem;
  }
  
  .input-container {
    gap: 0.25rem;
  }
  
  .chat-input {
    font-size: 0.9rem;
    padding: 0.6rem 0.8rem;
  }
  
  .send-button {
    min-width: 2.2rem;
    height: 2.2rem;
  }
  
  .input-footer {
    font-size: 0.75rem;
  }
}
</style>