import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('API Service - Simple Test', () => {
  beforeEach(() => {
    vi.resetModules()

    // Mock axios properly
    vi.doMock('axios', () => {
      const mockAxios = {
        create: vi.fn().mockReturnValue({
          get: vi.fn(),
          post: vi.fn(),
          delete: vi.fn(),
          interceptors: {
            request: { use: vi.fn() },
            response: { use: vi.fn() }
          }
        }),
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() }
        }
      }
      return { default: mockAxios }
    })
  })

  it('can import and initialize API service', async () => {
    const { minutesApi } = await import('@/services/api')

    expect(minutesApi).toBeDefined()
    expect(minutesApi.uploadVideo).toBeDefined()
    expect(minutesApi.getTasks).toBeDefined()
    expect(minutesApi.getTaskStatus).toBeDefined()
  })
})
