// Vue統合テスト用のセットアップファイル
import { mount, shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { vi } from 'vitest'
import {
  createPrimeVueMountOptions,
  createToastMock,
  createConfirmationMock
} from './primevue-setup.js'
import { createTestPinia, createTasksStoreMock } from './pinia-setup.js'
import {
  setupToastMocks,
  globalToastService,
  PrimeVueToastSymbol
} from './toast-mock-fix.js'

/**
 * 完全統合テスト用のマウントオプション作成
 */
export function createIntegratedMountOptions(options = {}) {
  // Pinia設定
  const pinia = createTestPinia({
    initialState: options.piniaState || {},
    stubActions: options.stubActions !== undefined ? options.stubActions : false
  })

  // Toast統合モック設定
  setupToastMocks()

  // Toast/Confirmation モック
  const toastMock = globalToastService // 統一されたToastサービスを使用
  const confirmationMock = createConfirmationMock()

  // PrimeVueマウントオプション取得
  const primeVueOptions = createPrimeVueMountOptions(options.primeVue || {})

  // 統合マウントオプション
  return {
    ...primeVueOptions,
    global: {
      ...primeVueOptions.global,
      plugins: [
        pinia,
        // PrimeVue Toast統合プラグイン
        {
          install: app => {
            app.config.globalProperties.$toast = toastMock
            app.provide(PrimeVueToastSymbol, toastMock)
          }
        },
        ...primeVueOptions.global.plugins
      ],
      provide: {
        ...primeVueOptions.global.provide,
        [PrimeVueToastSymbol]: toastMock,
        PrimeVueToast: toastMock,
        $toast: toastMock,
        $confirm: confirmationMock
      },
      mocks: {
        ...primeVueOptions.global.mocks,
        $toast: toastMock,
        $confirm: confirmationMock,
        ...(options.mocks || {})
      }
    },
    // カスタムオプション
    ...options.mountOptions
  }
}

/**
 * FileUploaderコンポーネント専用のマウントヘルパー
 */
export async function mountFileUploader(options = {}) {
  // TasksStoreのモック作成
  const tasksStore = createTasksStoreMock(options.tasksStore || {})

  // マウントオプション作成
  const mountOptions = createIntegratedMountOptions({
    piniaState: {
      tasks: tasksStore
    },
    mocks: {
      // useTasksStoreのモック
      useTasksStore: () => tasksStore,
      ...options.mocks
    },
    mountOptions: options.mountOptions
  })

  //動的インポートでコンポーネント取得
  const FileUploader = (await import('@/components/FileUploader.vue')).default

  // マウント
  const wrapper = mount(FileUploader, mountOptions)

  return {
    wrapper,
    tasksStore,
    toastMock: mountOptions.global.mocks.$toast,
    confirmationMock: mountOptions.global.mocks.$confirm
  }
}

/**
 * 軽量テスト用のマウントヘルパー（スタブ使用）
 */
export function mountComponentWithStubs(component, options = {}) {
  const defaultStubs = {
    Card: true,
    Button: true,
    FileUpload: true,
    ProgressBar: true,
    Badge: true,
    Dialog: true,
    DataTable: true,
    Column: true,
    Teleport: true
  }

  const mountOptions = {
    global: {
      plugins: [createTestPinia()],
      stubs: {
        ...defaultStubs,
        ...(options.stubs || {})
      },
      mocks: {
        $toast: createToastMock(),
        $confirm: createConfirmationMock(),
        ...(options.mocks || {})
      }
    },
    ...options.mountOptions
  }

  return mount(component, mountOptions)
}

/**
 * イベントテスト用のヘルパー関数
 */
export class EventTestHelper {
  constructor(wrapper) {
    this.wrapper = wrapper
  }

  // ファイル選択イベントのシミュレート
  async simulateFileSelect(files) {
    const fileInput = this.wrapper.find('input[type="file"]')
    if (!fileInput.exists()) {
      throw new Error('File input not found')
    }

    const event = new Event('change')
    Object.defineProperty(event, 'target', {
      value: { files },
      enumerable: true
    })

    await fileInput.trigger('change')
    await nextTick()
    return event
  }

  // ドラッグ&ドロップイベントのシミュレート
  async simulateDragAndDrop(files, target = '.upload-dropzone') {
    const dropZone = this.wrapper.find(target)
    if (!dropZone.exists()) {
      throw new Error(`Drop zone ${target} not found`)
    }

    // DragEnter
    await dropZone.trigger('dragenter', {
      dataTransfer: {
        types: ['Files'],
        files
      }
    })

    // DragOver
    await dropZone.trigger('dragover', {
      dataTransfer: {
        types: ['Files'],
        files,
        dropEffect: 'copy'
      }
    })

    // Drop
    await dropZone.trigger('drop', {
      dataTransfer: {
        files,
        types: ['Files']
      }
    })

    await nextTick()
  }

  // ボタンクリックのシミュレート
  async clickButton(selector) {
    const button = this.wrapper.find(selector)
    if (!button.exists()) {
      throw new Error(`Button ${selector} not found`)
    }

    await button.trigger('click')
    await nextTick()
  }

  // フォーム送信のシミュレート
  async submitForm(selector = 'form') {
    const form = this.wrapper.find(selector)
    if (!form.exists()) {
      throw new Error(`Form ${selector} not found`)
    }

    await form.trigger('submit')
    await nextTick()
  }
}

/**
 * アサーションヘルパー関数
 */
export class AssertionHelper {
  constructor(wrapper, mocks = {}) {
    this.wrapper = wrapper
    this.mocks = mocks
  }

  // トースト表示の確認
  expectToastCalled(severity, summary, detail) {
    expect(this.mocks.toastMock?.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity,
        summary,
        detail,
        life: expect.any(Number)
      })
    )
  }

  // コンポーネントの存在確認
  expectElementExists(selector) {
    expect(this.wrapper.find(selector).exists()).toBe(true)
  }

  // コンポーネントの非存在確認
  expectElementNotExists(selector) {
    expect(this.wrapper.find(selector).exists()).toBe(false)
  }

  // テキスト内容の確認
  expectTextContent(selector, expectedText) {
    const element = this.wrapper.find(selector)
    expect(element.exists()).toBe(true)
    expect(element.text()).toContain(expectedText)
  }

  // プロップの確認
  expectComponentProp(selector, propName, expectedValue) {
    const component = this.wrapper.findComponent(selector)
    expect(component.exists()).toBe(true)
    expect(component.props(propName)).toEqual(expectedValue)
  }

  // イベント発火の確認
  expectEventEmitted(eventName, expectedPayload) {
    const emittedEvents = this.wrapper.emitted(eventName)
    expect(emittedEvents).toBeTruthy()
    if (expectedPayload !== undefined) {
      expect(emittedEvents[emittedEvents.length - 1]).toEqual([expectedPayload])
    }
  }

  // ストアアクションの呼び出し確認
  expectStoreActionCalled(store, actionName, ...expectedArgs) {
    const action = store[actionName]
    expect(action).toHaveBeenCalledWith(...expectedArgs)
  }

  // ストア状態の確認
  expectStoreState(store, expectedState) {
    Object.entries(expectedState).forEach(([key, value]) => {
      expect(store[key]).toEqual(value)
    })
  }
}

