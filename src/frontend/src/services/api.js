import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 300000, // 5 minutes timeout for long processing
  withCredentials: true, // セッションCookieを自動送信
  headers: {
    'Content-Type': 'application/json'
  }
})

// APIキー設定
const API_KEY = import.meta.env.VITE_API_KEY

// デバッグ用ログ
console.log('API_KEY loaded:', API_KEY ? `${API_KEY.substring(0, 8)}...` : 'Not set')

// APIキーが設定されている場合は認証ヘッダーを追加
if (API_KEY) {
  api.defaults.headers.common['Authorization'] = `Bearer ${API_KEY}`
  console.log('Authorization header set')
} else {
  console.warn('API_KEY not found in environment variables')
}

// Request interceptor
api.interceptors.request.use(
  config => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    console.log('Request headers:', config.headers)
    return config
  },
  error => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  response => {
    console.log(`API Response: ${response.status} ${response.config.url}`)
    return response
  },
  error => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const minutesApi = {
  // Upload video file
  uploadVideo: async (file, onUploadProgress) => {
    const formData = new FormData()
    formData.append('file', file) // FastAPIの期待するパラメーター名に変更

    return api.post('/minutes/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress
    })
  },

  // Get all tasks
  getTasks: async () => {
    return api.get('/minutes/tasks')
  },

  // Get task status
  getTaskStatus: async taskId => {
    return api.get(`/minutes/${taskId}/status`)
  },

  // Get task result
  getTaskResult: async taskId => {
    return api.get(`/minutes/${taskId}/result`)
  },

  // Delete task
  deleteTask: async taskId => {
    return api.delete(`/minutes/${taskId}`)
  },

  // Retry failed task
  retryTask: async taskId => {
    return api.post(`/minutes/${taskId}/retry`)
  },

  // Regenerate minutes from transcription
  regenerateMinutes: async taskId => {
    return api.post(`/minutes/${taskId}/regenerate`)
  }
}

export const chatApi = {
  // Create chat session
  createSession: async (taskId, transcription, minutes) => {
    return api.post(`/minutes/${taskId}/chat/sessions`, {
      transcription,
      minutes
    })
  },

  // Get chat sessions
  getSessions: async (taskId) => {
    return api.get(`/minutes/${taskId}/chat/sessions`)
  },

  // Send message
  sendMessage: async (taskId, sessionId, message, intent = 'question') => {
    return api.post(`/minutes/${taskId}/chat/sessions/${sessionId}/messages`, {
      message,
      intent
    })
  },

  // Get chat history
  getChatHistory: async (taskId, sessionId) => {
    return api.get(`/minutes/${taskId}/chat/sessions/${sessionId}/messages`)
  },

  // Execute edit
  executeEdit: async (taskId, sessionId, messageId) => {
    return api.post(`/minutes/${taskId}/chat/sessions/${sessionId}/messages/${messageId}/execute`)
  },

  // Get edit history
  getEditHistory: async (taskId) => {
    return api.get(`/minutes/${taskId}/chat/edit-history`)
  },

  // Undo edit
  undoEdit: async (taskId, editId) => {
    return api.post(`/minutes/${taskId}/chat/edit-history/${editId}/undo`)
  }
}

export default api
