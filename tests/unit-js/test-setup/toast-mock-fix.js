// PrimeVue Toast問題の完全解決
import { vi } from 'vitest'

// PrimeVueToastSymbol の再現
const PrimeVueToastSymbol = Symbol('PrimeVueToast')

// Toast モックサービス
const createToastService = () => ({
  add: vi.fn(message => {
    console.log('Toast message:', message)
  }),
  remove: vi.fn(),
  removeGroup: vi.fn(),
  removeAllGroups: vi.fn(),
  clear: vi.fn()
})

// グローバルToastサービス（単一インスタンス）
const globalToastService = createToastService()

// useToast の完全モック（グローバルインスタンスを返す）
const mockUseToast = () => {
  return globalToastService
}

// Toastプロバイダー設定
export function setupToastProvider() {
  // グローバル設定でToastサービスを提供
  const app = {
    provide: (key, value) => {
      if (key === PrimeVueToastSymbol) {
        return globalToastService
      }
      return value
    },
    config: {
      globalProperties: {
        $toast: globalToastService
      }
    }
  }

  return {
    app,
    toastService: globalToastService,
    PrimeVueToastSymbol
  }
}

// Viteモック設定
export function setupToastMocks() {
  // useToast をモック
  vi.doMock('primevue/usetoast', () => ({
    useToast: mockUseToast,
    PrimeVueToastSymbol
  }))

  // ToastService をモック
  vi.doMock('primevue/toastservice', () => ({
    default: {
      install: app => {
        app.config.globalProperties.$toast = globalToastService
        app.provide(PrimeVueToastSymbol, globalToastService)
      }
    },
    PrimeVueToastSymbol
  }))

  return globalToastService
}

// Vue Test Utils マウントオプション用
export function createToastMountOptions(customToastService = null) {
  const toastService = customToastService || globalToastService

  return {
    global: {
      provide: {
        [PrimeVueToastSymbol]: toastService,
        PrimeVueToast: toastService
      },
      mocks: {
        $toast: toastService
      },
      plugins: [
        {
          install: app => {
            app.config.globalProperties.$toast = toastService
            app.provide(PrimeVueToastSymbol, toastService)
          }
        }
      ]
    }
  }
}

// シンプルなToast付きコンポーネントマウント（グローバルインスタンス使用）
export function mountWithToast(component, options = {}) {
  // 常にグローバルToastサービスを使用
  const toastOptions = createToastMountOptions(globalToastService)

  const mergedOptions = {
    ...toastOptions,
    global: {
      ...toastOptions.global,
      ...options.global,
      provide: {
        ...toastOptions.global.provide,
        ...options.global?.provide
      },
      mocks: {
        ...toastOptions.global.mocks,
        ...options.global?.mocks
      },
      plugins: [
        ...toastOptions.global.plugins,
        ...(options.global?.plugins || [])
      ]
    },
    ...options
  }

  return {
    toastService: globalToastService, // 常にグローバルインスタンスを返す
    mountOptions: mergedOptions
  }
}

export {
  PrimeVueToastSymbol,
  globalToastService,
  mockUseToast,
  createToastService
}
