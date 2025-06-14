<template>
  <div
    class="file-uploader"
    :class="{ 'drag-active': isDragOver }"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <Card class="upload-card">
      <template #content>
        <div class="upload-container">
          <!-- Title Section -->
          <div class="upload-header">
            <div class="title-section">
              <i class="pi pi-cloud-upload title-icon"></i>
              <h2 class="upload-title">動画・音声ファイルをアップロード</h2>
            </div>
            <p class="upload-description">動画・音声から自動的に議事録を生成します</p>
          </div>

          <!-- Upload Area -->
          <div class="upload-area">
            <FileUpload
              ref="fileUpload"
              mode="basic"
              :multiple="true"
              accept="video/*,audio/*,.mp4,.avi,.mov,.mkv,.wmv,.flv,.webm,.mp3,.wav,.m4a,.aac,.flac,.ogg,.wma"
              :maxFileSize="5368709120"
              :customUpload="true"
              @uploader="onUpload"
              @select="onSelect"
              @clear="onClear"
              :disabled="loading"
              chooseLabel="ファイルを選択"
              class="custom-file-upload"
            >
              <template #empty>
                <div class="upload-dropzone" :class="{ dragover: isDragOver }">
                  <!-- Animated Background Elements -->
                  <div class="dropzone-bg-elements">
                    <div class="floating-element element-1"></div>
                    <div class="floating-element element-2"></div>
                    <div class="floating-element element-3"></div>
                  </div>

                  <div class="dropzone-content">
                    <div class="upload-icon-container">
                      <div class="icon-wrapper">
                        <i
                          class="pi pi-cloud-upload upload-icon"
                          :class="{ bounce: isDragOver }"
                        ></i>
                        <div class="icon-glow"></div>
                      </div>
                    </div>

                    <div class="upload-text-container">
                      <h3
                        class="upload-text"
                        :class="{ highlight: isDragOver }"
                      >
                        {{
                          isDragOver
                            ? 'ファイルをここにドロップしてください！'
                            : 'ここに動画・音声ファイルをドラッグ&ドロップ'
                        }}
                      </h3>
                      <p class="upload-subtext">
                        {{
                          isDragOver
                            ? '動画・音声ファイルを離してアップロード開始'
                            : 'または下のボタンからファイルを選択してください'
                        }}
                      </p>
                    </div>

                    <div class="upload-actions-container">
                      <Button
                        label="ファイルを選択"
                        icon="pi pi-folder-open"
                        class="upload-button-primary"
                        :loading="loading"
                        @click="triggerFileSelect"
                      />

                      <div class="divider">
                        <span>または</span>
                      </div>

                      <div class="quick-actions">
                        <Button
                          label="カメラロール"
                          icon="pi pi-image"
                          class="quick-action-btn"
                          @click="openFileDialog('video/*')"
                        />
                        <Button
                          label="最近のファイル"
                          icon="pi pi-clock"
                          class="quick-action-btn"
                          @click="showRecentFiles"
                        />
                      </div>
                    </div>

                    <div class="upload-note">
                      <div class="note-content">
                        <i class="pi pi-info-circle"></i>
                        <div class="note-text">
                          <div class="supported-formats">
                            動画形式: MP4, AVI, MOV, MKV, WMV, FLV, WebM<br>
                            音声形式: MP3, WAV, M4A, AAC, FLAC, OGG, WMA
                          </div>
                          <div class="file-limit">最大ファイルサイズ: 5GB</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Drag & Drop Overlay -->
                  <div v-if="isDragOver" class="drag-overlay">
                    <div class="drag-overlay-content">
                      <i class="pi pi-arrow-down drag-icon"></i>
                      <p>ファイルをここにドロップ</p>
                      <div class="drop-hint">
                        <i class="pi pi-arrow-down drop-arrow"></i>
                        <span>離してアップロード開始</span>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </FileUpload>

            <!-- Selected Files Display -->
            <div v-if="selectedFiles.length > 0" class="selected-files-section">
              <div class="selected-files-header">
                <h4><i class="pi pi-check-circle"></i> 選択されたファイル</h4>
              </div>
              <div class="selected-files-list">
                <div
                  v-for="file in selectedFiles"
                  :key="file.name"
                  class="file-item"
                >
                  <div class="file-info">
                    <div class="file-icon">
                      <i class="pi pi-file-video"></i>
                    </div>
                    <div class="file-details">
                      <span class="file-name">{{ file.name }}</span>
                      <span class="file-size">{{
                        formatFileSize(file.size)
                      }}</span>
                    </div>
                  </div>
                  <Button
                    icon="pi pi-trash"
                    class="p-button-outlined p-button-danger p-button-sm file-remove-btn"
                    @click="removeFile(file)"
                    :disabled="loading"
                    v-tooltip="'ファイルを削除'"
                  />
                </div>
              </div>
            </div>

            <!-- Upload Progress -->
            <div
              v-if="uploadProgress.length > 0"
              class="upload-progress-section"
            >
              <div class="progress-header">
                <h4>
                  <i class="pi pi-spin pi-spinner"></i> アップロード進行状況
                </h4>
              </div>
              <div class="progress-list">
                <div
                  v-for="progress in uploadProgress"
                  :key="progress.name"
                  class="progress-item"
                >
                  <div class="progress-info">
                    <div class="progress-file-info">
                      <span class="progress-name">{{ progress.name }}</span>
                      <span class="progress-percent"
                        >{{ progress.percent }}%</span
                      >
                    </div>
                    <ProgressBar
                      :value="progress.percent"
                      :showValue="false"
                      class="progress-bar"
                    />
                    <div v-if="progress.status" class="progress-status">
                      <Badge
                        :value="getStatusLabel(progress.status)"
                        :severity="getStatusSeverity(progress.status)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Upload Button -->
            <div
              v-if="selectedFiles.length > 0 && uploadProgress.length === 0"
              class="upload-actions"
            >
              <Button
                label="アップロード開始"
                icon="pi pi-upload"
                @click="startUpload"
                :loading="loading"
                :disabled="selectedFiles.length === 0"
                class="upload-start-button"
                size="large"
              />
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useTasksStore } from '@/stores/tasks'
import Card from 'primevue/card'
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import Badge from 'primevue/badge'

