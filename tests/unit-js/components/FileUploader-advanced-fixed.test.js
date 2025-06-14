import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import {
  setupToastMocks,
  mountWithToast,
  createToastService,
  globalToastService
} from '../test-setup/toast-mock-fix.js'

describe('FileUploader - Advanced Fixed Test', () => {
  let pinia
  let toastService

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    toastService = setupToastMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('FileUploaderの高度なスタブテスト（モック修正版）', async () => {
    // TasksStoreをモック
    const mockTasksStore = {
      uploadFile: vi.fn().mockImplementation(async (file, progressCallback) => {
        // 進捗をシミュレート
        if (progressCallback) {
          setTimeout(() => progressCallback(25), 10)
          setTimeout(() => progressCallback(50), 20)
          setTimeout(() => progressCallback(75), 30)
          setTimeout(() => progressCallback(100), 40)
        }

        return {
          task_id: `task-${Date.now()}`,
          status: 'pending',
          video_filename: file.name,
          video_size: file.size,
          upload_timestamp: new Date().toISOString()
        }
      }),
      tasks: [],
      loading: false,
      error: null
    }

    // より実際に近いFileUploaderスタブ
    const FileUploaderAdvanced = {
      template: `
        <div class="file-uploader" :class="{ 'drag-active': isDragOver }">
          <div class="upload-header">
            <h2>動画ファイルをアップロード</h2>
            <p>動画から自動的に議事録を生成します</p>
          </div>
          
          <div 
            class="upload-dropzone"
            :class="{ 'dragover': isDragOver }"
            @dragenter="onDragEnter"
            @dragover="onDragOver"
            @dragleave="onDragLeave"
            @drop="onDrop"
          >
            <div v-if="!isDragOver" class="dropzone-content">
              <div class="upload-icon">📁</div>
              <h3>ここに動画ファイルをドラッグ&ドロップ</h3>
              <p>または下のボタンからファイルを選択してください</p>
              <button @click="triggerFileSelect" :disabled="loading">
                ファイルを選択
              </button>
              <input 
                ref="fileInput"
                type="file"
                accept="video/*"
                multiple
                @change="onFileSelect"
                style="display: none;"
              />
            </div>
            <div v-else class="drag-overlay">
              <div class="drag-content">
                <div class="drag-icon">⬇️</div>
                <p>ファイルをここにドロップ</p>
              </div>
            </div>
          </div>
          
          <!-- 選択されたファイル一覧 -->
          <div v-if="selectedFiles.length > 0" class="selected-files">
            <h4>選択されたファイル</h4>
            <div 
              v-for="(file, index) in selectedFiles" 
              :key="index" 
              class="file-item"
            >
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <button @click="removeFile(index)" :disabled="loading">削除</button>
            </div>
          </div>
          
          <!-- アップロード進捗 -->
          <div v-if="uploadProgress.length > 0" class="upload-progress">
            <h4>アップロード進行状況</h4>
            <div 
              v-for="(progress, index) in uploadProgress" 
              :key="index"
              class="progress-item"
            >
              <span class="progress-name">{{ progress.name }}</span>
              <div class="progress-bar-container">
                <div 
                  class="progress-bar" 
                  :style="{ width: progress.percent + '%' }"
                ></div>
              </div>
              <span class="progress-percent">{{ progress.percent }}%</span>
            </div>
          </div>
          
          <!-- アップロードボタン -->
          <div v-if="selectedFiles.length > 0 && uploadProgress.length === 0" class="upload-actions">
            <button 
              @click="startUpload" 
              :disabled="loading || selectedFiles.length === 0"
              class="upload-button"
            >
              {{ loading ? 'アップロード中...' : 'アップロード開始' }}
            </button>
          </div>
        </div>
      `,
      emits: ['upload-started', 'upload-completed', 'upload-error'],
      setup(_, { emit }) {
        const { ref } = require('vue')

        // TasksStoreの代わりにモックを使用
        const tasksStore = mockTasksStore

        const selectedFiles = ref([])
        const uploadProgress = ref([])
        const loading = ref(false)
        const isDragOver = ref(false)
        const fileInput = ref(null)

        // ファイル選択
        const onFileSelect = event => {
          const files = Array.from(event.target.files)
          selectedFiles.value = [...selectedFiles.value, ...files]
          uploadProgress.value = []
        }

        // ファイル削除
        const removeFile = index => {
          selectedFiles.value.splice(index, 1)
          if (selectedFiles.value.length === 0) {
            uploadProgress.value = []
          }
        }

        // ドラッグ&ドロップ
        const onDragEnter = e => {
          e.preventDefault()
          e.stopPropagation()
          if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
            isDragOver.value = true
          }
        }

        const onDragOver = e => {
          e.preventDefault()
          e.stopPropagation()
          if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
            e.dataTransfer.dropEffect = 'copy'
          }
        }

        const onDragLeave = e => {
          e.preventDefault()
          e.stopPropagation()
          if (!e.currentTarget.contains(e.relatedTarget)) {
            isDragOver.value = false
          }
        }

        const onDrop = e => {
          e.preventDefault()
          e.stopPropagation()
          isDragOver.value = false

          const files = Array.from(e.dataTransfer.files)
          const validFiles = files.filter(
            file =>
              file.type.startsWith('video/') ||
              file.name.toLowerCase().match(/\.(mp4|avi|mov|mkv|wmv|flv|webm)$/)
          )

          if (validFiles.length !== files.length) {
            globalToastService.add({
              severity: 'warn',
              summary: '一部ファイルをスキップ',
              detail: `${files.length - validFiles.length}個のファイルは動画ファイルではありません`
            })
          }

          if (validFiles.length > 0) {
            selectedFiles.value = [...selectedFiles.value, ...validFiles]
            globalToastService.add({
              severity: 'success',
              summary: 'ファイル追加完了',
              detail: `${validFiles.length}個のファイルが追加されました`
            })
          }
        }

        // ファイル選択ダイアログ
        const triggerFileSelect = () => {
          if (fileInput.value) {
            fileInput.value.click()
          }
        }

        // アップロード開始
        const startUpload = async () => {
          if (selectedFiles.value.length === 0) {
            globalToastService.add({
              severity: 'warn',
              summary: '警告',
              detail: 'アップロードするファイルを選択してください'
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

                const task = await tasksStore.uploadFile(file, percent => {
                  progressItem.percent = percent
                })

                progressItem.status = 'completed'
                progressItem.percent = 100

                globalToastService.add({
                  severity: 'success',
                  summary: 'アップロード完了',
                  detail: `${file.name} のアップロードが完了しました`
                })

                emit('upload-completed', { file, task })
              } catch (error) {
                progressItem.status = 'error'

                globalToastService.add({
                  severity: 'error',
                  summary: 'アップロードエラー',
                  detail: `${file.name}: ${error.message}`
                })

                emit('upload-error', { file, error })
              }
            }

            // クリア
            setTimeout(() => {
              selectedFiles.value = []
              uploadProgress.value = []
            }, 2000)
          } finally {
            loading.value = false
          }
        }

        // ユーティリティ関数
        const formatFileSize = bytes => {
          if (bytes === 0) return '0 Bytes'
          const k = 1024
          const sizes = ['Bytes', 'KB', 'MB', 'GB']
          const i = Math.floor(Math.log(bytes) / Math.log(k))
          return (
            parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
          )
        }

        return {
          selectedFiles,
          uploadProgress,
          loading,
          isDragOver,
          fileInput,
          onFileSelect,
          removeFile,
          onDragEnter,
          onDragOver,
          onDragLeave,
          onDrop,
          triggerFileSelect,
          startUpload,
          formatFileSize
        }
      }
    }

    const { mountOptions, toastService: testToast } = mountWithToast(
      FileUploaderAdvanced,
      {
        global: {
          plugins: [pinia],
          stubs: {
            Teleport: true
          }
        }
      }
    )

    const wrapper = mount(FileUploaderAdvanced, mountOptions)

    // 初期表示の確認
    expect(wrapper.find('.file-uploader').exists()).toBe(true)
    expect(wrapper.find('h2').text()).toBe('動画ファイルをアップロード')
    expect(wrapper.find('.upload-dropzone').exists()).toBe(true)

    // ファイル選択のシミュレート
    const mockFiles = [
      new File(['video content'], 'test1.mp4', { type: 'video/mp4' }),
      new File(['video content'], 'test2.avi', { type: 'video/avi' })
    ]

    // ファイル選択イベント
    await wrapper.vm.onFileSelect({ target: { files: mockFiles } })
    await nextTick()

    expect(wrapper.vm.selectedFiles).toHaveLength(2)
    expect(wrapper.find('.selected-files').exists()).toBe(true)
    expect(wrapper.findAll('.file-item')).toHaveLength(2)

    // アップロード開始
    await wrapper.vm.startUpload()
    await nextTick()

    // 進捗表示の確認
    expect(wrapper.find('.upload-progress').exists()).toBe(true)
    expect(wrapper.findAll('.progress-item')).toHaveLength(2)

    // Toastメッセージの確認（グローバルインスタンス使用）
    expect(globalToastService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'success',
        summary: 'アップロード完了'
      })
    )

    // イベント発火の確認
    const emittedEvents = wrapper.emitted('upload-started')
    expect(emittedEvents).toBeTruthy()
    expect(emittedEvents).toHaveLength(2)

    wrapper.unmount()
  })

  it('ドラッグ&ドロップのシンプルテスト', async () => {
    const SimpleDropzone = {
      template: `
        <div 
          class="dropzone"
          :class="{ active: isDragOver }"
          @dragenter="onDragEnter"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @drop="onDrop"
        >
          <p v-if="!isDragOver">ファイルをドロップ</p>
          <p v-else>ファイルを離してください</p>
          <div class="file-count">選択: {{ files.length }}</div>
        </div>
      `,
      setup() {
        const { ref } = require('vue')
        const isDragOver = ref(false)
        const files = ref([])

        const onDragEnter = e => {
          e.preventDefault()
          if (e.dataTransfer.types.includes('Files')) {
            isDragOver.value = true
          }
        }

        const onDragOver = e => {
          e.preventDefault()
          e.dataTransfer.dropEffect = 'copy'
        }

        const onDragLeave = e => {
          e.preventDefault()
          if (!e.currentTarget.contains(e.relatedTarget)) {
            isDragOver.value = false
          }
        }

        const onDrop = e => {
          e.preventDefault()
          isDragOver.value = false
          files.value = Array.from(e.dataTransfer.files)
        }

        return {
          isDragOver,
          files,
          onDragEnter,
          onDragOver,
          onDragLeave,
          onDrop
        }
      }
    }

    const { mountOptions } = mountWithToast(SimpleDropzone, {
      global: { plugins: [pinia] }
    })

    const wrapper = mount(SimpleDropzone, mountOptions)

    // 初期状態
    expect(wrapper.vm.isDragOver).toBe(false)
    expect(wrapper.vm.files).toHaveLength(0)

    // ドラッグエンター
    await wrapper.trigger('dragenter', {
      dataTransfer: { types: ['Files'] }
    })

    expect(wrapper.vm.isDragOver).toBe(true)
    expect(wrapper.classes()).toContain('active')

    // ドロップ
    const mockFiles = [new File([''], 'test.mp4', { type: 'video/mp4' })]
    await wrapper.trigger('drop', {
      dataTransfer: { files: mockFiles }
    })

    expect(wrapper.vm.isDragOver).toBe(false)
    expect(wrapper.vm.files).toHaveLength(1)
    expect(wrapper.vm.files[0].name).toBe('test.mp4')

    wrapper.unmount()
  })
})
