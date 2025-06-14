import { describe, it, expect, vi } from 'vitest'

describe('Basic Setup Test', () => {
  it('vitest is working', () => {
    expect(1 + 1).toBe(2)
  })

  it('vi.fn is working', () => {
    const mockFn = vi.fn()
    mockFn('test')
    expect(mockFn).toHaveBeenCalledWith('test')
  })

  it('environment variables are accessible', () => {
    expect(process.env.NODE_ENV).toBe('test')
  })
})
