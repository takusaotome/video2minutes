import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 300000, // 5 minutes timeout for long processing
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  config => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
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
    formData.append('file', file)  // FastAPIの期待するパラメーター名に変更
    
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
  getTaskStatus: async (taskId) => {
    return api.get(`/minutes/${taskId}/status`)
  },

  // Get task result
  getTaskResult: async (taskId) => {
    return api.get(`/minutes/${taskId}/result`)
  },

  // Delete task
  deleteTask: async (taskId) => {
    return api.delete(`/minutes/${taskId}`)
  },

  // Retry failed task
  retryTask: async (taskId) => {
    return api.post(`/minutes/${taskId}/retry`)
  }
}

export default api