import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

describe('Tasks Store - Simple Test', () => {
  let pinia

  beforeEach(async () => {
    pinia = createPinia()
    setActivePinia(pinia)

    // Mock the API and WebSocket services before importing the store
    vi.doMock('@/services/api', () => ({
      minutesApi: {
        getTasks: vi.fn(),
        uploadVideo: vi.fn(),
        getTaskStatus: vi.fn(),
        getTaskResult: vi.fn(),
        deleteTask: vi.fn(),
        retryTask: vi.fn()
      }
    }))

    vi.doMock('@/services/websocket', () => ({
      default: {
        connect: vi.fn(),
        disconnect: vi.fn(),
        disconnectAll: vi.fn()
      }
    }))
  })

  it('can be imported and initialized', async () => {
    // Dynamic import after mocks are set up
    const { useTasksStore } = await import('@/stores/tasks')

    // Create and set the pinia instance before using the store
    const store = useTasksStore()

    expect(store).toBeDefined()
    expect(store.tasks).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBe(null)
  })
})