export default {
  name: 'FileUploader',
  components: {
    Card,
    FileUpload,
    Button,
    ProgressBar,
    Badge
  },
  emits: ['upload-started', 'upload-completed', 'upload-error'],
  setup(_, { emit }) {
    const toast = useToast()
    const tasksStore = useTasksStore()

    const fileUpload = ref(null)
    const selectedFiles = ref([])
    const uploadProgress = ref([])
    const loading = ref(false)
    const isDragOver = ref(false)
    const isDragging = ref(false)
    const dragCounter = ref(0)

    const onSelect = event => {
      console.log('Files selected:', event.files)
      selectedFiles.value = [...event.files]
      uploadProgress.value = []
    }

    const onClear = () => {
      selectedFiles.value = []
      uploadProgress.value = []
    }

    const removeFile = fileToRemove => {
      selectedFiles.value = selectedFiles.value.filter(
        file => file !== fileToRemove
      )
      if (selectedFiles.value.length === 0) {
        uploadProgress.value = []
      }
    }

    const onUpload = async event => {
      // This is called by PrimeVue's internal upload mechanism
      // We handle uploads manually in startUpload instead
    }

    const startUpload = async () => {
      if (selectedFiles.value.length === 0) {
        toast.add({
          severity: 'warn',
          summary: '警告',
          detail: 'アップロードするファイルを選択してください',
          life: 3000
        })
        return
      }

      loading.value = true

      // Initialize progress tracking
      uploadProgress.value = selectedFiles.value.map(file => ({
        name: file.name,
        percent: 0,
        status: 'uploading'
      }))

      try {
        // Upload files sequentially to avoid overwhelming the server
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

            emit('upload-completed', { file, task })
          } catch (error) {
            progressItem.status = 'error'

            toast.add({
              severity: 'error',
              summary: 'アップロードエラー',
              detail: `${file.name}: ${error.message}`,
              life: 5000
            })

            emit('upload-error', { file, error })
          }
        }

        // Clear files after successful upload
        setTimeout(() => {
          selectedFiles.value = []
          uploadProgress.value = []
          fileUpload.value?.clear()
        }, 2000)
      } finally {
        loading.value = false
      }
    }

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

    const getStatusLabel = status => {
      switch (status) {
        case 'completed':
          return '完了'
        case 'error':
          return 'エラー'
        case 'uploading':
          return 'アップロード中'
        default:
          return status
      }
    }

    const triggerFileSelect = () => {
      try {
        if (
          fileUpload.value &&
          fileUpload.value.$refs &&
          fileUpload.value.$refs.fileInput
        ) {
          fileUpload.value.$refs.fileInput.click()
        } else {
          // Fallback: try to find the file input element
          const fileInput = document.querySelector(
            '.custom-file-upload input[type="file"]'
          )
          if (fileInput) {
            fileInput.click()
          }
        }
      } catch (error) {
        console.warn('Could not trigger file select:', error)
      }
    }

    // Drag & Drop handlers
    const onDragEnter = e => {
      e.preventDefault()
      e.stopPropagation()

      console.log('Drag enter event:', e.dataTransfer?.types)

      // Check if files are being dragged
      if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
        dragCounter.value++
        console.log('Drag counter:', dragCounter.value)
        if (dragCounter.value === 1) {
          isDragOver.value = true
          isDragging.value = true
          console.log('Drag over state set to true')
        }
      }
    }

    const onDragOver = e => {
      e.preventDefault()
      e.stopPropagation()

      if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
        e.dataTransfer.dropEffect = 'copy'
        isDragOver.value = true
      }
    }

    const onDragLeave = e => {
      e.preventDefault()
      e.stopPropagation()

      console.log('Drag leave event', e.relatedTarget)

      // Only reduce counter if leaving the main drop area
      if (!e.currentTarget.contains(e.relatedTarget)) {
        dragCounter.value--
        console.log('Drag counter after leave:', dragCounter.value)
        if (dragCounter.value <= 0) {
          dragCounter.value = 0
          isDragOver.value = false
          isDragging.value = false
          console.log('Drag over state set to false')
        }
      }
    }

    const onDrop = e => {
      e.preventDefault()
      e.stopPropagation()

      console.log('Drop event triggered', e.dataTransfer.files)

      // Reset drag state
      isDragOver.value = false
      isDragging.value = false
      dragCounter.value = 0

      const files = Array.from(e.dataTransfer.files)
      console.log('Dropped files:', files)

      if (files.length > 0) {
        // Validate file types
        const validFiles = files.filter(file => {
          const fileType = file.type
          const fileName = file.name.toLowerCase()

          // Check if it's a video file
          if (fileType.startsWith('video/')) {
            return true
          }

          // Check if it's an audio file
          if (fileType.startsWith('audio/')) {
            return true
          }

          // Check by file extension if MIME type is not reliable
          const supportedExtensions = [
            '.mp4',
            '.avi',
            '.mov',
            '.mkv',
            '.wmv',
            '.flv',
            '.webm',
            '.mp3',
            '.wav',
            '.m4a',
            '.aac',
            '.flac',
            '.ogg',
            '.wma'
          ]
          return supportedExtensions.some(ext => fileName.endsWith(ext))
        })

        if (validFiles.length === 0) {
          toast.add({
            severity: 'warn',
            summary: '無効なファイル形式',
            detail: '動画・音声ファイルのみアップロード可能です',
            life: 3000
          })
          return
        }

        if (validFiles.length !== files.length) {
          toast.add({
            severity: 'warn',
            summary: '一部ファイルをスキップ',
            detail: `${files.length - validFiles.length}個のファイルは動画・音声ファイルではないためスキップされました`,
            life: 4000
          })
        }

        // Add files to selected files
        selectedFiles.value = [...selectedFiles.value, ...validFiles]
        uploadProgress.value = []

        // Update the PrimeVue FileUpload component directly
        if (fileUpload.value && validFiles.length > 0) {
          // Convert File objects to the format expected by PrimeVue
          const formattedFiles = validFiles.map(file => ({
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: file.lastModified,
            objectURL: file // Store the actual file
          }))

          // Set files on the PrimeVue component
          if (fileUpload.value.files) {
            fileUpload.value.files.push(...formattedFiles)
          } else {
            fileUpload.value.files = formattedFiles
          }

          // Trigger the onSelect event manually
          onSelect({ files: validFiles })
        }

        toast.add({
          severity: 'success',
          summary: 'ファイル追加完了',
          detail: `${validFiles.length}個のファイルが追加されました`,
          life: 3000
        })
      }
    }

    const openFileDialog = accept => {
      triggerFileSelect()
    }

    const showRecentFiles = () => {
      toast.add({
        severity: 'info',
        summary: '機能準備中',
        detail: '最近のファイル機能は準備中です',
        life: 3000
      })
    }

    return {
      fileUpload,
      selectedFiles,
      uploadProgress,
      loading,
      onSelect,
      onClear,
      onUpload,
      removeFile,
      startUpload,
      formatFileSize,
      getStatusSeverity,
      getStatusLabel,
      triggerFileSelect,
      isDragOver,
      isDragging,
      onDragEnter,
      onDragOver,
      onDragLeave,
      onDrop,
      openFileDialog,
      showRecentFiles
    }
  }
}
</script>

