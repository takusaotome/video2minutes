<template>
  <div class="dashboard">
    <!-- Welcome Section -->
    <div class="welcome-section">
      <div class="welcome-content">
        <h2>動画から議事録を自動生成</h2>
        <p>
          動画ファイルをアップロードするだけで、AIが自動的に文字起こしと議事録を生成します。<br>
          会議録の作成時間を大幅に短縮できます。
        </p>
      </div>
      <div class="features">
        <div class="feature-item">
          <i class="pi pi-cloud-upload feature-icon"></i>
          <span>簡単アップロード</span>
        </div>
        <div class="feature-item">
          <i class="pi pi-cog feature-icon"></i>
          <span>自動処理</span>
        </div>
        <div class="feature-item">
          <i class="pi pi-file-text feature-icon"></i>
          <span>議事録生成</span>
        </div>
      </div>
    </div>

    <!-- File Upload Section -->
    <FileUploader
      @upload-started="onUploadStarted"
      @upload-completed="onUploadCompleted"
      @upload-error="onUploadError"
    />

    <!-- Task List Section -->
    <TaskList />

    <!-- Quick Stats -->
    <div v-if="taskStats.total > 0" class="quick-stats">
      <Card>
        <template #title>
          <div class="stats-title">
            <i class="pi pi-chart-bar"></i>
            処理統計
          </div>
        </template>
        
        <template #content>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-number">{{ taskStats.total }}</div>
              <div class="stat-label">総タスク数</div>
            </div>
            <div class="stat-card processing">
              <div class="stat-number">{{ taskStats.processing }}</div>
              <div class="stat-label">処理中</div>
            </div>
            <div class="stat-card completed">
              <div class="stat-number">{{ taskStats.completed }}</div>
              <div class="stat-label">完了</div>
            </div>
            <div class="stat-card failed">
              <div class="stat-number">{{ taskStats.failed }}</div>
              <div class="stat-label">エラー</div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Help Section -->
    <div class="help-section">
      <Card>
        <template #title>
          <div class="help-title">
            <i class="pi pi-question-circle"></i>
            使い方
          </div>
        </template>
        
        <template #content>
          <div class="help-content">
            <div class="help-steps">
              <div class="help-step">
                <div class="step-number">1</div>
                <div class="step-content">
                  <h4>動画ファイルをアップロード</h4>
                  <p>MP4、AVI、MOV、WMVなどの動画ファイルをドラッグ&ドロップするか、「ファイルを選択」ボタンでアップロードしてください。</p>
                </div>
              </div>
              
              <div class="help-step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <h4>自動処理を待つ</h4>
                  <p>アップロード後、システムが自動的に音声抽出→文字起こし→議事録生成を順次実行します。進捗はリアルタイムで表示されます。</p>
                </div>
              </div>
              
              <div class="help-step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <h4>議事録をダウンロード</h4>
                  <p>処理完了後、議事録を表示・コピー・ダウンロードできます。Markdown、テキスト、PDF形式で保存可能です。</p>
                </div>
              </div>
            </div>
            
            <div class="help-notes">
              <h4>
                <i class="pi pi-info-circle"></i>
                ご注意
              </h4>
              <ul>
                <li>対応ファイルサイズ: 最大500MB</li>
                <li>処理時間: 10分程度の動画で約3-5分</li>
                <li>日本語音声での利用を推奨</li>
                <li>音質が良いほど文字起こし精度が向上します</li>
              </ul>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script>
import { computed, onMounted, onUnmounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useTasksStore } from '@/stores/tasks'
import FileUploader from '@/components/FileUploader.vue'
import TaskList from '@/components/TaskList.vue'
import Card from 'primevue/card'

