import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import { createAxiosMock, createMockFile } from '../utils/test-helpers'

// Axios のモック
vi.mock('axios', () => ({
  default: {
    create: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  }
}))

describe('API Service', () => {
  let mockAxios
  let axiosMock

  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks()

    // Axios インスタンスのモック
    mockAxios = {
      create: vi.fn().mockReturnThis(),
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    }

    // Reset axios module and create mock
    vi.resetModules()
    axios.create = vi.fn().mockReturnValue(mockAxios)
    axiosMock = createAxiosMock()

    // コンソールログのモック
    vi.spyOn(console, 'log').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.clearAllMocks()
    axiosMock.restore()
  })

  describe('API インスタンス設定', () => {
    it('正しいベースURLで作成される', async () => {
      // モジュールを動的インポートしてテスト
      const { minutesApi } = await import('@/services/api')

      expect(axios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000/api/v1',
        timeout: 300000,
        headers: {
          'Content-Type': 'application/json'
        }
      })
    })

    it('環境変数のAPI URLが使用される', async () => {
      vi.stubEnv('VITE_API_URL', 'https://api.example.com')

      // モジュールを再インポートして環境変数を反映
      vi.resetModules()
      const { minutesApi } = await import('@/services/api')

      expect(axios.create).toHaveBeenCalled()
    })
  })

  describe('uploadVideo', () => {
    it('正常なファイルアップロード', async () => {
      const mockFile = createMockFile({ name: 'test.mp4' })
      const mockResponse = { data: { task_id: 'task-123', status: 'queued' } }

      mockAxios.post.mockResolvedValue(mockResponse)

      const result = await minutesApi.uploadVideo(mockFile)

      expect(mockAxios.post).toHaveBeenCalledWith(
        '/minutes/upload',
        expect.any(FormData),
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: undefined
        }
      )
      expect(result).toEqual(mockResponse)
    })

    it('進捗コールバック付きアップロード', async () => {
      const mockFile = createMockFile()
      const mockResponse = { data: { task_id: 'task-123' } }
      const onProgress = vi.fn()

      mockAxios.post.mockResolvedValue(mockResponse)

      await minutesApi.uploadVideo(mockFile, onProgress)

      expect(mockAxios.post).toHaveBeenCalledWith(
        '/minutes/upload',
        expect.any(FormData),
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: onProgress
        }
      )
    })

    it('FormData が正しく構築される', async () => {
      const mockFile = createMockFile({ name: 'test.mp4' })
      mockAxios.post.mockResolvedValue({ data: {} })

      await minutesApi.uploadVideo(mockFile)

      const formDataArg = mockAxios.post.mock.calls[0][1]
      expect(formDataArg).toBeInstanceOf(FormData)
    })

    it('アップロードエラーの処理', async () => {
      const mockFile = createMockFile()
      const error = new Error('Upload failed')

      mockAxios.post.mockRejectedValue(error)

      await expect(minutesApi.uploadVideo(mockFile)).rejects.toThrow(
        'Upload failed'
      )
    })
  })

  describe('getTasks', () => {
    it('全タスク取得', async () => {
      const mockTasks = [
        { task_id: 'task-1', status: 'completed' },
        { task_id: 'task-2', status: 'processing' }
      ]
      const mockResponse = { data: { tasks: mockTasks } }

      mockAxios.get.mockResolvedValue(mockResponse)

      const result = await minutesApi.getTasks()

      expect(mockAxios.get).toHaveBeenCalledWith('/minutes/tasks')
      expect(result).toEqual(mockResponse)
    })

    it('タスク取得エラー', async () => {
      const error = new Error('Network error')
      mockAxios.get.mockRejectedValue(error)

      await expect(minutesApi.getTasks()).rejects.toThrow('Network error')
    })
  })

  describe('getTaskStatus', () => {
    it('タスクステータス取得', async () => {
      const taskId = 'task-123'
      const mockStatus = {
        task_id: taskId,
        status: 'processing',
        progress: 50
      }
      const mockResponse = { data: mockStatus }

      mockAxios.get.mockResolvedValue(mockResponse)

      const result = await minutesApi.getTaskStatus(taskId)

      expect(mockAxios.get).toHaveBeenCalledWith(`/minutes/${taskId}/status`)
      expect(result).toEqual(mockResponse)
    })

    it('存在しないタスクのステータス取得', async () => {
      const error = {
        response: { status: 404, data: { message: 'Task not found' } }
      }
      mockAxios.get.mockRejectedValue(error)

      await expect(minutesApi.getTaskStatus('nonexistent')).rejects.toEqual(
        error
      )
    })
  })

  describe('getTaskResult', () => {
    it('タスク結果取得', async () => {
      const taskId = 'task-123'
      const mockResult = {
        transcription: 'Sample transcription',
        minutes: '# Meeting Minutes\n\nContent here'
      }
      const mockResponse = { data: mockResult }

      mockAxios.get.mockResolvedValue(mockResponse)

      const result = await minutesApi.getTaskResult(taskId)

      expect(mockAxios.get).toHaveBeenCalledWith(`/minutes/${taskId}/result`)
      expect(result).toEqual(mockResponse)
    })

    it('未完了タスクの結果取得エラー', async () => {
      const error = {
        response: {
          status: 400,
          data: { message: 'Task not completed' }
        }
      }
      mockAxios.get.mockRejectedValue(error)

      await expect(minutesApi.getTaskResult('incomplete-task')).rejects.toEqual(
        error
      )
    })
  })

  describe('deleteTask', () => {
    it('タスク削除', async () => {
      const taskId = 'task-123'
      const mockResponse = { data: { message: 'Task deleted' } }

      mockAxios.delete.mockResolvedValue(mockResponse)

      const result = await minutesApi.deleteTask(taskId)

      expect(mockAxios.delete).toHaveBeenCalledWith(`/minutes/${taskId}`)
      expect(result).toEqual(mockResponse)
    })

    it('存在しないタスクの削除エラー', async () => {
      const error = { response: { status: 404 } }
      mockAxios.delete.mockRejectedValue(error)

      await expect(minutesApi.deleteTask('nonexistent')).rejects.toEqual(error)
    })
  })

  describe('retryTask', () => {
    it('タスク再試行', async () => {
      const taskId = 'failed-task'
      const mockResponse = {
        data: {
          task_id: taskId,
          status: 'pending',
          message: 'Task queued for retry'
        }
      }

      mockAxios.post.mockResolvedValue(mockResponse)

      const result = await minutesApi.retryTask(taskId)

      expect(mockAxios.post).toHaveBeenCalledWith(`/minutes/${taskId}/retry`)
      expect(result).toEqual(mockResponse)
    })

    it('再試行不可能なタスクのエラー', async () => {
      const error = {
        response: {
          status: 400,
          data: { message: 'Task cannot be retried' }
        }
      }
      mockAxios.post.mockRejectedValue(error)

      await expect(minutesApi.retryTask('completed-task')).rejects.toEqual(
        error
      )
    })
  })

  describe('インターセプター', () => {
    it('リクエストインターセプターが設定される', () => {
      expect(mockAxios.interceptors.request.use).toHaveBeenCalled()
    })

    it('レスポンスインターセプターが設定される', () => {
      expect(mockAxios.interceptors.response.use).toHaveBeenCalled()
    })
  })

  describe('エラーハンドリング', () => {
    it('ネットワークエラーの処理', async () => {
      const networkError = new Error('Network Error')
      networkError.code = 'NETWORK_ERROR'

      mockAxios.get.mockRejectedValue(networkError)

      await expect(minutesApi.getTasks()).rejects.toThrow('Network Error')
    })

    it('タイムアウトエラーの処理', async () => {
      const timeoutError = new Error('timeout of 300000ms exceeded')
      timeoutError.code = 'ECONNABORTED'

      mockAxios.get.mockRejectedValue(timeoutError)

      await expect(minutesApi.getTasks()).rejects.toThrow(
        'timeout of 300000ms exceeded'
      )
    })

    it('HTTP エラーレスポンスの処理', async () => {
      const httpError = {
        response: {
          status: 500,
          data: { message: 'Internal Server Error' }
        }
      }

      mockAxios.get.mockRejectedValue(httpError)

      await expect(minutesApi.getTasks()).rejects.toEqual(httpError)
    })
  })

  describe('レスポンス形式', () => {
    it('正常なレスポンス形式の確認', async () => {
      const mockResponse = {
        data: { tasks: [] },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      }

      mockAxios.get.mockResolvedValue(mockResponse)

      const result = await minutesApi.getTasks()

      expect(result).toHaveProperty('data')
      expect(result).toHaveProperty('status')
      expect(result.status).toBe(200)
    })

    it('空のレスポンスの処理', async () => {
      const emptyResponse = { data: null, status: 204 }
      mockAxios.delete.mockResolvedValue(emptyResponse)

      const result = await minutesApi.deleteTask('task-123')

      expect(result.status).toBe(204)
      expect(result.data).toBe(null)
    })
  })
})
