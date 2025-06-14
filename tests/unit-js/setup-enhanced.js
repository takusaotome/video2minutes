// 強化された統合テスト用セットアップファイル
import { vi } from 'vitest'
import { config } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'

// 統合テスト用のヘルパーをインポート
import {
  createPrimeVueMountOptions,
  createToastMock,
  createConfirmationMock
} from './test-setup/primevue-setup.js'
import { createTestPinia as createCustomTestPinia } from './test-setup/pinia-setup.js'

// 基本的なモック設定
const mockToast = createToastMock()
const mockConfirmation = createConfirmationMock()

// PrimeVue useToast の完全なモック
vi.mock('primevue/usetoast', async importOriginal => {
  const actual = await importOriginal()
  return {
    ...actual,
    useToast: () => mockToast,
    PrimeVueToastSymbol: actual.PrimeVueToastSymbol
  }
})

// ConfirmationService のモック
vi.mock('primevue/confirmationservice', async importOriginal => {
  const actual = await importOriginal()
  return {
    ...actual,
    useConfirm: () => mockConfirmation
  }
})

// API サービスのモック
vi.mock('@/services/api', () => ({
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

// WebSocket サービスのモック
vi.mock('@/services/websocket', () => ({
  default: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    disconnectAll: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn()
  }
}))

// ルーターのモック
const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  go: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  currentRoute: {
    value: {
      path: '/',
      params: {},
      query: {},
      meta: {}
    }
  }
}

const mockRoute = {
  path: '/',
  params: {},
  query: {},
  meta: {},
  name: null,
  hash: '',
  fullPath: '/',
  matched: []
}

// Vue Router のモック
vi.mock('vue-router', () => ({
  useRouter: () => mockRouter,
  useRoute: () => mockRoute,
  createRouter: vi.fn(),
  createWebHistory: vi.fn(),
  RouterLink: {
    template: '<a @click="navigate"><slot /></a>',
    props: ['to'],
    methods: {
      navigate() {
        this.$router.push(this.to)
      }
    }
  },
  RouterView: {
    template: '<div class="router-view"><slot /></div>'
  }
}))

// グローバル設定
config.global.plugins = [createTestingPinia({ createSpy: vi.fn })]

config.global.mocks = {
  $t: (key, params) => key, // i18n モック
  $router: mockRouter,
  $route: mockRoute,
  $toast: mockToast,
  $confirm: mockConfirmation
}

config.global.stubs = {
  'router-link': {
    template: '<a @click="navigate"><slot /></a>',
    props: ['to'],
    methods: {
      navigate() {
        this.$router.push(this.to)
      }
    }
  },
  'router-view': {
    template: '<div class="router-view"><slot /></div>'
  },
  Teleport: {
    template: '<div class="teleport-stub"><slot /></div>'
  }
}

// Web APIs のモック
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
})

// ResizeObserver のモック
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

// IntersectionObserver のモック
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

// File API の強化されたモック
global.File = class MockFile {
  constructor(fileBits, fileName, options = {}) {
    this.fileBits = fileBits
    this.name = fileName
    this.size = options.size || fileBits[0]?.length || 0
    this.type = options.type || ''
    this.lastModified = options.lastModified || Date.now()
    this.lastModifiedDate = new Date(this.lastModified)
    this.webkitRelativePath = options.webkitRelativePath || ''
  }

  stream() {
    return new ReadableStream({
      start(controller) {
        controller.enqueue(new Uint8Array(this.fileBits[0] || []))
        controller.close()
      }
    })
  }

  text() {
    return Promise.resolve(this.fileBits[0] || '')
  }

  arrayBuffer() {
    const uint8Array = new Uint8Array(this.fileBits[0] || [])
    return Promise.resolve(uint8Array.buffer)
  }
}

global.FileReader = class MockFileReader extends EventTarget {
  constructor() {
    super()
    this.result = null
    this.error = null
    this.readyState = 0 // EMPTY
    this.EMPTY = 0
    this.LOADING = 1
    this.DONE = 2
  }

  readAsText(file) {
    this.readyState = this.LOADING
    setTimeout(() => {
      this.readyState = this.DONE
      this.result = 'mocked file content'
      this.dispatchEvent(new Event('load'))
      this.dispatchEvent(new Event('loadend'))
    }, 0)
  }

  readAsDataURL(file) {
    this.readyState = this.LOADING
    setTimeout(() => {
      this.readyState = this.DONE
      this.result = `data:${file.type || 'application/octet-stream'};base64,bW9ja2VkIGZpbGUgY29udGVudA==`
      this.dispatchEvent(new Event('load'))
      this.dispatchEvent(new Event('loadend'))
    }, 0)
  }

  readAsArrayBuffer(file) {
    this.readyState = this.LOADING
    setTimeout(() => {
      this.readyState = this.DONE
      this.result = new ArrayBuffer(8)
      this.dispatchEvent(new Event('load'))
      this.dispatchEvent(new Event('loadend'))
    }, 0)
  }

  abort() {
    this.readyState = this.DONE
    this.dispatchEvent(new Event('abort'))
    this.dispatchEvent(new Event('loadend'))
  }
}

