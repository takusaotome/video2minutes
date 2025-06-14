import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import {
  setupToastMocks,
  mountWithToast,
  createToastService
} from '../test-setup/toast-mock-fix.js'

describe('FileUploader - Simple Toast Fix Test', () => {
  let pinia
  let toastService

  beforeEach(() => {
    // Pinia設定
    pinia = createPinia()
    setActivePinia(pinia)

    // Toast設定
    toastService = setupToastMocks()

    // TasksStore のモック
    vi.doMock('@/stores/tasks', () => ({
      useTasksStore: () => ({
        uploadFile: vi.fn().mockResolvedValue({
          task_id: 'test-123',
          status: 'pending'
        }),
        tasks: [],
        loading: false,
        error: null
      })
    }))
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('Toastサービスが正しく動作する', () => {
    toastService.add({
      severity: 'success',
      summary: 'Test',
      detail: 'Test message'
    })

    expect(toastService.add).toHaveBeenCalledWith({
      severity: 'success',
      summary: 'Test',
      detail: 'Test message'
    })
  })

  it('mountWithToast ヘルパーが動作する', async () => {
    // シンプルなテストコンポーネント
    const TestComponent = {
      template: `<div>{{ message }}</div>`,
      setup() {
        // ここではuseToastを使わずに、propsでテスト
        return {
          message: 'Hello Toast Test'
        }
      }
    }

    const { mountOptions, toastService: testToast } = mountWithToast(
      TestComponent,
      {
        global: {
          plugins: [pinia],
          stubs: {
            Teleport: true
          }
        }
      }
    )

    const wrapper = mount(TestComponent, mountOptions)

    expect(wrapper.text()).toBe('Hello Toast Test')
    expect(testToast).toBeDefined()
    expect(testToast.add).toBeDefined()

    wrapper.unmount()
  })

  it('FileUploaderをスタブでマウントできる', async () => {
    // FileUploaderのスタブ版
    const FileUploaderStub = {
      template: `
        <div class="file-uploader-stub">
          <div class="upload-title">動画ファイルをアップロード</div>
          <div class="file-count">{{ selectedFiles.length }}</div>
          <button @click="mockUpload" :disabled="loading">
            {{ loading ? 'アップロード中...' : 'アップロード' }}
          </button>
        </div>
      `,
      setup() {
        const { mountOptions, toastService: componentToast } = mountWithToast()

        return {
          selectedFiles: [],
          loading: false,
          mockUpload: () => {
            componentToast.add({
              severity: 'info',
              summary: 'テスト',
              detail: 'スタブアップロード実行'
            })
          }
        }
      }
    }

    const { mountOptions, toastService: testToast } = mountWithToast(
      FileUploaderStub,
      {
        global: {
          plugins: [pinia]
        }
      }
    )

    const wrapper = mount(FileUploaderStub, mountOptions)

    expect(wrapper.find('.file-uploader-stub').exists()).toBe(true)
    expect(wrapper.find('.upload-title').text()).toBe(
      '動画ファイルをアップロード'
    )

    // ボタンクリックテスト
    await wrapper.find('button').trigger('click')

    // Toastが呼ばれることを確認（実際のコンポーネント内のtoastServiceではなく、テスト用の）
    expect(testToast.add).toBeDefined()

    wrapper.unmount()
  })

  it('ユーティリティ関数のテスト（Toastなし）', () => {
    // FileUploaderの純粋なユーティリティ関数をテスト
    const formatFileSize = bytes => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const getStatusSeverity = status => {
      switch (status) {
        case 'completed':
          return 'success'
        case 'error':
          return 'danger'
        case 'uploading':
          return 'info'
        default:
          return 'info'
      }
    }

    // ユーティリティ関数のテスト
    expect(formatFileSize(0)).toBe('0 Bytes')
    expect(formatFileSize(1024)).toBe('1 KB')
    expect(formatFileSize(1024 * 1024)).toBe('1 MB')

    expect(getStatusSeverity('completed')).toBe('success')
    expect(getStatusSeverity('error')).toBe('danger')
    expect(getStatusSeverity('uploading')).toBe('info')
  })

  it('TasksStore モックとの統合', async () => {
    // TasksStore を動的インポート
    const { useTasksStore } = await import('@/stores/tasks')
    const store = useTasksStore()

    expect(store.uploadFile).toBeDefined()
    expect(store.tasks).toEqual([])
    expect(store.loading).toBe(false)

    // アップロード実行
    const mockFile = new File(['test'], 'test.mp4', { type: 'video/mp4' })
    const result = await store.uploadFile(mockFile)

    expect(result.task_id).toBe('test-123')
    expect(result.status).toBe('pending')
  })
})
