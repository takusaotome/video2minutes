import { describe, it, expect } from 'vitest'
import {
  formatDateTime,
  formatDate,
  formatTime,
  formatRelativeTime,
  formatDuration,
  formatFileSize
} from '@/utils/dateUtils'

describe('dateUtils', () => {
  it('formats date and time with timezone option', () => {
    const result = formatDateTime('2024-01-01T12:34:56Z', { timeZone: 'UTC' })
    expect(result).toBe('2024/01/01 12:34')
  })

  it('returns empty string for invalid input', () => {
    expect(formatDateTime('invalid')).toBe('')
  })

  it('formatDate returns date string', () => {
    const res = formatDate('2024-01-01T12:34:56Z')
    expect(res).toBe('2024/01/01 12:34')
  })

  it('formatTime returns time string', () => {
    const res = formatTime('2024-01-01T12:34:56Z')
    expect(res).toBe('2024/01/01 12:34')
  })

  it('formatRelativeTime displays minutes ago', () => {
    const date = new Date(Date.now() - 5 * 60 * 1000)
    expect(formatRelativeTime(date)).toBe('5分前')
  })

  it('formatDuration handles hours and minutes', () => {
    expect(formatDuration(3661000)).toBe('1時間1分1秒')
    expect(formatDuration(90000)).toBe('1分30秒')
    expect(formatDuration(0)).toBe('0秒')
  })

  it('formatFileSize converts bytes', () => {
    expect(formatFileSize(0)).toBe('0 Bytes')
    expect(formatFileSize(1024)).toBe('1 KB')
    expect(formatFileSize(1024 * 1024)).toBe('1 MB')
  })
})
