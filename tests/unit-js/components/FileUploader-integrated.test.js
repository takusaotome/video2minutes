import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'
import {
  mountFileUploader,
  EventTestHelper,
  AssertionHelper,
  waitForAsyncUpdates
} from '../test-setup/vue-integration.js'

describe('FileUploader - 統合テスト', () => {
  let wrapper
  let tasksStore
  let toastMock
  let eventHelper
  let assertHelper

  beforeEach(async () => {
    const mountResult = await mountFileUploader({
      tasksStore: {
        state: {
          tasks: [],
          loading: false,
          error: null
        }
      }
    })

    wrapper = mountResult.wrapper
    tasksStore = mountResult.tasksStore
    toastMock = mountResult.toastMock

    eventHelper = new EventTestHelper(wrapper)
    assertHelper = new AssertionHelper(wrapper, { toastMock })
  })

  afterEach(() => {
    wrapper?.unmount()
    vi.clearAllMocks()
  })

  describe('初期状態', () => {
    it('コンポーネントが正しくレンダリングされる', () => {
      expect(wrapper.exists()).toBe(true)
      assertHelper.expectElementExists('.file-uploader')
    })

    it('初期状態では選択されたファイルがない', () => {
      expect(wrapper.vm.selectedFiles).toEqual([])
      expect(wrapper.vm.uploadProgress).toEqual([])
    })

    it('ドラッグオーバー状態が正しく初期化される', () => {
      expect(wrapper.vm.isDragOver).toBe(false)
      expect(wrapper.vm.isDragging).toBe(false)
    })
  })

  describe('ファイル選択', () => {
    it('ファイル選択時に selectedFiles が更新される', async () => {
      const files = [global.testUtils.createMockFile({ name: 'test1.mp4' })]

      // ファイル選択イベントをシミュレート
      wrapper.vm.onSelect({ files })
      await nextTick()

      expect(wrapper.vm.selectedFiles).toHaveLength(1)
      expect(wrapper.vm.selectedFiles[0].name).toBe('test1.mp4')
    })

    it('ファイルクリア時に selectedFiles が空になる', async () => {
      // 先にファイルを選択
      const files = [global.testUtils.createMockFile()]
      wrapper.vm.onSelect({ files })
      await nextTick()

      // クリア実行
      wrapper.vm.onClear()
      await nextTick()

      expect(wrapper.vm.selectedFiles).toEqual([])
      expect(wrapper.vm.uploadProgress).toEqual([])
    })

    it('個別ファイル削除が正しく動作する', async () => {
      // 複数ファイルを選択
      const files = [
        global.testUtils.createMockFile({ name: 'test1.mp4' }),
        global.testUtils.createMockFile({ name: 'test2.mp4' })
      ]
      wrapper.vm.onSelect({ files })
      await nextTick()

      // 最初のファイルを削除
      wrapper.vm.removeFile(files[0])
      await nextTick()

      expect(wrapper.vm.selectedFiles).toHaveLength(1)
      expect(wrapper.vm.selectedFiles[0].name).toBe('test2.mp4')
    })
  })

  describe('ファイルアップロード', () => {
    it('ファイルが選択されていない場合は警告を表示', async () => {
      await wrapper.vm.startUpload()
      await waitForAsyncUpdates()

      assertHelper.expectToastCalled(
        'warn',
        '警告',
        'アップロードするファイルを選択してください'
      )
    })

    it('正常なアップロード処理', async () => {
      const file = global.testUtils.createMockFile({ name: 'test.mp4' })
      wrapper.vm.onSelect({ files: [file] })
      await nextTick()

      await wrapper.vm.startUpload()
      await waitForAsyncUpdates()

      expect(tasksStore.uploadFile).toHaveBeenCalledWith(
        file,
        expect.any(Function)
      )
      assertHelper.expectToastCalled(
        'success',
        'アップロード完了',
        expect.stringContaining('test.mp4')
      )
    })

    it('アップロード中はローディング状態になる', async () => {
      const file = global.testUtils.createMockFile()
      wrapper.vm.onSelect({ files: [file] })
      await nextTick()

      // アップロードを開始（完了を待たずに状態確認）
      const uploadPromise = wrapper.vm.startUpload()
      await nextTick()

      expect(wrapper.vm.loading).toBe(true)

      // アップロード完了を待つ
      await uploadPromise
      await waitForAsyncUpdates()

      expect(wrapper.vm.loading).toBe(false)
    })

    it('アップロードエラー時の処理', async () => {
      const file = global.testUtils.createMockFile()
      const error = new Error('Upload failed')

      // アップロードを失敗させる
      tasksStore.uploadFile.mockRejectedValueOnce(error)

      wrapper.vm.onSelect({ files: [file] })
      await nextTick()

      await wrapper.vm.startUpload()
      await waitForAsyncUpdates()

      assertHelper.expectToastCalled(
        'error',
        'アップロードエラー',
        expect.stringContaining('Upload failed')
      )
    })

    it('進捗状況が正しく更新される', async () => {
      const file = global.testUtils.createMockFile()
      let progressCallback

      // 進捗コールバックをキャプチャ
      tasksStore.uploadFile.mockImplementation((file, callback) => {
        progressCallback = callback
        return new Promise(resolve => {
          setTimeout(() => resolve({ task_id: 'test-123' }), 100)
        })
      })

      wrapper.vm.onSelect({ files: [file] })
      await nextTick()

      const uploadPromise = wrapper.vm.startUpload()
      await nextTick()

      // 進捗を更新
      progressCallback(50)
      await nextTick()

      expect(wrapper.vm.uploadProgress[0].percent).toBe(50)

      await uploadPromise
    })
  })

  describe('ドラッグ&ドロップ', () => {
    it('ドラッグエンター時の状態変更', async () => {
      const dragEvent = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        dataTransfer: {
          types: ['Files']
        }
      }

      wrapper.vm.onDragEnter(dragEvent)
      await nextTick()

      expect(wrapper.vm.isDragOver).toBe(true)
      expect(wrapper.vm.isDragging).toBe(true)
    })

    it('有効な動画ファイルのドロップ', async () => {
      const files = [
        global.testUtils.createMockFile({
          name: 'video.mp4',
          type: 'video/mp4'
        })
      ]
      const dropEvent = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        dataTransfer: { files }
      }

      wrapper.vm.onDrop(dropEvent)
      await nextTick()

      expect(wrapper.vm.selectedFiles).toHaveLength(1)
      expect(wrapper.vm.selectedFiles[0].name).toBe('video.mp4')
      assertHelper.expectToastCalled(
        'success',
        'ファイル追加完了',
        '1個のファイルが追加されました'
      )
    })

    it('無効なファイル形式のドロップ', async () => {
      const files = [
        global.testUtils.createMockFile({
          name: 'document.pdf',
          type: 'application/pdf'
        })
      ]
      const dropEvent = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn(),
        dataTransfer: { files }
      }

      wrapper.vm.onDrop(dropEvent)
      await nextTick()

      expect(wrapper.vm.selectedFiles).toHaveLength(0)
      assertHelper.expectToastCalled(
        'warn',
        '無効なファイル形式',
        '動画ファイルのみアップロード可能です'
      )
    })
  })

  describe('ユーティリティ関数', () => {
    it('ファイルサイズのフォーマット', () => {
      expect(wrapper.vm.formatFileSize(0)).toBe('0 Bytes')
      expect(wrapper.vm.formatFileSize(1024)).toBe('1 KB')
      expect(wrapper.vm.formatFileSize(1024 * 1024)).toBe('1 MB')
      expect(wrapper.vm.formatFileSize(1024 * 1024 * 1024)).toBe('1 GB')
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
      expect(wrapper.vm.getStatusLabel('unknown')).toBe('unknown')
    })
  })

  describe('イベント発火', () => {
    it('アップロード開始時にイベントを発火', async () => {
      const file = global.testUtils.createMockFile()
      wrapper.vm.onSelect({ files: [file] })
      await nextTick()

      await wrapper.vm.startUpload()
      await waitForAsyncUpdates()

      const emittedEvents = wrapper.emitted('upload-started')
      expect(emittedEvents).toBeTruthy()
      expect(emittedEvents[0][0]).toEqual({ file })
    })

    it('アップロード完了時にイベントを発火', async () => {
      const file = global.testUtils.createMockFile()
      const mockTask = { task_id: 'test-123' }
      tasksStore.uploadFile.mockResolvedValue(mockTask)

      wrapper.vm.onSelect({ files: [file] })
      await nextTick()

      await wrapper.vm.startUpload()
      await waitForAsyncUpdates()

      const emittedEvents = wrapper.emitted('upload-completed')
      expect(emittedEvents).toBeTruthy()
      expect(emittedEvents[0][0]).toEqual({ file, task: mockTask })
    })

    it('アップロードエラー時にイベントを発火', async () => {
      const file = global.testUtils.createMockFile()
      const error = new Error('Upload failed')
      tasksStore.uploadFile.mockRejectedValue(error)

      wrapper.vm.onSelect({ files: [file] })
      await nextTick()

      await wrapper.vm.startUpload()
      await waitForAsyncUpdates()

      const emittedEvents = wrapper.emitted('upload-error')
      expect(emittedEvents).toBeTruthy()
      expect(emittedEvents[0][0]).toEqual({ file, error })
    })
  })
})
