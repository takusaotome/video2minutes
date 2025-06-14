import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useTasksStore } from '@/stores/tasks'
import { minutesApi } from '@/services/api'
import websocketManager from '@/services/websocket'
import { testData } from '../utils/test-helpers'

// モックの設定
vi.mock('@/services/api')
vi.mock('@/services/websocket')

describe('Tasks Store', () => {
  let store
  let mockApi
  let mockWebSocket

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useTasksStore()

    // API モック
    mockApi = {
      getTasks: vi.fn(),
      uploadVideo: vi.fn(),
      getTaskStatus: vi.fn(),
      getTaskResult: vi.fn(),
      deleteTask: vi.fn(),
      retryTask: vi.fn()
    }
    minutesApi.getTasks = mockApi.getTasks
    minutesApi.uploadVideo = mockApi.uploadVideo
    minutesApi.getTaskStatus = mockApi.getTaskStatus
    minutesApi.getTaskResult = mockApi.getTaskResult
    minutesApi.deleteTask = mockApi.deleteTask
    minutesApi.retryTask = mockApi.retryTask

    // WebSocket モック
    mockWebSocket = {
      connect: vi.fn(),
      disconnect: vi.fn(),
      disconnectAll: vi.fn()
    }
    websocketManager.connect = mockWebSocket.connect
    websocketManager.disconnect = mockWebSocket.disconnect
    websocketManager.disconnectAll = mockWebSocket.disconnectAll
  })

  afterEach(() => {
    // ポーリングのクリーンアップ
    if (store && store.pollingInterval) {
      clearInterval(store.pollingInterval)
      store.pollingInterval = null
    }
    // WebSocket接続のクリーンアップ
    if (store && store.activeConnections) {
      store.activeConnections.clear()
    }
    vi.clearAllMocks()
  })

  describe('初期状態', () => {
    it('初期状態が正しく設定される', () => {
      expect(store.tasks).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.error).toBe(null)
      expect(store.pollingInterval).toBe(null)
      expect(store.activeConnections).toBeInstanceOf(Set)
      expect(store.activeConnections.size).toBe(0)
    })
  })

  describe('ゲッター', () => {
    beforeEach(() => {
      store.tasks = [
        testData.createTask({ task_id: 'task-1', status: 'pending' }),
        testData.createTask({ task_id: 'task-2', status: 'processing' }),
        testData.createCompletedTask({ task_id: 'task-3' }),
        testData.createErrorTask({ task_id: 'task-4' })
      ]
    })

    it('getTaskById が正しく動作する', () => {
      expect(store.getTaskById('task-1')).toBeDefined()
      expect(store.getTaskById('task-1').task_id).toBe('task-1')
      expect(store.getTaskById('nonexistent')).toBeUndefined()
    })

    it('ステータス別フィルターが正しく動作する', () => {
      expect(store.pendingTasks).toHaveLength(1)
      expect(store.processingTasks).toHaveLength(1)
      expect(store.completedTasks).toHaveLength(1)
      expect(store.failedTasks).toHaveLength(1)
    })

    it('taskStats が正しい統計を返す', () => {
      const stats = store.taskStats
      expect(stats.total).toBe(4)
      expect(stats.pending).toBe(1)
      expect(stats.processing).toBe(1)
      expect(stats.completed).toBe(1)
      expect(stats.failed).toBe(1)
    })
  })

  describe('fetchTasks', () => {
    it('正常にタスクを取得する', async () => {
      const mockTasks = [testData.createTask(), testData.createCompletedTask()]
      mockApi.getTasks.mockResolvedValue({ data: { tasks: mockTasks } })

      await store.fetchTasks()

      expect(store.loading).toBe(false)
      expect(store.error).toBe(null)
      expect(store.tasks).toEqual(mockTasks)
      expect(mockApi.getTasks).toHaveBeenCalledOnce()
    })

    it('エラー時の処理', async () => {
      const error = new Error('Network error')
      mockApi.getTasks.mockRejectedValue(error)

      await store.fetchTasks()

      expect(store.loading).toBe(false)
      expect(store.error).toBe('Network error')
      expect(store.tasks).toEqual([])
    })

    it('APIレスポンスの異なる形式に対応', async () => {
      const mockTasks = [testData.createTask()]
      mockApi.getTasks.mockResolvedValue({ data: mockTasks })

      await store.fetchTasks()

      expect(store.tasks).toEqual(mockTasks)
    })
  })

  describe('uploadFile', () => {
    it('正常なファイルアップロード', async () => {
      const mockFile = new File(['content'], 'test.mp4', { type: 'video/mp4' })
      const mockUploadResult = { task_id: 'new-task', status: 'queued' }
      const mockTask = testData.createTask({ task_id: 'new-task' })

      mockApi.uploadVideo.mockResolvedValue({ data: mockUploadResult })
      mockApi.getTaskStatus.mockResolvedValue({ data: mockTask })

      const onProgress = vi.fn()
      const result = await store.uploadFile(mockFile, onProgress)

      expect(result).toEqual(mockUploadResult)
      expect(store.tasks[0]).toMatchObject(mockTask)
      expect(mockWebSocket.connect).toHaveBeenCalledWith(
        'new-task',
        expect.any(Object)
      )
      expect(store.activeConnections.has('new-task')).toBe(true)
    })

    it('進捗コールバックが呼ばれる', async () => {
      const mockFile = new File(['content'], 'test.mp4', { type: 'video/mp4' })
      const mockUploadResult = { task_id: 'new-task', status: 'queued' }

      let progressCallback
      mockApi.uploadVideo.mockImplementation((file, callback) => {
        progressCallback = callback
        return Promise.resolve({ data: mockUploadResult })
      })
      mockApi.getTaskStatus.mockResolvedValue({ data: testData.createTask() })

      const onProgress = vi.fn()
      const uploadPromise = store.uploadFile(mockFile, onProgress)

      // 進捗イベントをシミュレート
      progressCallback({ loaded: 50, total: 100 })

      await uploadPromise

      expect(onProgress).toHaveBeenCalledWith(50)
    })

    it('タスクステータス取得に失敗した場合の fallback', async () => {
      const mockFile = new File(['content'], 'test.mp4', { type: 'video/mp4' })
      const mockUploadResult = { task_id: 'new-task', status: 'queued' }

      mockApi.uploadVideo.mockResolvedValue({ data: mockUploadResult })
      mockApi.getTaskStatus.mockRejectedValue(new Error('Status not available'))

      await store.uploadFile(mockFile)

      expect(store.tasks[0]).toMatchObject({
        task_id: 'new-task',
        status: 'queued',
        video_filename: 'test.mp4'
      })
    })

    it('アップロードエラー時の処理', async () => {
      const mockFile = new File(['content'], 'test.mp4', { type: 'video/mp4' })
      const error = new Error('Upload failed')
      mockApi.uploadVideo.mockRejectedValue(error)

      await expect(store.uploadFile(mockFile)).rejects.toThrow('Upload failed')
      expect(store.error).toBe('Upload failed')
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchTaskStatus', () => {
    it('タスクステータスを正常に更新', async () => {
      const existingTask = testData.createTask({
        task_id: 'task-1',
        status: 'pending'
      })
      store.tasks = [existingTask]

      const updatedTask = {
        ...existingTask,
        status: 'processing',
        progress: 50
      }
      mockApi.getTaskStatus.mockResolvedValue({ data: updatedTask })

      const result = await store.fetchTaskStatus('task-1')

      expect(result).toEqual(updatedTask)
      expect(store.tasks[0]).toMatchObject(updatedTask)
    })

    it('存在しないタスクの場合', async () => {
      mockApi.getTaskStatus.mockResolvedValue({ data: testData.createTask() })

      await store.fetchTaskStatus('nonexistent')

      expect(store.tasks).toHaveLength(0)
    })
  })

  describe('WebSocket 管理', () => {
    it('タスク接続が正しく管理される', () => {
      store.connectToTask('task-1')

      expect(mockWebSocket.connect).toHaveBeenCalledWith(
        'task-1',
        expect.any(Object)
      )
      expect(store.activeConnections.has('task-1')).toBe(true)
    })

    it('重複接続を防ぐ', () => {
      store.activeConnections.add('task-1')
      store.connectToTask('task-1')

      expect(mockWebSocket.connect).not.toHaveBeenCalled()
    })

    it('タスク切断が正しく動作', () => {
      store.activeConnections.add('task-1')
      store.disconnectFromTask('task-1')

      expect(mockWebSocket.disconnect).toHaveBeenCalledWith('task-1')
      expect(store.activeConnections.has('task-1')).toBe(false)
    })

    it('WebSocket メッセージハンドリング - 進捗更新', () => {
      const task = testData.createTask({ task_id: 'task-1' })
      store.tasks = [task]

      const progressData = {
        type: 'progress_update',
        data: { progress: 75, current_step: 'transcription' }
      }

      store.handleWebSocketMessage('task-1', progressData)

      expect(store.tasks[0]).toMatchObject({
        ...task,
        progress: 75,
        current_step: 'transcription'
      })
    })

    it('WebSocket メッセージハンドリング - タスク完了', () => {
      const task = testData.createTask({ task_id: 'task-1' })
      store.tasks = [task]

      const completedData = {
        type: 'task_completed',
        data: { status: 'completed', minutes: 'Generated minutes' }
      }

      store.handleWebSocketMessage('task-1', completedData)

      expect(store.tasks[0]).toMatchObject({
        status: 'completed',
        minutes: 'Generated minutes'
      })
      expect(mockWebSocket.disconnect).toHaveBeenCalledWith('task-1')
    })

    it('WebSocket メッセージハンドリング - タスク失敗', () => {
      const task = testData.createTask({ task_id: 'task-1' })
      store.tasks = [task]

      const failedData = {
        type: 'task_failed',
        data: { error_message: 'Processing failed' }
      }

      store.handleWebSocketMessage('task-1', failedData)

      expect(store.tasks[0]).toMatchObject({
        status: 'failed',
        error_message: 'Processing failed'
      })
      expect(mockWebSocket.disconnect).toHaveBeenCalledWith('task-1')
    })
  })

  describe('ポーリング機能', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('アクティブタスクのポーリング開始', () => {
      store.tasks = [
        testData.createTask({ task_id: 'task-1', status: 'processing' }),
        testData.createCompletedTask({ task_id: 'task-2' })
      ]

      store.startPolling(1000)

      expect(store.pollingInterval).toBeDefined()

      vi.advanceTimersByTime(1000)

      expect(mockApi.getTaskStatus).toHaveBeenCalledWith('task-1')
      expect(mockApi.getTaskStatus).not.toHaveBeenCalledWith('task-2')
    })

    it('全タスク完了時にポーリング停止', () => {
      store.tasks = [
        testData.createCompletedTask({ task_id: 'task-1' }),
        testData.createErrorTask({ task_id: 'task-2' })
      ]

      store.startPolling(1000)
      vi.advanceTimersByTime(1000)

      expect(store.pollingInterval).toBe(null)
    })

    it('重複ポーリング開始を防ぐ', () => {
      store.pollingInterval = 123
      store.startPolling()

      expect(store.pollingInterval).toBe(123)
    })

    it('ポーリング手動停止', () => {
      store.startPolling()
      store.stopPolling()

      expect(store.pollingInterval).toBe(null)
    })
  })

  describe('タスク操作', () => {
    it('タスク削除', async () => {
      store.tasks = [testData.createTask({ task_id: 'task-1' })]
      store.activeConnections.add('task-1')
      mockApi.deleteTask.mockResolvedValue()

      await store.deleteTask('task-1')

      expect(store.tasks).toHaveLength(0)
      expect(mockWebSocket.disconnect).toHaveBeenCalledWith('task-1')
      expect(store.activeConnections.has('task-1')).toBe(false)
    })

    it('タスク再試行', async () => {
      const failedTask = testData.createErrorTask({ task_id: 'task-1' })
      store.tasks = [failedTask]

      const retriedTask = { ...failedTask, status: 'pending' }
      mockApi.retryTask.mockResolvedValue({ data: retriedTask })

      await store.retryTask('task-1')

      expect(store.tasks[0]).toMatchObject(retriedTask)
      expect(mockWebSocket.connect).toHaveBeenCalledWith(
        'task-1',
        expect.any(Object)
      )
    })

    it('タスク結果取得', async () => {
      const result = { transcription: 'text', minutes: 'minutes' }
      mockApi.getTaskResult.mockResolvedValue({ data: result })

      const fetchedResult = await store.fetchTaskResult('task-1')

      expect(fetchedResult).toEqual(result)
      expect(mockApi.getTaskResult).toHaveBeenCalledWith('task-1')
    })
  })

  describe('エラー管理', () => {
    it('エラークリア', () => {
      store.error = 'Some error'
      store.clearError()

      expect(store.error).toBe(null)
    })
  })

  describe('クリーンアップ', () => {
    it('全WebSocket接続を切断', () => {
      store.activeConnections.add('task-1')
      store.activeConnections.add('task-2')

      store.disconnectAllWebSockets()

      expect(mockWebSocket.disconnectAll).toHaveBeenCalled()
      expect(store.activeConnections.size).toBe(0)
    })
  })
})
