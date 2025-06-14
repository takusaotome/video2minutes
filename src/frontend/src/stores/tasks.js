import { defineStore } from 'pinia'
import { minutesApi } from '@/services/api'
import websocketManager from '@/services/websocket'

export const useTasksStore = defineStore('tasks', {
  state: () => ({
    tasks: [],
    loading: false,
    error: null,
    pollingInterval: null,
    activeConnections: new Set(),
    initialized: false // 初期化状態を追跡
  }),

  getters: {
    getTaskById: state => id => {
      return state.tasks.find(task => task.task_id === id)
    },

    pendingTasks: state => {
      return state.tasks.filter(task => task.status === 'pending')
    },

    processingTasks: state => {
      return state.tasks.filter(task => task.status === 'processing')
    },

    completedTasks: state => {
      return state.tasks.filter(task => task.status === 'completed')
    },

    failedTasks: state => {
      return state.tasks.filter(task => task.status === 'failed')
    },

    taskStats: state => {
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
    async fetchTasks(showLoading = true) {
      try {
        if (showLoading) {
          this.loading = true
        }
        this.error = null
        const response = await minutesApi.getTasks()
        this.tasks = response.data.tasks || response.data
        this.initialized = true
      } catch (error) {
        this.error = error.response?.data?.message || error.message
        console.error('Failed to fetch tasks:', error)
      } finally {
        if (showLoading) {
          this.loading = false
        }
      }
    },

    async silentRefresh() {
      // ローディング表示なしで更新（定期更新用）
      try {
        this.error = null
        const response = await minutesApi.getTasks()
        this.tasks = response.data.tasks || response.data
        this.initialized = true
      } catch (error) {
        console.error('Failed to silently refresh tasks:', error)
        // サイレント更新なので、エラーは設定しない
      }
    },

    async forceRefresh() {
      // 手動更新（ローディング表示あり）
      return await this.fetchTasks(true)
    },

    async uploadFile(file, onProgress) {
      try {
        this.loading = true
        this.error = null

        const response = await minutesApi.uploadVideo(file, progressEvent => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress?.(percentCompleted)
        })

        const uploadResult = response.data

        // Fetch the complete task information
        try {
          const taskStatusResponse = await minutesApi.getTaskStatus(
            uploadResult.task_id
          )
          const newTask = taskStatusResponse.data

          // Add filename from the uploaded file since backend might not have it yet
          newTask.video_filename = newTask.video_filename || file.name
          newTask.video_size = newTask.video_size || file.size

          this.tasks.unshift(newTask)
        } catch (statusError) {
          console.warn(
            'Could not fetch task status immediately, will rely on polling:',
            statusError
          )
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
          const previousTask = { ...this.tasks[index] }

          // Merge the updated data
          this.tasks[index] = { ...this.tasks[index], ...updatedTask }

          // Log status changes for debugging
          if (previousTask.status !== updatedTask.status) {
            console.log(
              `Task ${taskId.slice(-8)} status changed: ${previousTask.status} -> ${updatedTask.status}`
            )
          }

          if (previousTask.overall_progress !== updatedTask.overall_progress) {
            console.log(
              `Task ${taskId.slice(-8)} progress updated: ${previousTask.overall_progress}% -> ${updatedTask.overall_progress}%`
            )
          }

          // If task completed or failed, disconnect WebSocket
          if (
            updatedTask.status === 'completed' ||
            updatedTask.status === 'failed'
          ) {
            console.log(
              `Task ${taskId.slice(-8)} finished, disconnecting WebSocket`
            )
            this.disconnectFromTask(taskId)
          }
        } else {
          console.warn(`Task ${taskId} not found in local store`)
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
        onMessage: data => {
          this.handleWebSocketMessage(taskId, data)
        },
        onClose: () => {
          this.activeConnections.delete(taskId)
        },
        onError: error => {
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
        if (
          currentTask.status === 'completed' ||
          currentTask.status === 'failed'
        ) {
          this.disconnectFromTask(taskId)
        }
      }
    },

    startPolling(interval = 5000) {
      if (this.pollingInterval) {
        console.log('Polling already active, skipping start')
        return
      }

      console.log('Starting task polling with interval:', interval)

      // Use adaptive polling - faster when tasks are active
      let currentInterval = interval

      this.pollingInterval = setInterval(async () => {
        // Poll for active tasks (processing, pending, or queued)
        const activeTasks = this.tasks.filter(
          task =>
            task.status === 'processing' ||
            task.status === 'pending' ||
            task.status === 'queued'
        )

        console.log(
          `[${new Date().toLocaleTimeString()}] Polling: ${activeTasks.length} active tasks found`
        )

        if (activeTasks.length > 0) {
          console.log(
            'Active tasks:',
            activeTasks.map(
              t =>
                `${t.task_id.slice(-8)}: ${t.status} (${t.overall_progress}%)`
            )
          )

          // Use faster polling for active tasks (3 seconds)
          if (currentInterval !== 3000) {
            currentInterval = 3000
            this.restartPolling(currentInterval)
            return
          }

          // Update all active tasks in parallel for better performance
          const updatePromises = activeTasks.map(async task => {
            try {
              const before = {
                status: task.status,
                progress: task.overall_progress
              }
              const updated = await this.fetchTaskStatus(task.task_id)
              const after = {
                status: updated.status,
                progress: updated.overall_progress
              }

              if (
                before.status !== after.status ||
                before.progress !== after.progress
              ) {
                console.log(
                  `Task ${task.task_id.slice(-8)} updated:`,
                  before,
                  '->',
                  after
                )
              }
            } catch (error) {
              console.error(`Failed to poll task ${task.task_id}:`, error)
            }
          })

          await Promise.allSettled(updatePromises)
        } else if (
          this.tasks.length > 0 &&
          this.tasks.every(
            task => task.status === 'completed' || task.status === 'failed'
          )
        ) {
          // Stop polling if all tasks are complete
          console.log('All tasks completed, stopping polling')
          this.stopPolling()
        } else if (this.tasks.length === 0) {
          // Refresh task list to check for new tasks (without loading spinner)
          console.log('No tasks found, refreshing task list')
          await this.silentRefresh()
        } else {
          // Use slower polling when no active tasks (back to original interval)
          if (currentInterval !== interval) {
            currentInterval = interval
            this.restartPolling(currentInterval)
            return
          }
        }
      }, currentInterval)
    },

    restartPolling(newInterval) {
      console.log(`Restarting polling with new interval: ${newInterval}ms`)
      this.stopPolling()
      this.startPolling(newInterval)
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
    },

    async forceRefresh() {
      console.log('Force refreshing tasks...')
      await this.fetchTasks()

      // If there are active tasks and polling is not running, start it
      const activeTasks = this.tasks.filter(
        task =>
          task.status === 'processing' ||
          task.status === 'pending' ||
          task.status === 'queued'
      )

      if (activeTasks.length > 0 && !this.pollingInterval) {
        console.log('Found active tasks after refresh, starting polling')
        this.startPolling(5000)
      }
    }
  }
})
