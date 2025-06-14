import { defineStore } from 'pinia'
import { minutesApi } from '@/services/api'
import websocketManager from '@/services/websocket'

export const useTasksStore = defineStore('tasks', {
  state: () => ({
    tasks: [],
    loading: false,
    error: null,
    pollingInterval: null,
    activeConnections: new Set()
  }),

  getters: {
    getTaskById: (state) => (id) => {
      return state.tasks.find(task => task.task_id === id)
    },

    pendingTasks: (state) => {
      return state.tasks.filter(task => task.status === 'pending')
    },

    processingTasks: (state) => {
      return state.tasks.filter(task => task.status === 'processing')
    },

    completedTasks: (state) => {
      return state.tasks.filter(task => task.status === 'completed')
    },

    failedTasks: (state) => {
      return state.tasks.filter(task => task.status === 'failed')
    },

    taskStats: (state) => {
      return {
        total: state.tasks.length,
        pending: state.tasks.filter(t => t.status === 'pending').length,
        processing: state.tasks.filter(t => t.status === 'processing').length,
        completed: state.tasks.filter(t => t.status === 'completed').length,
        failed: state.tasks.filter(t => t.status === 'failed').length
      }
    }
  },

  actions: {
    async fetchTasks() {
      try {
        this.loading = true
        this.error = null
        const response = await minutesApi.getTasks()
        this.tasks = response.data.tasks || response.data
      } catch (error) {
        this.error = error.response?.data?.message || error.message
        console.error('Failed to fetch tasks:', error)
      } finally {
        this.loading = false
      }
    },

    async uploadFile(file, onProgress) {
      try {
        this.loading = true
        this.error = null
        
        const response = await minutesApi.uploadVideo(file, (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress?.(percentCompleted)
        })

        const uploadResult = response.data
        
        // Fetch the complete task information
        try {
          const taskStatusResponse = await minutesApi.getTaskStatus(uploadResult.task_id)
          const newTask = taskStatusResponse.data
          
          // Add filename from the uploaded file since backend might not have it yet
          newTask.video_filename = newTask.video_filename || file.name
          newTask.video_size = newTask.video_size || file.size
          
          this.tasks.unshift(newTask)
        } catch (statusError) {
          console.warn('Could not fetch task status immediately, will rely on polling:', statusError)
          // Create a minimal task object for immediate display
          const minimalTask = {
            task_id: uploadResult.task_id,
            status: uploadResult.status,
            video_filename: file.name,
            video_size: file.size,
            upload_timestamp: new Date().toISOString(),
            overall_progress: 0,
            steps: []
          }
          this.tasks.unshift(minimalTask)
        }

        // Start WebSocket connection for real-time updates
        this.connectToTask(uploadResult.task_id)

        return uploadResult
      } catch (error) {
        this.error = error.response?.data?.message || error.message
        console.error('Failed to upload file:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchTaskStatus(taskId) {
      try {
        const response = await minutesApi.getTaskStatus(taskId)
        const updatedTask = response.data
        
        const index = this.tasks.findIndex(task => task.task_id === taskId)
        if (index !== -1) {
          this.tasks[index] = { ...this.tasks[index], ...updatedTask }
        }
        
        return updatedTask
      } catch (error) {
        console.error(`Failed to fetch status for task ${taskId}:`, error)
        throw error
      }
    },

    async fetchTaskResult(taskId) {
      try {
        const response = await minutesApi.getTaskResult(taskId)
        return response.data
      } catch (error) {
        console.error(`Failed to fetch result for task ${taskId}:`, error)
        throw error
      }
    },

    async deleteTask(taskId) {
      try {
        await minutesApi.deleteTask(taskId)
        this.tasks = this.tasks.filter(task => task.task_id !== taskId)
        this.disconnectFromTask(taskId)
      } catch (error) {
        console.error(`Failed to delete task ${taskId}:`, error)
        throw error
      }
    },

    async retryTask(taskId) {
      try {
        const response = await minutesApi.retryTask(taskId)
        const updatedTask = response.data
        
        const index = this.tasks.findIndex(task => task.task_id === taskId)
        if (index !== -1) {
          this.tasks[index] = { ...this.tasks[index], ...updatedTask }
        }

        // Reconnect WebSocket for retried task
        this.connectToTask(taskId)
        
        return updatedTask
      } catch (error) {
        console.error(`Failed to retry task ${taskId}:`, error)
        throw error
      }
    },

    connectToTask(taskId) {
      if (this.activeConnections.has(taskId)) {
        return
      }

      this.activeConnections.add(taskId)
      
      websocketManager.connect(taskId, {
        onMessage: (data) => {
          this.handleWebSocketMessage(taskId, data)
        },
        onClose: () => {
          this.activeConnections.delete(taskId)
        },
        onError: (error) => {
          console.error(`WebSocket error for task ${taskId}:`, error)
          this.activeConnections.delete(taskId)
        }
      })
    },

    disconnectFromTask(taskId) {
      websocketManager.disconnect(taskId)
      this.activeConnections.delete(taskId)
    },

    handleWebSocketMessage(taskId, data) {
      console.log(`WebSocket message received for task ${taskId}:`, data)
      
      const index = this.tasks.findIndex(task => task.task_id === taskId)
      if (index !== -1) {
        // Handle different message types
        if (data.type === 'progress_update') {
          this.tasks[index] = { ...this.tasks[index], ...data.data }
          console.log(`Progress update for task ${taskId}:`, this.tasks[index])
        } else if (data.type === 'task_completed') {
          console.log(`Task completed for ${taskId}:`, data.data)
          // Update task with completed data
          this.tasks[index] = { ...this.tasks[index], ...data.data }
          this.disconnectFromTask(taskId)
          
          // Also fetch complete task data to ensure consistency
          this.fetchTaskStatus(taskId)
        } else if (data.type === 'task_failed') {
          console.log(`Task failed for ${taskId}:`, data.data)
          this.tasks[index] = { 
            ...this.tasks[index], 
            status: 'failed', 
            error_message: data.data.error_message 
          }
          this.disconnectFromTask(taskId)
        } else {
          console.log(`Unknown message type for task ${taskId}:`, data)
          // Fallback for direct data updates
          this.tasks[index] = { ...this.tasks[index], ...data }
        }

        // If task is completed or failed, disconnect WebSocket
        const currentTask = this.tasks[index]
        if (currentTask.status === 'completed' || currentTask.status === 'failed') {
          this.disconnectFromTask(taskId)
        }
      }
    },

    startPolling(interval = 2000) {
      if (this.pollingInterval) {
        return
      }

      this.pollingInterval = setInterval(() => {
        // Poll for active tasks (processing or queued)
        const activeTasks = this.tasks.filter(task => 
          task.status === 'processing' || task.status === 'queued'
        )
        
        if (activeTasks.length > 0) {
          activeTasks.forEach(task => {
            this.fetchTaskStatus(task.task_id)
          })
        } else if (this.tasks.every(task => task.status === 'completed' || task.status === 'failed')) {
          // Stop polling if all tasks are complete
          this.stopPolling()
        }
      }, interval)
    },

    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },

    disconnectAllWebSockets() {
      websocketManager.disconnectAll()
      this.activeConnections.clear()
    },

    clearError() {
      this.error = null
    }
  }
})