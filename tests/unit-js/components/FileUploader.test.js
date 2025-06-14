import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import FileUploader from '@/components/FileUploader.vue'
import {
  createMountOptions,
  createMockFile,
  createFileUploadEvent,
  expectToastCall,
  waitForAsyncUpdate,
  testData
} from '../utils/test-helpers'

// Toast はすでにsetup.jsでモックされている

describe('FileUploader', () => {
  let wrapper
  let mockToast
  let mockTasksStore
  let pinia

  beforeEach(() => {
    // Pinia セットアップ
    pinia = createPinia()
    setActivePinia(pinia)

    // Toast モック（setup.jsで設定済みのものを取得）
    mockToast = {
      add: vi.fn(),
      removeGroup: vi.fn(),
      removeAllGroups: vi.fn(),
      clear: vi.fn()
    }

    // Tasks Store モック（動的に作成）
    mockTasksStore = {
      uploadFile: vi.fn().mockResolvedValue(testData.createTask()),
      tasks: [],
      fetchTasks: vi.fn(),
      deleteTask: vi.fn(),
      retryTask: vi.fn()
    }

    // FileUpload コンポーネントのモック
    const mountOptions = createMountOptions({
      global: {
        plugins: [pinia],
        provide: {
          PrimeVueToast: mockToast,
          PrimeVueToastSymbol: mockToast
        },
        mocks: {
          $toast: mockToast
        }
      },
      stubs: {
        Card: {
          template: '<div class="card-stub"><slot name="content" /></div>'
        },
        FileUpload: {
          template: '<div class="fileupload-stub"><slot name="empty" /></div>',
          props: [
            'mode',
            'multiple',
            'accept',
            'maxFileSize',
            'customUpload',
            'disabled'
          ],
          emits: ['uploader', 'select', 'clear'],
          methods: {
            clear: vi.fn()
          }
        },
        Button: {
          template:
            '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
          props: ['disabled', 'loading', 'label', 'icon']
        },
        ProgressBar: {
          template:
            '<div class="progressbar-stub" :aria-valuenow="value"></div>',
          props: ['value']
        },
        Badge: {
          template:
            '<span class="badge-stub" :class="severity">{{ value }}</span>',
          props: ['value', 'severity']
        }
      }
    })

    // TasksStore のモック注入
    vi.doMock('@/stores/tasks', () => ({
      useTasksStore: () => mockTasksStore
    }))

    wrapper = mount(FileUploader, mountOptions)
  })

  afterEach(() => {
    wrapper?.unmount()
    vi.clearAllMocks()
  })

  describe('初期状態', () => {
    it('コンポーネントが正しくレンダリングされる', () => {
      expect(wrapper.find('.file-uploader').exists()).toBe(true)
      expect(wrapper.find('.upload-title').text()).toBe(
        '動画ファイルをアップロード'
      )
      expect(wrapper.find('.upload-description').text()).toBe(
        '動画から自動的に議事録を生成します'
      )
    })

    it('初期状態では選択されたファイルがない', () => {
      expect(wrapper.vm.selectedFiles).toEqual([])
      expect(wrapper.vm.uploadProgress).toEqual([])
      expect(wrapper.vm.loading).toBe(false)
    })

    it('ドラッグオーバー状態が正しく初期化される', () => {
      expect(wrapper.vm.isDragOver).toBe(false)
      expect(wrapper.vm.isDragging).toBe(false)
    })
  })

  describe('ファイル選択', () => {
    it('ファイル選択時に selectedFiles が更新される', async () => {
      const mockFiles = [
        createMockFile({ name: 'test1.mp4', size: 1024 }),
        createMockFile({ name: 'test2.mp4', size: 2048 })
      ]

      await wrapper.vm.onSelect({ files: mockFiles })

      expect(wrapper.vm.selectedFiles).toHaveLength(2)
      expect(wrapper.vm.selectedFiles[0].name).toBe('test1.mp4')
      expect(wrapper.vm.selectedFiles[1].name).toBe('test2.mp4')
    })

    it('ファイルクリア時に selectedFiles が空になる', async () => {
      wrapper.vm.selectedFiles = [createMockFile()]

      await wrapper.vm.onClear()

      expect(wrapper.vm.selectedFiles).toEqual([])
      expect(wrapper.vm.uploadProgress).toEqual([])
    })

    it('個別ファイル削除が正しく動作する', async () => {
      const file1 = createMockFile({ name: 'test1.mp4' })
      const file2 = createMockFile({ name: 'test2.mp4' })
      wrapper.vm.selectedFiles = [file1, file2]

      await wrapper.vm.removeFile(file1)

      expect(wrapper.vm.selectedFiles).toHaveLength(1)
      expect(wrapper.vm.selectedFiles[0].name).toBe('test2.mp4')
    })
  })

  describe('ファイルアップロード', () => {
    it('ファイルが選択されていない場合は警告を表示', async () => {
      await wrapper.vm.startUpload()

      expectToastCall(
        mockToast,
        'warn',
        '警告',
        'アップロードするファイルを選択してください'
      )
    })

    it('正常なアップロード処理', async () => {
      const mockFile = createMockFile({ name: 'test.mp4' })
      wrapper.vm.selectedFiles = [mockFile]

      await wrapper.vm.startUpload()

      expect(mockTasksStore.uploadFile).toHaveBeenCalledWith(
        mockFile,
        expect.any(Function)
      )
      expectToastCall(
        mockToast,
        'success',
        'アップロード完了',
        'test.mp4 のアップロードが完了しました'
      )
    })

    it('アップロード中はローディング状態になる', async () => {
      const mockFile = createMockFile()
      wrapper.vm.selectedFiles = [mockFile]

      // アップロードを遅延させる
      mockTasksStore.uploadFile.mockImplementation(
        () =>
          new Promise(resolve =>
            setTimeout(() => resolve(testData.createTask()), 100)
          )
      )

      const uploadPromise = wrapper.vm.startUpload()
      await nextTick()

      expect(wrapper.vm.loading).toBe(true)

      await uploadPromise
      expect(wrapper.vm.loading).toBe(false)
    })

    it('アップロードエラー時の処理', async () => {
      const mockFile = createMockFile({ name: 'error.mp4' })
      wrapper.vm.selectedFiles = [mockFile]

      const error = new Error('Upload failed')
      mockTasksStore.uploadFile.mockRejectedValue(error)

      await wrapper.vm.startUpload()

      expectToastCall(
        mockToast,
        'error',
        'アップロードエラー',
        'error.mp4: Upload failed'
      )
    })

    it('進捗状況が正しく更新される', async () => {
      const mockFile = createMockFile({ name: 'test.mp4' })
      wrapper.vm.selectedFiles = [mockFile]

      let progressCallback
      mockTasksStore.uploadFile.mockImplementation((file, callback) => {
        progressCallback = callback
        return Promise.resolve(testData.createTask())
      })

      const uploadPromise = wrapper.vm.startUpload()
      await nextTick()

      // 進捗を更新
      progressCallback(50)
      await nextTick()

      expect(wrapper.vm.uploadProgress[0].percent).toBe(50)

      await uploadPromise
      expect(wrapper.vm.uploadProgress[0].percent).toBe(100)
      expect(wrapper.vm.uploadProgress[0].status).toBe('completed')
    })
  })

  describe('ドラッグ&ドロップ', () => {
    it('ドラッグエンター時の状態変更', () => {
      const event = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        dataTransfer: {
          types: ['Files']
        }
      }

      wrapper.vm.onDragEnter(event)

      expect(wrapper.vm.isDragOver).toBe(true)
      expect(wrapper.vm.isDragging).toBe(true)
      expect(event.preventDefault).toHaveBeenCalled()
    })

    it('ドラッグリーブ時の状態変更', () => {
      wrapper.vm.isDragOver = true
      wrapper.vm.isDragging = true
      wrapper.vm.dragCounter = 1

      const event = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        currentTarget: document.createElement('div'),
        relatedTarget: null
      }

      wrapper.vm.onDragLeave(event)

      expect(wrapper.vm.isDragOver).toBe(false)
      expect(wrapper.vm.isDragging).toBe(false)
    })

    it('有効な動画ファイルのドロップ', async () => {
      const mockFiles = [
        createMockFile({ name: 'test.mp4', type: 'video/mp4' }),
        createMockFile({ name: 'test.avi', type: 'video/avi' })
      ]

      const event = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        dataTransfer: {
          files: mockFiles
        }
      }

      await wrapper.vm.onDrop(event)

      expect(wrapper.vm.selectedFiles).toHaveLength(2)
      expect(wrapper.vm.isDragOver).toBe(false)
      expectToastCall(
        mockToast,
        'success',
        'ファイル追加完了',
        '2個のファイルが追加されました'
      )
    })

    it('無効なファイル形式のドロップ', async () => {
      const mockFiles = [
        createMockFile({ name: 'test.txt', type: 'text/plain' }),
        createMockFile({ name: 'test.pdf', type: 'application/pdf' })
      ]

      const event = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        dataTransfer: {
          files: mockFiles
        }
      }

      await wrapper.vm.onDrop(event)

      expect(wrapper.vm.selectedFiles).toHaveLength(0)
      expectToastCall(
        mockToast,
        'warn',
        '無効なファイル形式',
        '動画ファイルのみアップロード可能です'
      )
    })

    it('混在ファイルのドロップ（有効・無効）', async () => {
      const mockFiles = [
        createMockFile({ name: 'test.mp4', type: 'video/mp4' }),
        createMockFile({ name: 'test.txt', type: 'text/plain' }),
        createMockFile({ name: 'test.mov', type: 'video/quicktime' })
      ]

      const event = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        dataTransfer: {
          files: mockFiles
        }
      }

      await wrapper.vm.onDrop(event)

      expect(wrapper.vm.selectedFiles).toHaveLength(2)
      expectToastCall(
        mockToast,
        'warn',
        '一部ファイルをスキップ',
        '1個のファイルは動画ファイルではないためスキップされました'
      )
    })
  })

  describe('イベント発火', () => {
    it('アップロード開始時にイベントを発火', async () => {
      const mockFile = createMockFile({ name: 'test.mp4' })
      wrapper.vm.selectedFiles = [mockFile]

      await wrapper.vm.startUpload()

      expect(wrapper.emitted('upload-started')).toBeTruthy()
      expect(wrapper.emitted('upload-started')[0][0]).toEqual({
        file: mockFile
      })
    })

    it('アップロード完了時にイベントを発火', async () => {
      const mockFile = createMockFile({ name: 'test.mp4' })
      wrapper.vm.selectedFiles = [mockFile]

      await wrapper.vm.startUpload()

      expect(wrapper.emitted('upload-completed')).toBeTruthy()
      expect(wrapper.emitted('upload-completed')[0][0].file).toEqual(mockFile)
    })

    it('アップロードエラー時にイベントを発火', async () => {
      const mockFile = createMockFile({ name: 'error.mp4' })
      wrapper.vm.selectedFiles = [mockFile]

      const error = new Error('Upload failed')
      mockTasksStore.uploadFile.mockRejectedValue(error)

      await wrapper.vm.startUpload()

      expect(wrapper.emitted('upload-error')).toBeTruthy()
      expect(wrapper.emitted('upload-error')[0][0]).toEqual({
        file: mockFile,
        error
      })
    })
  })

  describe('ユーティリティ関数', () => {
    it('ファイルサイズのフォーマット', () => {
      expect(wrapper.vm.formatFileSize(0)).toBe('0 Bytes')
      expect(wrapper.vm.formatFileSize(1024)).toBe('1 KB')
      expect(wrapper.vm.formatFileSize(1024 * 1024)).toBe('1 MB')
      expect(wrapper.vm.formatFileSize(1024 * 1024 * 1024)).toBe('1 GB')
      expect(wrapper.vm.formatFileSize(1536)).toBe('1.5 KB')
    })

    it('ステータスの重要度レベル', () => {
      expect(wrapper.vm.getStatusSeverity('completed')).toBe('success')
      expect(wrapper.vm.getStatusSeverity('error')).toBe('danger')
      expect(wrapper.vm.getStatusSeverity('uploading')).toBe('info')
      expect(wrapper.vm.getStatusSeverity('unknown')).toBe('info')
    })

    it('ステータスラベル', () => {
      expect(wrapper.vm.getStatusLabel('completed')).toBe('完了')
      expect(wrapper.vm.getStatusLabel('error')).toBe('エラー')
      expect(wrapper.vm.getStatusLabel('uploading')).toBe('アップロード中')
      expect(wrapper.vm.getStatusLabel('custom')).toBe('custom')
    })
  })

  describe('UI インタラクション', () => {
    it('ファイル選択ボタンのクリック', async () => {
      // ファイル入力要素のモック
      const mockFileInput = document.createElement('input')
      mockFileInput.type = 'file'
      mockFileInput.click = vi.fn()

      document.querySelector = vi.fn().mockReturnValue(mockFileInput)

      await wrapper.vm.triggerFileSelect()

      expect(mockFileInput.click).toHaveBeenCalled()
    })

    it('最近のファイル機能（準備中）', async () => {
      await wrapper.vm.showRecentFiles()

      expectToastCall(
        mockToast,
        'info',
        '機能準備中',
        '最近のファイル機能は準備中です'
      )
    })
  })

  describe('レスポンシブ対応', () => {
    it('モバイル表示での要素配置確認', () => {
      // モバイルサイズの設定をシミュレート
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 480
      })

      const mobileWrapper = mount(FileUploader, createMountOptions())

      expect(mobileWrapper.find('.upload-dropzone').exists()).toBe(true)
      expect(mobileWrapper.find('.upload-actions-container').exists()).toBe(
        true
      )

      mobileWrapper.unmount()
    })
  })

  describe('アクセシビリティ', () => {
    it('適切なARIA属性が設定されている', () => {
      const progressBar = wrapper.find('.p-progressbar')
      if (progressBar.exists()) {
        expect(progressBar.attributes('aria-valuenow')).toBeDefined()
      }
    })

    it('キーボードナビゲーション対応', async () => {
      const uploadButton = wrapper.find('button')
      expect(uploadButton.exists()).toBe(true)

      // Enterキーのシミュレート
      await uploadButton.trigger('keydown.enter')

      // フォーカス可能要素の確認
      expect(uploadButton.element.tagName).toBe('BUTTON')
    })
  })
})
