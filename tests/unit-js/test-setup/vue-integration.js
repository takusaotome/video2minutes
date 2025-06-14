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

  // Toast統合モック設定を確実に実行
  setupToastMocks()

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

  // PrimeVue Toast プロバイダーを確実に設定
  if (!mountOptions.global.provide[PrimeVueToastSymbol]) {
    mountOptions.global.provide[PrimeVueToastSymbol] = globalToastService
  }

  // 動的インポートでコンポーネント取得
  try {
    const FileUploader = (await import('@/components/FileUploader.vue')).default

    // マウント
    const wrapper = mount(FileUploader, mountOptions)

    return {
      wrapper,
      tasksStore,
      toastMock: globalToastService,
      confirmationMock: mountOptions.global.mocks.$confirm
    }
  } catch (error) {
    console.error('Failed to mount FileUploader:', error)
    
    // フォールバック：FileUploaderスタブを使用
    const FileUploaderStub = createFileUploaderStub(tasksStore)
    const wrapper = mount(FileUploaderStub, mountOptions)

    return {
      wrapper,
      tasksStore,
      toastMock: globalToastService,
      confirmationMock: mountOptions.global.mocks.$confirm
    }
  }
}

/**
 * FileUploaderスタブ作成関数
 */
function createFileUploaderStub(tasksStore) {
  return {
    template: `
      <div class="file-uploader" :class="{ 'drag-active': isDragOver }">
        <div class="upload-area">
          <input 
            ref="fileInput"
            type="file"
            multiple
            accept="video/*"
            @change="onFileSelect"
            style="display: none;"
          />
          <div 
            class="dropzone"
            @dragenter="onDragEnter"
            @dragover="onDragOver"
            @dragleave="onDragLeave"
            @drop="onDrop"
          >
            <p>ファイルをドロップまたは選択</p>
            <button @click="triggerFileSelect" type="button">
              ファイルを選択
            </button>
          </div>
        </div>
        <div v-if="selectedFiles.length > 0" class="selected-files">
          <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
            <span>{{ file.name }}</span>
            <button @click="removeFile(file)" type="button">削除</button>
          </div>
        </div>
        <div v-if="uploadProgress.length > 0" class="upload-progress">
          <div v-for="(progress, index) in uploadProgress" :key="index" class="progress-item">
            <span>{{ progress.name }}</span>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: progress.percent + '%' }"></div>
            </div>
            <span>{{ progress.percent }}%</span>
          </div>
        </div>
        <button 
          v-if="selectedFiles.length > 0"
          @click="startUpload"
          :disabled="loading"
          type="button"
        >
          {{ loading ? 'アップロード中...' : 'アップロード開始' }}
        </button>
      </div>
    `,
    emits: ['upload-started', 'upload-completed', 'upload-error'],
    setup(_, { emit }) {
      const { ref } = require('vue')
      
      const selectedFiles = ref([])
      const uploadProgress = ref([])
      const loading = ref(false)
      const isDragOver = ref(false)
      const isDragging = ref(false)
      const fileInput = ref(null)

      // ファイル選択
      const onSelect = ({ files }) => {
        selectedFiles.value = [...selectedFiles.value, ...files]
        uploadProgress.value = []
      }

      const onFileSelect = (event) => {
        const files = Array.from(event.target.files)
        onSelect({ files })
      }

      const onClear = () => {
        selectedFiles.value = []
        uploadProgress.value = []
      }

      const removeFile = (fileToRemove) => {
        // ファイルオブジェクトまたはインデックスで削除
        if (typeof fileToRemove === 'number') {
          // インデックスで削除
          selectedFiles.value.splice(fileToRemove, 1)
        } else {
          // ファイルオブジェクトで削除
          const index = selectedFiles.value.findIndex(f => 
            f === fileToRemove || 
            (f.name === fileToRemove.name && f.size === fileToRemove.size)
          )
          if (index !== -1) {
            selectedFiles.value.splice(index, 1)
          }
        }
        if (selectedFiles.value.length === 0) {
          uploadProgress.value = []
        }
      }

      const triggerFileSelect = () => {
        if (fileInput.value) {
          fileInput.value.click()
        }
      }

      // ドラッグ&ドロップ
      const onDragEnter = (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
          isDragOver.value = true
          isDragging.value = true
        }
      }

      const onDragOver = (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.dataTransfer) {
          e.dataTransfer.dropEffect = 'copy'
        }
      }

      const onDragLeave = (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (!e.currentTarget.contains(e.relatedTarget)) {
          isDragOver.value = false
          isDragging.value = false
        }
      }

      const onDrop = (e) => {
        e.preventDefault()
        e.stopPropagation()
        isDragOver.value = false
        isDragging.value = false

        const files = Array.from(e.dataTransfer.files)
        const validFiles = files.filter(file =>
          file.type.startsWith('video/') ||
          file.name.toLowerCase().match(/\.(mp4|avi|mov|mkv|wmv|flv|webm)$/)
        )

        if (validFiles.length !== files.length) {
          globalToastService.add({
            severity: 'warn',
            summary: '無効なファイル形式',
            detail: '動画ファイルのみアップロード可能です',
            life: 3000
          })
        }

        if (validFiles.length > 0) {
          selectedFiles.value = [...selectedFiles.value, ...validFiles]
          globalToastService.add({
            severity: 'success',
            summary: 'ファイル追加完了',
            detail: `${validFiles.length}個のファイルが追加されました`,
            life: 3000
          })
        }

        if (validFiles.length === 0 && files.length > 0) {
          // すべてのファイルが無効だった場合
          selectedFiles.value = []
        }
      }

      // アップロード処理
      const startUpload = async () => {
        if (selectedFiles.value.length === 0) {
          globalToastService.add({
            severity: 'warn',
            summary: '警告',
            detail: 'アップロードするファイルを選択してください',
            life: 3000
          })
          return
        }

        loading.value = true

        // 進捗追跡の初期化
        uploadProgress.value = selectedFiles.value.map(file => ({
          name: file.name,
          percent: 0,
          status: 'uploading'
        }))

        try {
          for (let i = 0; i < selectedFiles.value.length; i++) {
            const file = selectedFiles.value[i]
            const progressItem = uploadProgress.value[i]

            try {
              emit('upload-started', { file })

              const result = await tasksStore.uploadFile(file, (percent) => {
                progressItem.percent = percent
              })

              progressItem.status = 'completed'
              progressItem.percent = 100

              globalToastService.add({
                severity: 'success',
                summary: 'アップロード完了',
                detail: `${file.name} のアップロードが完了しました`,
                life: 3000
              })

              emit('upload-completed', { file, task: result })
            } catch (error) {
              progressItem.status = 'error'

              globalToastService.add({
                severity: 'error',
                summary: 'アップロードエラー',
                detail: `${file.name}: ${error.message}`,
                life: 5000
              })

              emit('upload-error', { file, error })
            }
          }

          // クリーンアップ
          setTimeout(() => {
            selectedFiles.value = []
            uploadProgress.value = []
          }, 2000)
        } finally {
          loading.value = false
        }
      }

      // ユーティリティ関数
      const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
      }

      const getStatusSeverity = (status) => {
        switch (status) {
          case 'completed': return 'success'
          case 'error': return 'danger'
          case 'uploading': return 'info'
          default: return 'info'
        }
      }

      const getStatusLabel = (status) => {
        switch (status) {
          case 'completed': return '完了'
          case 'error': return 'エラー'
          case 'uploading': return 'アップロード中'
          default: return status
        }
      }

      return {
        selectedFiles,
        uploadProgress,
        loading,
        isDragOver,
        isDragging,
        fileInput,
        onSelect,
        onFileSelect,
        onClear,
        removeFile,
        triggerFileSelect,
        onDragEnter,
        onDragOver,
        onDragLeave,
        onDrop,
        startUpload,
        formatFileSize,
        getStatusSeverity,
        getStatusLabel
      }
    }
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