<style scoped>
.file-uploader {
  margin-bottom: 1rem;
  position: relative;
  transition: all 0.3s ease;
  border-radius: 16px;
}

.file-uploader.drag-active {
  box-shadow: 0 0 40px rgba(16, 185, 129, 0.3);
  transform: scale(1.02);
}

.file-uploader.drag-active .upload-card {
  border: 3px solid var(--success-400);
  box-shadow: 0 10px 30px rgba(16, 185, 129, 0.2);
}

.upload-card {
  border: none;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  overflow: hidden;
}

.upload-container {
  padding: 0;
}

/* Header Section */
.upload-header {
  padding: 20px 20px 16px 20px;
  margin: 0 -20px 16px -20px;
  background: linear-gradient(
    135deg,
    var(--primary-700) 0%,
    var(--secondary-700) 100%
  );
  color: white;
  border-bottom: none;
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  text-align: center;
  position: relative;
  transition: all 0.3s ease;
  overflow: hidden;
}

/* Dark overlay for better text contrast */
.upload-header::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.1);
  pointer-events: none;
}

.upload-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 100" fill="white" opacity="0.1"><polygon points="0,100 1000,0 1000,100"/></svg>')
    no-repeat center bottom;
  background-size: cover;
}

.title-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  position: relative;
  z-index: 2;
}

