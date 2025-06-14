// Vitest セットアップファイル
import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// グローバルプロパティのモック
config.global.mocks = {
  $t: (key) => key, // i18n モック
}

// PrimeVue コンポーネントのスタブ
config.global.stubs = {
  'router-link': true,
  'router-view': true,
  // PrimeVue コンポーネント
  'p-button': true,
  'p-card': true,
  'p-toast': true,
  'p-dialog': true,
  'p-progress-bar': true,
  'p-data-table': true,
  'p-column': true,
  'p-file-upload': true,
  'p-badge': true,
  'p-timeline': true,
  'p-menu': true,
  'p-menu-bar': true,
  'p-sidebar': true,
  'p-panel': true,
  'p-dropdown': true,
  'p-input-text': true,
  'p-textarea': true,
  'p-checkbox': true,
  'p-radio-button': true,
  'p-calendar': true,
  'p-chips': true,
  'p-tooltip': true
}

// Web APIs のモック
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// ResizeObserver のモック
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// IntersectionObserver のモック
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// File API のモック
global.File = class MockFile {
  constructor(fileBits, fileName, options) {
    this.fileBits = fileBits
    this.name = fileName
    this.size = fileBits[0]?.length || 0
    this.type = options?.type || ''
    this.lastModified = Date.now()
  }
}

global.FileReader = class MockFileReader {
  constructor() {
    this.result = null
    this.error = null
    this.readyState = 0
    this.onload = null
    this.onerror = null
    this.onabort = null
    this.onloadstart = null
    this.onloadend = null
    this.onprogress = null
  }

  readAsText(file) {
    setTimeout(() => {
      this.readyState = 2
      this.result = 'mocked file content'
      if (this.onload) this.onload()
    }, 0)
  }

  readAsDataURL(file) {
    setTimeout(() => {
      this.readyState = 2
      this.result = 'data:text/plain;base64,bW9ja2VkIGZpbGUgY29udGVudA=='
      if (this.onload) this.onload()
    }, 0)
  }

  abort() {
    this.readyState = 2
    if (this.onabort) this.onabort()
  }
}

// WebSocket のモック
global.WebSocket = vi.fn().mockImplementation(() => ({
  send: vi.fn(),
  close: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  readyState: 1, // OPEN
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3
}))

// localStorage のモック
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn()
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

// sessionStorage のモック
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn()
}
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock
})

// URL のモック
global.URL.createObjectURL = vi.fn(() => 'mocked-url')
global.URL.revokeObjectURL = vi.fn()

// Fetch API のモック (axios 用の fallback)
global.fetch = vi.fn()

// console のスパイ設定 (テスト中のログ出力を制御)
vi.spyOn(console, 'log').mockImplementation(() => {})
vi.spyOn(console, 'warn').mockImplementation(() => {})
vi.spyOn(console, 'error').mockImplementation(() => {})

// テスト環境変数
process.env.NODE_ENV = 'test'