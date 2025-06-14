// JavaScript単体テスト用ヘルパー関数
import { nextTick } from 'vue'
import { createTestingPinia } from '@pinia/testing'
import { vi } from 'vitest'
import axios from 'axios'
import MockAdapter from 'axios-mock-adapter'

/**
 * Vue Test Utils のマウントオプション生成
 */
export function createMountOptions(options = {}) {
  const mockToast = {
    add: vi.fn(),
    remove: vi.fn(),
    removeGroup: vi.fn(),
    removeAllGroups: vi.fn()
  }

  return {
    global: {
      plugins: [
        createTestingPinia({
          createSpy: vi.fn,
          initialState: options.initialState || {}
        })
      ],
      provide: {
        PrimeVueToast: mockToast,
        $primevue: {
          config: {
            ripple: false,
            inputStyle: 'outlined'
          }
        },
        ...options.provide
      },
      mocks: {
        $router: {
          push: vi.fn(),
          replace: vi.fn(),
          go: vi.fn(),
          back: vi.fn(),
          forward: vi.fn()
        },
        $route: {
          path: '/',
          params: {},
          query: {},
          ...options.route
        },
        $toast: mockToast,
        ...options.mocks
      },
      stubs: {
        'router-link': true,
        'router-view': true,
        Teleport: true,
        ...options.stubs
      }
    },
    ...options
  }
}

/**
 * Axios モックアダプター生成
 */
export function createAxiosMock() {
  const mock = new MockAdapter(axios)

  // デフォルトのレスポンス設定
  mock.onGet('/api/v1/minutes/tasks').reply(200, [])
  mock.onPost('/api/v1/minutes/upload').reply(200, {
    task_id: 'test-task-id',
    status: 'queued'
  })

  return mock
}

/**
 * ファイルオブジェクトのモック生成
 */
export function createMockFile(options = {}) {
  const {
    name = 'test-video.mp4',
    size = 1024 * 1024, // 1MB
    type = 'video/mp4',
    content = 'mock video content'
  } = options

  return new File([content], name, { type, size })
}

/**
 * ファイルアップロードイベントのモック生成
 */
export function createFileUploadEvent(files) {
  const fileArray = Array.isArray(files) ? files : [files]

  return {
    target: {
      files: fileArray
    },
    dataTransfer: {
      files: fileArray
    },
    preventDefault: vi.fn(),
    stopPropagation: vi.fn()
  }
}

/**
 * WebSocket モック生成
 */
export function createWebSocketMock() {
  const eventListeners = {}

  const mockWebSocket = {
    readyState: 1, // OPEN
    send: vi.fn(),
    close: vi.fn(),
    addEventListener: vi.fn((event, handler) => {
      if (!eventListeners[event]) {
        eventListeners[event] = []
      }
      eventListeners[event].push(handler)
    }),
    removeEventListener: vi.fn(),

    // テスト用メソッド
    triggerEvent: (event, data) => {
      if (eventListeners[event]) {
        eventListeners[event].forEach(handler => handler(data))
      }
    },

    triggerMessage: data => {
      const event = { data: JSON.stringify(data) }
      if (eventListeners.message) {
        eventListeners.message.forEach(handler => handler(event))
      }
    },

    triggerOpen: () => {
      if (eventListeners.open) {
        eventListeners.open.forEach(handler => handler())
      }
    },

    triggerClose: () => {
      if (eventListeners.close) {
        eventListeners.close.forEach(handler => handler())
      }
    },

    triggerError: error => {
      if (eventListeners.error) {
        eventListeners.error.forEach(handler => handler(error))
      }
    }
  }

  return mockWebSocket
}

/**
 * Toast通知のアサーション
 */
export function expectToastCall(mockToast, severity, summary, detail) {
  expect(mockToast.add).toHaveBeenCalledWith({
    severity,
    summary,
    detail,
    life: expect.any(Number)
  })
}

/**
 * ルーターナビゲーションのアサーション
 */
export function expectRouterPush(mockRouter, path) {
  expect(mockRouter.push).toHaveBeenCalledWith(path)
}

/**
 * 非同期更新の完了を待機
 */
export async function waitForAsyncUpdate() {
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

/**
 * 指定時間だけ待機
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * DOM要素の表示を待機
 */
export async function waitForElement(wrapper, selector, timeout = 1000) {
  const start = Date.now()

  while (Date.now() - start < timeout) {
    await nextTick()
    const element = wrapper.find(selector)
    if (element.exists()) {
      return element
    }
    await sleep(10)
  }

  throw new Error(`Element ${selector} not found within ${timeout}ms`)
}

/**
 * テストデータ生成
 */
export const testData = {
  // タスクデータ
  createTask: (overrides = {}) => ({
    task_id: 'test-task-123',
    status: 'pending',
    video_filename: 'test-video.mp4',
    video_size: 1024 * 1024,
    upload_timestamp: '2024-01-15T10:00:00Z',
    processing_steps: [
      { name: 'upload', status: 'completed', progress: 100 },
      { name: 'audio_extraction', status: 'pending', progress: 0 },
      { name: 'transcription', status: 'pending', progress: 0 },
      { name: 'minutes_generation', status: 'pending', progress: 0 }
    ],
    progress: 25,
    transcription: null,
    minutes: null,
    error_message: null,
    ...overrides
  }),

  // 完了したタスクデータ
  createCompletedTask: (overrides = {}) => ({
    task_id: 'completed-task-456',
    status: 'completed',
    video_filename: 'completed-video.mp4',
    video_size: 2 * 1024 * 1024,
    upload_timestamp: '2024-01-15T09:00:00Z',
    processing_steps: [
      { name: 'upload', status: 'completed', progress: 100 },
      { name: 'audio_extraction', status: 'completed', progress: 100 },
      { name: 'transcription', status: 'completed', progress: 100 },
      { name: 'minutes_generation', status: 'completed', progress: 100 }
    ],
    progress: 100,
    transcription: 'これはサンプルの文字起こし結果です。',
    minutes: '# 会議議事録\n\n## 概要\nサンプル議事録の内容です。',
    error_message: null,
    ...overrides
  }),

  // エラータスクデータ
  createErrorTask: (overrides = {}) => ({
    task_id: 'error-task-789',
    status: 'failed',
    video_filename: 'error-video.mp4',
    video_size: 1024 * 1024,
    upload_timestamp: '2024-01-15T08:00:00Z',
    processing_steps: [
      { name: 'upload', status: 'completed', progress: 100 },
      { name: 'audio_extraction', status: 'failed', progress: 50 },
      { name: 'transcription', status: 'pending', progress: 0 },
      { name: 'minutes_generation', status: 'pending', progress: 0 }
    ],
    progress: 25,
    transcription: null,
    minutes: null,
    error_message: 'Audio extraction failed: Invalid video format',
    ...overrides
  })
}

/**
 * カスタムマッチャー
 */
export const customMatchers = {
  toBeInDocument: received => {
    const pass = received && document.body.contains(received)
    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to be in document`
          : `Expected element to be in document`
    }
  },

  toHaveTextContent: (received, expected) => {
    const pass =
      received &&
      received.textContent &&
      received.textContent.includes(expected)
    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to have text content "${expected}"`
          : `Expected element to have text content "${expected}"`
    }
  }
}

// カスタムマッチャーを拡張
expect.extend(customMatchers)
