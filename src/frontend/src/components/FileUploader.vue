<template>
  <div class="file-uploader">
    <Card class="upload-card">
      <template #content>
        <div class="upload-container">
          <!-- Title Section -->
          <div class="upload-header">
            <div class="title-section">
              <i class="pi pi-cloud-upload title-icon"></i>
              <h2 class="upload-title">動画ファイルをアップロード</h2>
            </div>
            <p class="upload-description">
              動画から自動的に議事録を生成します
            </p>
          </div>

          <!-- Upload Area -->
          <div 
            class="upload-area"
            @dragenter="onDragEnter"
            @dragover="onDragOver" 
            @dragleave="onDragLeave"
            @drop="onDrop"
          >
            <FileUpload
              ref="fileUpload"
              mode="basic"
              :multiple="true"
              accept="video/*"
              :maxFileSize="5368709120"
              :customUpload="true"
              @uploader="onUpload"
              @select="onSelect"
              @clear="onClear"
              :disabled="loading"
              chooseLabel="ファイルを選択"
              class="custom-file-upload"
              :drag-highlight="false"
            >
              <template #empty>
                <div 
                  class="upload-dropzone"
                  :class="{ 'dragover': isDragOver }"
                >
                  <!-- Animated Background Elements -->
                  <div class="dropzone-bg-elements">
                    <div class="floating-element element-1"></div>
                    <div class="floating-element element-2"></div>
                    <div class="floating-element element-3"></div>
                  </div>
                  
                  <div class="dropzone-content">
                    <div class="upload-icon-container">
                      <div class="icon-wrapper">
                        <i class="pi pi-cloud-upload upload-icon" :class="{ 'bounce': isDragOver }"></i>
                        <div class="icon-glow"></div>
                      </div>
                    </div>
                    
                    <div class="upload-text-container">
                      <h3 class="upload-text" :class="{ 'highlight': isDragOver }">
                        {{ isDragOver ? 'ファイルをドロップしてください' : 'ファイルをドラッグ&ドロップ' }}
                      </h3>
                      <p class="upload-subtext">
                        または下のボタンからファイルを選択してください
                      </p>
                      <p v-if="isDragging" class="drag-status">
                        ドラッグ中...
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
                            対応形式: MP4, AVI, MOV, MKV, WMV, FLV, WebM
                          </div>
                          <div class="file-limit">
                            最大ファイルサイズ: 5GB
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Upload Progress Overlay -->
                  <div v-if="isDragOver" class="drag-overlay">
                    <div class="drag-overlay-content">
                      <i class="pi pi-download drag-icon"></i>
                      <p>ファイルをドロップ</p>
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
              <div v-for="file in selectedFiles" :key="file.name" class="file-item">
                <div class="file-info">
                  <div class="file-icon">
                    <i class="pi pi-file-video"></i>
                  </div>
                  <div class="file-details">
                    <span class="file-name">{{ file.name }}</span>
                    <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  </div>
                </div>
                <Button
                  icon="pi pi-times"
                  class="p-button-text p-button-danger p-button-sm file-remove-btn"
                  @click="removeFile(file)"
                  :disabled="loading"
                  v-tooltip="'削除'"
                />
              </div>
            </div>
          </div>

          <!-- Upload Progress -->
          <div v-if="uploadProgress.length > 0" class="upload-progress-section">
            <div class="progress-header">
              <h4><i class="pi pi-spin pi-spinner"></i> アップロード進行状況</h4>
            </div>
            <div class="progress-list">
              <div v-for="progress in uploadProgress" :key="progress.name" class="progress-item">
                <div class="progress-info">
                  <div class="progress-file-info">
                    <span class="progress-name">{{ progress.name }}</span>
                    <span class="progress-percent">{{ progress.percent }}%</span>
                  </div>
                  <ProgressBar :value="progress.percent" class="progress-bar" />
                  <div v-if="progress.status" class="progress-status">
                    <Badge :value="getStatusLabel(progress.status)" :severity="getStatusSeverity(progress.status)" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Upload Button -->
          <div v-if="selectedFiles.length > 0 && uploadProgress.length === 0" class="upload-actions">
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
import { ref, computed } from 'vue'
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

    const onSelect = (event) => {
      console.log('Files selected:', event.files)
      selectedFiles.value = [...event.files]
      uploadProgress.value = []
    }

    const onClear = () => {
      selectedFiles.value = []
      uploadProgress.value = []
    }

    const removeFile = (fileToRemove) => {
      selectedFiles.value = selectedFiles.value.filter(file => file !== fileToRemove)
      if (selectedFiles.value.length === 0) {
        uploadProgress.value = []
      }
    }

    const onUpload = async (event) => {
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

            const task = await tasksStore.uploadFile(file, (percent) => {
              progressItem.percent = percent
            })

            progressItem.status = 'completed'
            progressItem.percent = 100

            toast.add({
              severity: 'success',
              summary: 'アップロード完了',
              detail: `${file.name} のアップロードが完了しました`,
              life: 5000
            })

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

    const triggerFileSelect = () => {
      try {
        if (fileUpload.value && fileUpload.value.$refs && fileUpload.value.$refs.fileInput) {
          fileUpload.value.$refs.fileInput.click()
        } else {
          // Fallback: try to find the file input element
          const fileInput = document.querySelector('.custom-file-upload input[type="file"]')
          if (fileInput) {
            fileInput.click()
          }
        }
      } catch (error) {
        console.warn('Could not trigger file select:', error)
      }
    }

    // Drag & Drop handlers
    const onDragEnter = (e) => {
      e.preventDefault()
      e.stopPropagation()
      
      // Check if files are being dragged
      if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
        dragCounter.value++
        if (dragCounter.value === 1) {
          isDragOver.value = true
          isDragging.value = true
          console.log('Drag enter detected')
        }
      }
    }

    const onDragOver = (e) => {
      e.preventDefault()
      e.stopPropagation()
      
      if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
        e.dataTransfer.dropEffect = 'copy'
        isDragOver.value = true
      }
    }

    const onDragLeave = (e) => {
      e.preventDefault()
      e.stopPropagation()
      
      // Only reduce counter if leaving the main drop area
      if (!e.currentTarget.contains(e.relatedTarget)) {
        dragCounter.value--
        if (dragCounter.value === 0) {
          isDragOver.value = false
          isDragging.value = false
          console.log('Drag leave detected')
        }
      }
    }

    const onDrop = (e) => {
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
          
          // Check by file extension if MIME type is not reliable
          const supportedExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
          return supportedExtensions.some(ext => fileName.endsWith(ext))
        })

        if (validFiles.length === 0) {
          toast.add({
            severity: 'warn',
            summary: '無効なファイル形式',
            detail: '動画ファイルのみアップロード可能です',
            life: 3000
          })
          return
        }

        if (validFiles.length !== files.length) {
          toast.add({
            severity: 'warn',
            summary: '一部ファイルをスキップ',
            detail: `${files.length - validFiles.length}個のファイルは動画ファイルではないためスキップされました`,
            life: 4000
          })
        }

        // Add files to selected files and trigger PrimeVue's onSelect
        selectedFiles.value = [...selectedFiles.value, ...validFiles]
        uploadProgress.value = []
        
        // Trigger the onSelect event manually to sync with PrimeVue
        if (validFiles.length > 0) {
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

    const openFileDialog = (accept) => {
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
  margin-bottom: 2rem;
}

.upload-card {
  border: none;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  overflow: hidden;
}

.upload-container {
  padding: 0;
}

/* Header Section */
.upload-header {
  text-align: center;
  padding: 2.5rem 2rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  margin: -1.5rem -1.5rem 1.5rem -1.5rem;
}

.title-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.title-icon {
  font-size: 2rem;
  opacity: 0.9;
}

.upload-title {
  font-size: 1.75rem;
  font-weight: 600;
  margin: 0;
  line-height: 1.2;
}

.upload-description {
  font-size: 1rem;
  opacity: 0.9;
  margin: 0;
  font-weight: 400;
}

/* Upload Area */
.upload-area {
  padding: 0 1rem;
  position: relative;
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
  pointer-events: none;
}

:deep(.custom-file-upload .p-fileupload-content .p-fileupload-empty) {
  pointer-events: auto;
}

.upload-dropzone {
  border: 3px dashed #e5e7eb;
  border-radius: 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 4rem 2rem;
  text-align: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-dropzone:hover {
  border-color: #667eea;
  background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
  transform: translateY(-4px);
  box-shadow: 0 20px 40px -12px rgba(102, 126, 234, 0.25);
}

.upload-dropzone.dragover {
  border-color: #10b981;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 25px 50px -12px rgba(16, 185, 129, 0.35);
  border-style: solid;
}

.upload-dropzone::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
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
  background: linear-gradient(45deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
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
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  33% { transform: translateY(-20px) rotate(120deg); }
  66% { transform: translateY(10px) rotate(240deg); }
}

.dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 500px;
}

.upload-icon-container {
  position: relative;
  margin-bottom: 1rem;
}

.icon-wrapper {
  position: relative;
  display: inline-block;
}

.upload-icon {
  font-size: 5rem;
  color: #667eea;
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
  background: radial-gradient(circle, rgba(102, 126, 234, 0.2) 0%, transparent 70%);
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.4s ease;
}

.upload-dropzone:hover .upload-icon {
  transform: scale(1.15);
  color: #5b6de8;
}

.upload-dropzone:hover .icon-glow {
  opacity: 1;
}

.upload-dropzone.dragover .upload-icon {
  color: #10b981;
  transform: scale(1.2);
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-20px); }
  60% { transform: translateY(-10px); }
}