.title-icon {
  font-size: 2rem;
  opacity: 1;
  color: white;
  position: relative;
  z-index: 2;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.upload-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0;
  line-height: 1.2;
  color: white;
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 2;
}

.upload-description {
  font-size: 1rem;
  opacity: 1;
  margin: 0;
  font-weight: 500;
  color: white;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
  position: relative;
  z-index: 2;
}

/* Upload Area */
.upload-area {
  padding: 0.75rem;
  position: relative;
  border-radius: var(--radius-2xl);
  transition: all 0.3s ease;
}

:deep(.custom-file-upload) {
  width: 100%;
}

:deep(.custom-file-upload .p-fileupload-buttonbar) {
  display: none;
}

:deep(.custom-file-upload .p-fileupload-content) {
  border: none;
  background: none;
  padding: 0;
}

/* Disable PrimeVue's built-in drag and drop */
:deep(.custom-file-upload .p-fileupload-content) {
  pointer-events: auto;
}

.upload-dropzone {
  padding: 32px 20px;
  margin: 0 -20px;
  border: 2px dashed var(--gray-300);
  border-radius: var(--radius-lg);
  background: var(--gray-50);
  transition: all var(--transition-normal);
  text-align: center;
  min-height: 350px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-dropzone::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 10px,
    rgba(99, 102, 241, 0.05) 10px,
    rgba(99, 102, 241, 0.05) 20px
  );
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.upload-dropzone:hover {
  border-color: var(--primary-400);
  background: linear-gradient(
    135deg,
    var(--primary-50) 0%,
    var(--primary-100) 100%
  );
  transform: translateY(-4px);
  box-shadow: 0 20px 40px -12px rgba(99, 102, 241, 0.25);
}

