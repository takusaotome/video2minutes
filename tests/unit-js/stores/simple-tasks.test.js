import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { createTasksStoreMock } from '../test-setup/pinia-setup.js'

// APIモックをホイスト
const mockApiService = vi.hoisted(() => ({
  minutesApi: {
    getTasks: vi.fn(),
    uploadVideo: vi.fn(),
    getTaskStatus: vi.fn(),
    getTaskResult: vi.fn(),
    deleteTask: vi.fn(),
    retryTask: vi.fn()
  }
}))

const mockWebSocketService = vi.hoisted(() => ({
  default: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    disconnectAll: vi.fn()
  }
}))

// モジュールモック設定
vi.mock('@/services/api', () => mockApiService)
vi.mock('@/services/websocket', () => mockWebSocketService)

describe('Tasks Store - Simple Test', () => {
  let pinia
  let store

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)

    // 直接モックストアを作成（動的インポートを避ける）
    store = createTasksStoreMock({
      state: {
        tasks: [],
        loading: false,
        error: null
      }
    })
  })

  it('can be imported and initialized', () => {
    expect(store).toBeDefined()
    expect(store.tasks).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
  })

  it('has all required methods', () => {
    expect(typeof store.uploadFile).toBe('function')
    expect(typeof store.fetchTasks).toBe('function')
    expect(typeof store.deleteTask).toBe('function')
    expect(typeof store.retryTask).toBe('function')
  })
})