// FormData のモック
global.FormData = class MockFormData {
  constructor() {
    this.data = new Map()
  }

  append(key, value, filename) {
    if (!this.data.has(key)) {
      this.data.set(key, [])
    }
    this.data.get(key).push(filename ? { value, filename } : value)
  }

  delete(key) {
    this.data.delete(key)
  }

  get(key) {
    const values = this.data.get(key)
    return values ? values[0] : null
  }

  getAll(key) {
    return this.data.get(key) || []
  }

  has(key) {
    return this.data.has(key)
  }

  set(key, value, filename) {
    this.data.set(key, [filename ? { value, filename } : value])
  }

  entries() {
    return this.data.entries()
  }

  keys() {
    return this.data.keys()
  }

  values() {
    return this.data.values()
  }
}

// WebSocket のモック
class MockWebSocket extends EventTarget {
  constructor(url, protocols) {
    super()
    this.url = url
    this.protocols = protocols
    this.readyState = MockWebSocket.CONNECTING
    this.CONNECTING = 0
    this.OPEN = 1
    this.CLOSING = 2
    this.CLOSED = 3

    // 接続をシミュレート
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.dispatchEvent(new Event('open'))
    }, 0)
  }

  send(data) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
    // エコーバック
    setTimeout(() => {
      this.dispatchEvent(new MessageEvent('message', { data }))
    }, 0)
  }

  close(code, reason) {
    this.readyState = MockWebSocket.CLOSING
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED
      this.dispatchEvent(new CloseEvent('close', { code, reason }))
    }, 0)
  }
}

MockWebSocket.CONNECTING = 0
MockWebSocket.OPEN = 1
MockWebSocket.CLOSING = 2
MockWebSocket.CLOSED = 3

global.WebSocket = MockWebSocket

// localStorage と sessionStorage のモック
const createStorageMock = () => {
  let store = {}
  return {
    getItem: vi.fn(key => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = String(value)
    }),
    removeItem: vi.fn(key => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get length() {
      return Object.keys(store).length
    },
    key: vi.fn(index => {
      const keys = Object.keys(store)
      return keys[index] || null
    })
  }
}

Object.defineProperty(window, 'localStorage', {
  value: createStorageMock()
})

Object.defineProperty(window, 'sessionStorage', {
  value: createStorageMock()
})

// URL のモック
global.URL.createObjectURL = vi.fn(() => 'blob:mock-url-12345')
global.URL.revokeObjectURL = vi.fn()

// Fetch API のモック
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  status: 200,
  statusText: 'OK',
  headers: new Headers(),
  json: vi.fn().mockResolvedValue({}),
  text: vi.fn().mockResolvedValue(''),
  blob: vi.fn().mockResolvedValue(new Blob()),
  arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(0))
})

// コンソールログのスパイ設定
vi.spyOn(console, 'log').mockImplementation(() => {})
vi.spyOn(console, 'warn').mockImplementation(() => {})
vi.spyOn(console, 'error').mockImplementation(() => {})

// テスト環境変数
process.env.NODE_ENV = 'test'
process.env.VITE_API_URL = 'http://localhost:8000'

// Global test utilities
global.testUtils = {
  mockToast,
  mockConfirmation,
  mockRouter,
  mockRoute,
  createMockFile: (options = {}) => {
    const {
      name = 'test.mp4',
      size = 1024 * 1024,
      type = 'video/mp4',
      content = 'mock video content'
    } = options
    return new File([content], name, { type, size })
  },
  createMockFiles: (count = 1, options = {}) => {
    return Array.from({ length: count }, (_, i) =>
      global.testUtils.createMockFile({
        name: `test-${i + 1}.mp4`,
        ...options
      })
    )
  }
}

// グローバルエラーハンドラー
window.addEventListener('error', event => {
  console.error('Global error:', event.error)
})

window.addEventListener('unhandledrejection', event => {
  console.error('Unhandled promise rejection:', event.reason)
})

// テスト完了時のクリーンアップ
afterEach(() => {
  vi.clearAllTimers()
})