.upload-dropzone:hover::after {
  opacity: 1;
}

.upload-dropzone.dragover {
  border-color: var(--success-500);
  background: linear-gradient(
    135deg,
    var(--success-50) 0%,
    var(--success-100) 100%
  );
  transform: translateY(-6px) scale(1.02);
  box-shadow: 0 25px 50px -12px rgba(16, 185, 129, 0.35);
  border-style: solid;
  border-width: 4px;
  animation: dragPulse 1s ease-in-out infinite;
}

.upload-dropzone.dragover::after {
  opacity: 1;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 10px,
    rgba(16, 185, 129, 0.1) 10px,
    rgba(16, 185, 129, 0.1) 20px
  );
}

@keyframes dragPulse {
  0%,
  100% {
    box-shadow: 0 25px 50px -12px rgba(16, 185, 129, 0.35);
  }
  50% {
    box-shadow: 0 30px 60px -12px rgba(16, 185, 129, 0.45);
  }
}

.upload-dropzone::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.4),
    transparent
  );
  transition: left 0.8s ease-in-out;
}

.upload-dropzone:hover::before {
  left: 100%;
}

/* Floating Background Elements */
.dropzone-bg-elements {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.floating-element {
  position: absolute;
  border-radius: 50%;
  background: linear-gradient(
    45deg,
    rgba(102, 126, 234, 0.1),
    rgba(118, 75, 162, 0.1)
  );
  animation: float 6s ease-in-out infinite;
}

.element-1 {
  width: 80px;
  height: 80px;
  top: 20%;
  left: 10%;
  animation-delay: 0s;
}

.element-2 {
  width: 60px;
  height: 60px;
  top: 60%;
  right: 15%;
  animation-delay: 2s;
}

.element-3 {
  width: 100px;
  height: 100px;
  bottom: 25%;
  left: 15%;
  animation-delay: 4s;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px) rotate(0deg);
  }
  33% {
    transform: translateY(-20px) rotate(120deg);
  }
  66% {
    transform: translateY(10px) rotate(240deg);
  }
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 500px;
}

.upload-icon-container {
  position: relative;
  margin-bottom: 0.5rem;
}

.icon-wrapper {
  position: relative;
  display: inline-block;
}

.upload-icon {
  font-size: 5rem;
  color: var(--brand-500);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 1;
}

.upload-icon.bounce {
  animation: bounce 0.6s ease-in-out;
}

.icon-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 120px;
  height: 120px;
  background: radial-gradient(
    circle,
    rgba(102, 126, 234, 0.2) 0%,
    transparent 70%
  );
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.4s ease;
}

.upload-dropzone:hover .upload-icon {
  transform: scale(1.15);
  color: var(--brand-400);
}

.upload-dropzone:hover .icon-glow {
  opacity: 1;
}

.upload-dropzone.dragover .upload-icon {
  color: var(--success-500);
  transform: scale(1.2);
}