/**
 * 非同期テストのヘルパー関数
 */
export async function waitForAsyncUpdates(times = 1) {
  for (let i = 0; i < times; i++) {
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 0))
  }
}

/**
 * 条件待機のヘルパー関数
 */
export async function waitForCondition(
  conditionFn,
  timeout = 5000,
  interval = 100
) {
  const startTime = Date.now()

  while (Date.now() - startTime < timeout) {
    if (conditionFn()) {
      return true
    }
    await new Promise(resolve => setTimeout(resolve, interval))
  }

  throw new Error(`Condition not met within ${timeout}ms`)
}

/**
 * ファイルモック作成ヘルパー
 */
export function createMockFiles(fileConfigs) {
  return fileConfigs.map(config => {
    const {
      name = 'test.mp4',
      size = 1024 * 1024,
      type = 'video/mp4',
      content = 'mock file content'
    } = config

    return new File([content], name, { type, size })
  })
}

/**
 * テスト用のカスタムマッチャー
 */
export const customMatchers = {
  toBeInDocument: received => {
    const pass =
      received && document.body.contains(received.element || received)
    return {
      pass,
      message: () =>
        pass
          ? 'Expected element not to be in document'
          : 'Expected element to be in document'
    }
  },

  toHaveClasses: (received, expectedClasses) => {
    const element = received.element || received
    const classList = Array.from(element.classList)
    const pass = expectedClasses.every(cls => classList.includes(cls))

    return {
      pass,
      message: () =>
        pass
          ? `Expected element not to have classes: ${expectedClasses.join(', ')}`
          : `Expected element to have classes: ${expectedClasses.join(', ')}. Actual: ${classList.join(', ')}`
    }
  },

  toEmitEvent: (received, eventName, payload) => {
    const emitted = received.emitted(eventName)
    const pass = emitted && emitted.length > 0

    if (pass && payload !== undefined) {
      const lastEmission = emitted[emitted.length - 1]
      return {
        pass: JSON.stringify(lastEmission[0]) === JSON.stringify(payload),
        message: () =>
          `Expected event ${eventName} to be emitted with payload ${JSON.stringify(payload)}`
      }
    }

    return {
      pass,
      message: () =>
        pass
          ? `Expected event ${eventName} not to be emitted`
          : `Expected event ${eventName} to be emitted`
    }
  }
}

// カスタムマッチャーを拡張
expect.extend(customMatchers)