export default {
  name: 'DashboardView',
  components: {
    FileUploader,
    TaskList,
    Card
  },
  setup() {
    const toast = useToast()
    const tasksStore = useTasksStore()

    const taskStats = computed(() => tasksStore.taskStats)

    const onUploadStarted = ({ file }) => {
      console.log('Upload started:', file.name)
    }

    const onUploadCompleted = ({ file, task }) => {
      console.log('Upload completed:', file.name, task)
      
      // Show completion notification with link to view progress
      toast.add({
        severity: 'success',
        summary: 'アップロード完了',
        detail: `${file.name} のアップロードが完了しました。処理を開始します。`,
        life: 5000
      })
    }

    const onUploadError = ({ file, error }) => {
      console.error('Upload error:', file.name, error)
      
      toast.add({
        severity: 'error',
        summary: 'アップロードエラー',
        detail: `${file.name}: ${error.message}`,
        life: 7000
      })
    }

    // Auto-refresh tasks periodically
    const refreshTasks = () => {
      if (document.visibilityState === 'visible') {
        tasksStore.fetchTasks()
      }
    }

    onMounted(() => {
      // Initial load
      tasksStore.fetchTasks()
      
      // Set up auto-refresh
      document.addEventListener('visibilitychange', refreshTasks)
    })

    onUnmounted(() => {
      document.removeEventListener('visibilitychange', refreshTasks)
      tasksStore.stopPolling()
      tasksStore.disconnectAllWebSockets()
    })

    return {
      taskStats,
      onUploadStarted,
      onUploadCompleted,
      onUploadError
    }
  }
}
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.welcome-section {
  text-align: center;
  padding: 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 16px;
  margin-bottom: 1rem;
}

.welcome-content h2 {
  font-size: 2.5rem;
  margin: 0 0 1rem 0;
  font-weight: 700;
}

.welcome-content p {
  font-size: 1.1rem;
  line-height: 1.6;
  margin: 0 0 2rem 0;
  opacity: 0.95;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.features {
  display: flex;
  justify-content: center;
  gap: 3rem;
  flex-wrap: wrap;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  min-width: 120px;
}

.feature-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.quick-stats {
  margin-top: 1rem;
}

.stats-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  color: #495057;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.stat-card {
  text-align: center;
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 12px;
  border: 2px solid #e9ecef;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-card.processing {
  border-color: #ffc107;
  background: #fff9e6;
}

.stat-card.completed {
  border-color: #28a745;
  background: #e8f5e8;
}

.stat-card.failed {
  border-color: #dc3545;
  background: #ffeaea;
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 700;
  color: #495057;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.9rem;
  color: #6c757d;
  font-weight: 500;
}

.help-section {
  margin-top: 2rem;
}

.help-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  color: #495057;
}

.help-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.help-steps {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.help-step {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #6366f1;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-content h4 {
  margin: 0 0 0.5rem 0;
  color: #495057;
  font-size: 1.1rem;
}

.step-content p {
  margin: 0;
  line-height: 1.6;
  color: #6c757d;
}

.help-notes {
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #6366f1;
}

.help-notes h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  color: #495057;
  font-size: 1rem;
}

.help-notes ul {
  margin: 0;
  padding-left: 1.5rem;
}

.help-notes li {
  margin: 0.5rem 0;
  line-height: 1.5;
  color: #6c757d;
}

/* Responsive Design */
@media (max-width: 768px) {
  .welcome-content h2 {
    font-size: 2rem;
  }
  
  .welcome-content p {
    font-size: 1rem;
  }
  
  .features {
    gap: 1.5rem;
  }
  
  .feature-item {
    min-width: 100px;
    padding: 0.75rem;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .help-step {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .step-number {
    align-self: flex-start;
  }
}

@media (max-width: 480px) {
  .dashboard {
    gap: 1.5rem;
  }
  
  .welcome-section {
    padding: 1.5rem;
    margin-bottom: 0.5rem;
  }
  
  .welcome-content h2 {
    font-size: 1.75rem;
  }
  
  .features {
    flex-direction: column;
    gap: 1rem;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .stat-card {
    padding: 1rem;
  }
  
  .stat-number {
    font-size: 2rem;
  }
}
</style>