@keyframes bounce {
  0%,
  20%,
  50%,
  80%,
  100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-20px);
  }
  60% {
    transform: translateY(-10px);
  }
}

.upload-text-container {
  text-align: center;
  margin-bottom: 0.5rem;
}

.upload-text {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--gray-700);
  margin: 0 0 0.75rem 0;
  line-height: 1.3;
  transition: all 0.3s ease;
}

.upload-text.highlight {
  color: var(--success-500);
  transform: scale(1.08);
  text-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.upload-subtext {
  font-size: 1rem;
  color: var(--gray-500);
  margin: 0 0 1rem 0;
  line-height: 1.5;
  font-weight: 500;
  transition: all 0.3s ease;
}

.drag-hint {
  margin-top: 1rem;
  animation: pulseGlow 1.5s ease-in-out infinite;
}

.drag-hint-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(
    135deg,
    rgba(16, 185, 129, 0.1) 0%,
    rgba(16, 185, 129, 0.2) 100%
  );
  padding: 1rem 2rem;
  border-radius: 20px;
  border: 2px dashed var(--success-400);
  color: var(--success-700);
  font-weight: 600;
  backdrop-filter: blur(10px);
}

.drag-arrow {
  font-size: 2rem;
  animation: bounce 1s ease-in-out infinite;
  color: var(--success-500);
}

@keyframes pulseGlow {
  0%,
  100% {
    opacity: 0.8;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.05);
  }
}

@keyframes bounce {
  0%,
  20%,
  50%,
  80%,
  100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-10px);
  }
  60% {
    transform: translateY(-5px);
  }
}

/* Upload Actions Container */
.upload-actions-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
  width: 100%;
}

.divider {
  display: flex;
  align-items: center;
  width: 100%;
  margin: 0.5rem 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, var(--gray-200), transparent);
}

.divider span {
  padding: 0 1rem;
  color: var(--gray-400);
  font-size: 0.9rem;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 20px;
}

.quick-actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  justify-content: center;
}

.quick-action-btn {
  padding: 0.75rem 1.5rem;
  font-size: 0.9rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--gray-300);
  color: var(--gray-700);
  font-weight: 500;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.quick-action-btn:hover {
  background: white;
  border-color: var(--primary-600);
  color: var(--primary-700);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.upload-button-primary {
  padding: 0.75rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand-500) 0%, var(--brand-700) 100%);
  border: none;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.upload-button-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.upload-note {
  margin: 20px -24px 0 -24px;
  padding: 16px 20px;
  background: linear-gradient(135deg, var(--warning-50) 0%, var(--warning-100) 100%);
  border-radius: var(--radius-lg);
  border: 1px solid var(--warning-200);
  border-left: 4px solid var(--warning-500);
}

.note-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: rgba(255, 255, 255, 0.9);
  padding: 1rem 1.25rem;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(229, 231, 235, 0.6);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.note-content i {
  font-size: 1.1rem;
  color: var(--brand-500);
  flex-shrink: 0;
}

.note-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
  line-height: 1.4;
}

.supported-formats {
  color: var(--gray-700);
  font-weight: 500;
}

.file-limit {
  color: var(--gray-700);
  font-size: 0.85rem;
  font-weight: 500;
}

/* Drag Overlay */
.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(
    circle at center,
    rgba(16, 185, 129, 0.15) 0%,
    rgba(16, 185, 129, 0.05) 100%
  );
  backdrop-filter: blur(10px);
  border-radius: var(--radius-2xl);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  animation: overlaySlideIn 0.3s ease-out;
  border: 3px solid var(--success-400);
}

@keyframes overlaySlideIn {
  from {
    opacity: 0;
    transform: scale(0.95);
    backdrop-filter: blur(0px);
  }
  to {
    opacity: 1;
    transform: scale(1);
    backdrop-filter: blur(10px);
  }
}

