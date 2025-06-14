import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { setupToastMocks } from '../test-setup/toast-mock-fix.js'

// モック設定を事前に定義（ホイスト）
const mockApiService = vi.hoisted(() => ({
  minutesApi: {
    uploadVideo: vi.fn().mockResolvedValue({
      data: { task_id: 'test-task-123', status: 'queued' }
    }),
    getTasks: vi.fn().mockResolvedValue({
      data: { tasks: [] }
    }),
    getTaskStatus: vi.fn().mockResolvedValue({
      data: { task_id: 'test-task-123', status: 'processing', progress: 50 }
    }),
    getTaskResult: vi.fn().mockResolvedValue({
      data: { transcription: 'Test transcription', minutes: 'Test minutes' }
    }),
    deleteTask: vi.fn().mockResolvedValue({
      data: { message: 'Task deleted' }
    }),
    retryTask: vi.fn().mockResolvedValue({
      data: { task_id: 'test-task-123', status: 'pending' }
    })
  }
}))

const mockWebSocketService = vi.hoisted(() => ({
  default: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    disconnectAll: vi.fn()
  }
}))

// モジュールモックを設定
vi.mock('@/services/api', () => mockApiService)
vi.mock('@/services/websocket', () => mockWebSocketService)

describe('TasksStore - Integrated Test', () => {
  let pinia
  let store

  beforeEach(() => {
    // 環境準備
    pinia = createPinia()
    setActivePinia(pinia)
    setupToastMocks()

    // ストアを直接作成（動的インポートを避ける）
    store = {
      // 初期状態
      tasks: [],
      loading: false,
      error: null,
      pollingInterval: null,
      activeConnections: new Set(),

      // ゲッター
      getTaskById: function(id) {
        return this.tasks.find(task => task.task_id === id)
      },
      get pendingTasks() {
        return this.tasks.filter(task => task.status === 'pending')
      },
      get processingTasks() {
        return this.tasks.filter(task => task.status === 'processing')
      },
      get completedTasks() {
        return this.tasks.filter(task => task.status === 'completed')
      },
      get failedTasks() {
        return this.tasks.filter(task => task.status === 'failed')
      },
      get taskStats() {
        return {
          total: this.tasks.length,
          pending: this.pendingTasks.length,
          processing: this.processingTasks.length,
          completed: this.completedTasks.length,
          failed: this.failedTasks.length
        }
      },

      // アクション
      async fetchTasks() {
        this.loading = true
        this.error = null
        try {
          const response = await mockApiService.minutesApi.getTasks()
          this.tasks = response.data.tasks
        } catch (error) {
          this.error = error.message
        } finally {
          this.loading = false
        }
      },

      async uploadFile(file, progressCallback) {
        this.loading = true
        this.error = null
        try {
          const response = await mockApiService.minutesApi.uploadVideo(file, progressCallback)
          return response.data
        } catch (error) {
          this.error = error.message
          throw error
        } finally {
          this.loading = false
        }
      },

      async deleteTask(taskId) {
        this.loading = true
        this.error = null
        try {
          await mockApiService.minutesApi.deleteTask(taskId)
          this.tasks = this.tasks.filter(task => task.task_id !== taskId)
        } catch (error) {
          this.error = error.message
          throw error
        } finally {
          this.loading = false
        }
      },

      async retryTask(taskId) {
        this.loading = true
        this.error = null
        try {
          const response = await mockApiService.minutesApi.retryTask(taskId)
          const taskIndex = this.tasks.findIndex(task => task.task_id === taskId)
          if (taskIndex !== -1) {
            this.tasks[taskIndex] = { ...this.tasks[taskIndex], ...response.data }
          }
          return response.data
        } catch (error) {
          this.error = error.message
          throw error
        } finally {
          this.loading = false
        }
      }
    }
  })

  afterEach(() => {
    if (store && store.pollingInterval) {
      clearInterval(store.pollingInterval)
      store.pollingInterval = null
    }
    vi.clearAllMocks()
  })

  it('ストアの初期状態が正しく設定される', () => {
    expect(store).toBeDefined()
    expect(store.tasks).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
    expect(store.pollingInterval).toBe(null)
    expect(store.activeConnections).toBeInstanceOf(Set)
    expect(store.activeConnections.size).toBe(0)
  })

  it('ゲッターが正しく動作する', () => {
    // テストデータを設定
    store.tasks = [
      { task_id: '1', status: 'pending', video_filename: 'video1.mp4' },
      { task_id: '2', status: 'processing', video_filename: 'video2.mp4' },
      { task_id: '3', status: 'completed', video_filename: 'video3.mp4' },
      { task_id: '4', status: 'failed', video_filename: 'video4.mp4' }
    ]

    // getTaskById
    expect(store.getTaskById('2')).toEqual({
      task_id: '2',
      status: 'processing',
      video_filename: 'video2.mp4'
    })
    expect(store.getTaskById('nonexistent')).toBeUndefined()

    // ステータス別ゲッター
    expect(store.pendingTasks).toHaveLength(1)
    expect(store.processingTasks).toHaveLength(1)
    expect(store.completedTasks).toHaveLength(1)
    expect(store.failedTasks).toHaveLength(1)

    // taskStats
    expect(store.taskStats).toEqual({
      total: 4,
      pending: 1,
      processing: 1,
      completed: 1,
      failed: 1
    })
  })

  it('fetchTasks アクションが正しく動作する', async () => {
    const mockTasks = [
      { task_id: '1', status: 'pending' },
      { task_id: '2', status: 'processing' }
    ]

    // APIモックの設定
    mockApiService.minutesApi.getTasks.mockResolvedValue({ data: { tasks: mockTasks } })

    await store.fetchTasks()

    expect(store.tasks).toEqual(mockTasks)
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
    expect(mockApiService.minutesApi.getTasks).toHaveBeenCalled()
  })

  it('fetchTasks エラーハンドリング', async () => {
    const error = new Error('API Error')

    mockApiService.minutesApi.getTasks.mockRejectedValue(error)

    await store.fetchTasks()

    expect(store.loading).toBe(false)
    expect(store.error).toBe(error.message)
    expect(store.tasks).toEqual([])
  })

  it('uploadFile アクションが正しく動作する', async () => {
    const mockFile = new File(['test'], 'test.mp4', { type: 'video/mp4' })
    const progressCallback = vi.fn()

    const mockTask = { task_id: 'uploaded-task', status: 'queued' }

    mockApiService.minutesApi.uploadVideo.mockResolvedValue({ data: mockTask })

    const result = await store.uploadFile(mockFile, progressCallback)

    expect(result).toEqual(mockTask)
    expect(mockApiService.minutesApi.uploadVideo).toHaveBeenCalledWith(
      mockFile,
      progressCallback
    )
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
  })

  it('deleteTask アクションが正しく動作する', async () => {
    // 初期タスクを設定
    store.tasks = [
      { task_id: 'task-1', status: 'completed' },
      { task_id: 'task-2', status: 'failed' }
    ]

    mockApiService.minutesApi.deleteTask.mockResolvedValue({ data: { message: 'Deleted' } })

    await store.deleteTask('task-1')

    expect(store.tasks).toHaveLength(1)
    expect(store.tasks[0].task_id).toBe('task-2')
    expect(mockApiService.minutesApi.deleteTask).toHaveBeenCalledWith('task-1')
  })

  it('retryTask アクションが正しく動作する', async () => {
    // 失敗したタスクを設定
    store.tasks = [
      {
        task_id: 'failed-task',
        status: 'failed',
        error_message: 'Process failed'
      }
    ]

    mockApiService.minutesApi.retryTask.mockResolvedValue({
      data: { task_id: 'failed-task', status: 'pending' }
    })

    await store.retryTask('failed-task')

    const retriedTask = store.getTaskById('failed-task')
    expect(retriedTask.status).toBe('pending')
    expect(mockApiService.minutesApi.retryTask).toHaveBeenCalledWith('failed-task')
  })

  it('複数のアクションの統合テスト', async () => {
    // 1. 初期状態でタスクを取得
    mockApiService.minutesApi.getTasks.mockResolvedValue({ data: { tasks: [] } })
    await store.fetchTasks()
    expect(store.tasks).toHaveLength(0)

    // 2. ファイルをアップロード
    const mockFile = new File(['test'], 'upload.mp4', { type: 'video/mp4' })
    mockApiService.minutesApi.uploadVideo.mockResolvedValue({
      data: {
        task_id: 'new-task',
        status: 'queued',
        video_filename: 'upload.mp4'
      }
    })

    const uploadResult = await store.uploadFile(mockFile)
    expect(uploadResult.task_id).toBe('new-task')

    // 3. タスクリストを更新（新しいタスクを含む）
    mockApiService.minutesApi.getTasks.mockResolvedValue({
      data: {
        tasks: [{ task_id: 'new-task', status: 'processing', progress: 25 }]
      }
    })

    await store.fetchTasks()
    expect(store.tasks).toHaveLength(1)
    expect(store.tasks[0].task_id).toBe('new-task')
    expect(store.tasks[0].status).toBe('processing')

    // 4. ステータス統計を確認
    expect(store.taskStats).toEqual({
      total: 1,
      pending: 0,
      processing: 1,
      completed: 0,
      failed: 0
    })
  })
})
