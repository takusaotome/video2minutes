import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { setupToastMocks } from '../test-setup/toast-mock-fix.js'

describe('TasksStore - Integrated Test', () => {
  let pinia
  let store

  beforeEach(async () => {
    // 環境準備
    pinia = createPinia()
    setActivePinia(pinia)
    setupToastMocks()

    // APIとWebSocketをモック
    vi.doMock('@/services/api', () => ({
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

    vi.doMock('@/services/websocket', () => ({
      default: {
        connect: vi.fn(),
        disconnect: vi.fn(),
        disconnectAll: vi.fn()
      }
    }))

    // ストアを動的インポート
    const { useTasksStore } = await import('@/stores/tasks')
    store = useTasksStore()
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
    const { minutesApi } = await import('@/services/api')
    minutesApi.getTasks.mockResolvedValue({ data: { tasks: mockTasks } })

    await store.fetchTasks()

    expect(store.tasks).toEqual(mockTasks)
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
    expect(minutesApi.getTasks).toHaveBeenCalled()
  })

  it('fetchTasks エラーハンドリング', async () => {
    const error = new Error('API Error')

    const { minutesApi } = await import('@/services/api')
    minutesApi.getTasks.mockRejectedValue(error)

    await store.fetchTasks()

    expect(store.loading).toBe(false)
    expect(store.error).toBe(error.message)
    expect(store.tasks).toEqual([])
  })

  it('uploadFile アクションが正しく動作する', async () => {
    const mockFile = new File(['test'], 'test.mp4', { type: 'video/mp4' })
    const progressCallback = vi.fn()

    const mockTask = { task_id: 'uploaded-task', status: 'queued' }

    const { minutesApi } = await import('@/services/api')
    minutesApi.uploadVideo.mockResolvedValue({ data: mockTask })

    const result = await store.uploadFile(mockFile, progressCallback)

    expect(result).toEqual(mockTask)
    expect(minutesApi.uploadVideo).toHaveBeenCalledWith(
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

    const { minutesApi } = await import('@/services/api')
    minutesApi.deleteTask.mockResolvedValue({ data: { message: 'Deleted' } })

    await store.deleteTask('task-1')

    expect(store.tasks).toHaveLength(1)
    expect(store.tasks[0].task_id).toBe('task-2')
    expect(minutesApi.deleteTask).toHaveBeenCalledWith('task-1')
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

    const { minutesApi } = await import('@/services/api')
    minutesApi.retryTask.mockResolvedValue({
      data: { task_id: 'failed-task', status: 'pending' }
    })

    await store.retryTask('failed-task')

    const retriedTask = store.getTaskById('failed-task')
    expect(retriedTask.status).toBe('pending')
    expect(minutesApi.retryTask).toHaveBeenCalledWith('failed-task')
  })

  it('複数のアクションの統合テスト', async () => {
    const { minutesApi } = await import('@/services/api')

    // 1. 初期状態でタスクを取得
    minutesApi.getTasks.mockResolvedValue({ data: { tasks: [] } })
    await store.fetchTasks()
    expect(store.tasks).toHaveLength(0)

    // 2. ファイルをアップロード
    const mockFile = new File(['test'], 'upload.mp4', { type: 'video/mp4' })
    minutesApi.uploadVideo.mockResolvedValue({
      data: {
        task_id: 'new-task',
        status: 'queued',
        video_filename: 'upload.mp4'
      }
    })

    const uploadResult = await store.uploadFile(mockFile)
    expect(uploadResult.task_id).toBe('new-task')

    // 3. タスクリストを更新（新しいタスクを含む）
    minutesApi.getTasks.mockResolvedValue({
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