.drag-overlay-content {
  text-align: center;
  color: var(--success-700);
  font-weight: 700;
  padding: var(--space-8);
  background: rgba(255, 255, 255, 0.9);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  border: 2px solid var(--success-200);
  backdrop-filter: blur(5px);
}

.drag-icon {
  font-size: 5rem;
  margin-bottom: var(--space-4);
  animation: dragBounce 0.8s ease-in-out infinite;
  filter: drop-shadow(0 4px 8px rgba(16, 185, 129, 0.3));
}

@keyframes dragBounce {
  0%,
  20%,
  50%,
  80%,
  100% {
    transform: translateY(0) scale(1);
  }
  40% {
    transform: translateY(-15px) scale(1.1);
  }
  60% {
    transform: translateY(-8px) scale(1.05);
  }
}

.drag-overlay p {
  font-size: 1.5rem;
  margin: 0 0 1rem 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  letter-spacing: 0.025em;
}

.drop-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.9);
  padding: 1rem 2rem;
  border-radius: 15px;
  border: 2px dashed var(--success-400);
  color: var(--success-700);
  font-weight: 600;
  animation: pulseGlow 1.5s ease-in-out infinite;
}

.drop-arrow {
  font-size: 1.5rem;
  animation: bounce 1s ease-in-out infinite;
  color: var(--success-500);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Selected Files Section */
.selected-files-section {
  margin-top: 1.5rem;
  padding: 0 1rem;
}

.selected-files-header {
  margin-bottom: 1rem;
}

.selected-files-header h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  color: var(--success-600);
  font-size: 1.1rem;
  font-weight: 600;
}

.selected-files-list {
  display: grid;
  gap: 0.75rem;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--gray-200);
  transition: all 0.2s ease;
}

.file-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--brand-500) 0%, var(--brand-700) 100%);
  border-radius: 10px;
  color: white;
  font-size: 1.5rem;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.file-name {
  font-weight: 600;
  color: var(--gray-700);
  font-size: 1rem;
  line-height: 1.2;
}

.file-size {
  font-size: 0.9rem;
  color: var(--gray-500);
}

.file-remove-btn {
  flex-shrink: 0;
  border-radius: 8px;
  min-width: 44px;
  height: 44px;
  background: rgba(239, 68, 68, 0.1) !important;
  border: 2px solid var(--error-300) !important;
  color: var(--error-600) !important;
  transition: all 0.3s ease;
}

.file-remove-btn:hover:not(:disabled) {
  background: var(--error-500) !important;
  border-color: var(--error-500) !important;
  color: white !important;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.file-remove-btn:active {
  transform: translateY(0);
}

.file-remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Upload Progress Section */
.upload-progress-section {
  margin-top: 1.5rem;
  padding: 0 1rem;
}

.progress-header h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  color: var(--info-500);
  font-size: 1.1rem;
  font-weight: 600;
}

.progress-list {
  display: grid;
  gap: 1rem;
}

.progress-item {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--gray-200);
}

.progress-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.progress-file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-name {
  font-weight: 600;
  color: var(--gray-700);
  font-size: 1rem;
}

.progress-percent {
  font-weight: 700;
  color: var(--info-500);
  font-size: 1.1rem;
}

.progress-bar {
  border-radius: 6px;
  height: 8px;
}

.progress-status {
  display: flex;
  justify-content: flex-end;
}

/* Upload Actions */
.upload-actions {
  margin-top: 2rem;
  text-align: center;
  padding: 0 1rem 1rem;
}

.upload-start-button {
  padding: 1rem 2.5rem;
  font-size: 1.1rem;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--success-600) 0%, var(--success-700) 100%);
  border: none;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(5, 150, 105, 0.3);
  min-width: 200px;
}

.upload-start-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(5, 150, 105, 0.4);
}