.upload-text-container {
  text-align: center;
  margin-bottom: 1rem;
}

.upload-text {
  font-size: 1.5rem;
  font-weight: 700;
  color: #374151;
  margin: 0 0 0.75rem 0;
  line-height: 1.3;
  transition: all 0.3s ease;
}

.upload-text.highlight {
  color: #10b981;
  transform: scale(1.05);
}

.upload-subtext {
  font-size: 1.1rem;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
  font-weight: 400;
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
  background: linear-gradient(to right, transparent, #e5e7eb, transparent);
}

.divider span {
  padding: 0 1rem;
  color: #9ca3af;
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
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #e5e7eb;
  color: #6b7280;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.quick-action-btn:hover {
  background: white;
  border-color: #667eea;
  color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.upload-button-primary {
  padding: 0.75rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.upload-button-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.upload-note {
  width: 100%;
  margin-top: 0.5rem;
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
  color: #667eea;
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
  color: #374151;
  font-weight: 500;
}

.file-limit {
  color: #6b7280;
  font-size: 0.85rem;
}

/* Drag Overlay */
.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(16, 185, 129, 0.1);
  backdrop-filter: blur(8px);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  animation: fadeIn 0.2s ease-out;
}

.drag-overlay-content {
  text-align: center;
  color: #10b981;
  font-weight: 600;
}

.drag-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  animation: bounce 0.6s ease-in-out infinite;
}

.drag-overlay p {
  font-size: 1.25rem;
  margin: 0;
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
  color: #059669;
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
  border: 1px solid #e5e7eb;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  color: #374151;
  font-size: 1rem;
  line-height: 1.2;
}

.file-size {
  font-size: 0.9rem;
  color: #6b7280;
}

.file-remove-btn {
  flex-shrink: 0;
  border-radius: 8px;
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
  color: #3b82f6;
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
  border: 1px solid #e5e7eb;
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
  color: #374151;
  font-size: 1rem;
}

.progress-percent {
  font-weight: 700;
  color: #3b82f6;
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
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
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
  
  .upload-title {
    font-size: 1.5rem;
  }
  
  .upload-description {
    font-size: 0.9rem;
  }
  
  .upload-dropzone {
    padding: 2rem 1rem;
    min-height: 350px;
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
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
  
  .file-info {
    width: 100%;
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
</style>