/* Responsive Design */
@media (max-width: 768px) {
  .upload-header {
    padding: 2rem 1rem 1rem;
    margin: -1.5rem -1.5rem 1rem -1.5rem;
  }

  .upload-area {
    padding: 0.75rem;
  }

  .upload-title {
    font-size: 1.5rem;
  }

  .upload-description {
    font-size: 0.9rem;
  }

  .upload-dropzone {
    padding: 1.5rem 1rem;
    min-height: 300px;
  }

  .upload-icon {
    font-size: 3rem;
  }

  .upload-text {
    font-size: 1.1rem;
  }

  .upload-subtext {
    font-size: 0.9rem;
  }

  .dropzone-content {
    gap: 1.5rem;
  }

  .quick-actions {
    flex-direction: column;
    gap: 0.75rem;
    width: 100%;
  }

  .quick-action-btn {
    width: 100%;
    justify-content: center;
  }

  .upload-button-primary {
    padding: 0.75rem 1.5rem;
    font-size: 0.9rem;
  }

  .file-item {
    padding: 0.75rem 1rem;
  }

  .file-info {
    flex: 1;
  }

  .file-remove-btn {
    min-width: 36px;
    height: 36px;
  }

  .file-icon {
    width: 40px;
    height: 40px;
    font-size: 1.25rem;
  }

  .progress-file-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .upload-start-button {
    width: 100%;
    padding: 1rem;
    font-size: 1rem;
  }

  .selected-files-section,
  .upload-progress-section,
  .upload-actions {
    padding-left: 0.5rem;
    padding-right: 0.5rem;
  }
}

@media (max-width: 480px) {
  .upload-header {
    padding: 1.5rem 0.75rem 0.75rem;
  }

  .title-section {
    flex-direction: column;
    gap: 0.5rem;
  }

  .upload-title {
    font-size: 1.25rem;
  }

  .upload-dropzone {
    padding: 1.5rem 0.75rem;
    min-height: 300px;
  }

  .dropzone-content {
    gap: 1rem;
  }

  .upload-icon {
    font-size: 2.5rem;
  }

  .upload-text {
    font-size: 1rem;
  }

  .upload-subtext {
    font-size: 0.85rem;
  }

  .upload-button-primary {
    padding: 0.75rem 1.25rem;
    font-size: 0.9rem;
    width: 100%;
  }

  .note-content {
    padding: 0.75rem 1rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .note-text {
    font-size: 0.8rem;
  }

  .drag-overlay p {
    font-size: 1rem;
  }

  .drag-icon {
    font-size: 3rem;
  }
}

/* FileUploaderカードの統一余白設定 */
.file-uploader :deep(.p-card) {
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--gray-200);
  background: white;
  transition: all var(--transition-normal);
}

.file-uploader :deep(.p-card-body) {
  padding: 0;
}

.file-uploader :deep(.p-card-title) {
  padding: 20px 24px 0 24px;
  margin: 0 0 16px 0;
  color: var(--gray-900);
  font-weight: 600;
  font-size: 1.2rem;
}

.file-uploader :deep(.p-card-content) {
  padding: 0 24px 24px 24px;
  color: var(--gray-700);
}

/* ドロップゾーンの調整 */
.upload-dropzone {
  padding: 32px 20px;
  margin: 0 -20px;
  border: 2px dashed var(--gray-300);
  border-radius: var(--radius-lg);
  background: var(--gray-50);
  transition: all var(--transition-normal);
  text-align: center;
  min-height: 350px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ファイルリストの調整 */
.file-list {
  margin: 20px -24px 0 -24px;
  padding: 20px 24px;
  background: var(--gray-50);
  border-radius: var(--radius-lg);
  border: 1px solid var(--gray-200);
}

/* 注意事項の調整 */
.upload-note {
  margin: 20px -24px 0 -24px;
  padding: 16px 20px;
  background: linear-gradient(135deg, var(--warning-50) 0%, var(--warning-100) 100%);
  border-radius: var(--radius-lg);
  border: 1px solid var(--warning-200);
  border-left: 4px solid var(--warning-500);
}
</style>
