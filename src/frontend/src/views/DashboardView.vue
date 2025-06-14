<template>
  <div class="dashboard">
    <!-- Welcome Section -->
    <div class="welcome-section">
      <div class="welcome-content">
        <h2>動画から議事録を自動生成</h2>
        <p>
          動画ファイルをアップロードするだけで、AIが自動的に文字起こしと議事録を生成します。<br />
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
          <i class="pi pi-file feature-icon"></i>
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
                  <p>
                    MP4、AVI、MOV、WMVなどの動画ファイルをドラッグ&ドロップするか、「ファイルを選択」ボタンでアップロードしてください。
                  </p>
                </div>
              </div>

              <div class="help-step">
                <div class="step-number">2</div>
                <div class="step-content">
                  <h4>自動処理を待つ</h4>
                  <p>
                    アップロード後、システムが自動的に音声抽出→文字起こし→議事録生成を順次実行します。進捗はリアルタイムで表示されます。
                  </p>
                </div>
              </div>

              <div class="help-step">
                <div class="step-number">3</div>
                <div class="step-content">
                  <h4>議事録をダウンロード</h4>
                  <p>
                    処理完了後、議事録を表示・コピー・ダウンロードできます。Markdown、テキスト、PDF形式で保存可能です。
                  </p>
                </div>
              </div>
            </div>

            <div class="help-notes">
              <h4>
                <i class="pi pi-info-circle"></i>
                ご注意
              </h4>
              <ul>
                <li>対応ファイルサイズ: 最大5GB</li>
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

    // Auto-refresh tasks periodically (silent refresh)
    const refreshTasks = () => {
      if (document.visibilityState === 'visible') {
        tasksStore.silentRefresh()
      }
    }

    onMounted(async () => {
      // 初期化されていない場合のみ初回読み込みを実行
      if (!tasksStore.initialized) {
        await tasksStore.fetchTasks(false) // 初回はローディング表示せずに即座に実行
      }

      // Start polling for real-time updates
      tasksStore.startPolling(5000) // 5秒間隔でポーリング

      // Set up auto-refresh on page visibility change
      document.addEventListener('visibilitychange', refreshTasks)

      console.log('DashboardView mounted, polling started')
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
  gap: var(--space-6);
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 var(--space-4);
  animation: fadeIn 0.6s ease-out;
}

.welcome-section {
  text-align: center;
  padding: var(--space-8) var(--space-6);
  background: linear-gradient(
    135deg,
    var(--primary-700) 0%,
    var(--secondary-700) 100%
  );
  color: white;
  border-radius: var(--radius-2xl);
  margin-bottom: var(--space-4);
  box-shadow: var(--shadow-xl);
  position: relative;
  overflow: hidden;
}

.welcome-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(
    circle at 30% 20%,
    rgba(255, 255, 255, 0.1) 0%,
    transparent 50%
  );
  pointer-events: none;
}

/* Dark overlay for better contrast */
.welcome-section::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.05);
  pointer-events: none;
}

.welcome-content h2 {
  font-size: 2.75rem;
  margin: 0 0 var(--space-5) 0;
  font-weight: 800;
  color: white;
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  position: relative;
  z-index: 1;
}

.welcome-content p {
  font-size: 1.2rem;
  line-height: 1.7;
  margin: 0 0 var(--space-8) 0;
  color: white;
  opacity: 1;
  max-width: 650px;
  margin-left: auto;
  margin-right: auto;
  position: relative;
  z-index: 1;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  font-weight: 500;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-6);
  max-width: 600px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5);
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all var(--transition-normal);
}

.feature-item:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: var(--space-2);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.quick-stats {
  margin-top: var(--space-4);
  animation: slideUp 0.8s ease-out 0.2s both;
}

.stats-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: 1.375rem;
  color: var(--gray-800);
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 20px;
  margin: 0;
}

.stat-card {
  text-align: center;
  padding: 24px 16px;
  background: white;
  border-radius: var(--radius-xl);
  border: 2px solid var(--gray-200);
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gray-200);
  transition: all var(--transition-normal);
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-xl);
  border-color: var(--primary-300);
}

.stat-card:hover::before {
  background: var(--primary-500);
}

.stat-card.processing {
  border-color: var(--warning-300);
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
}

.stat-card.processing::before {
  background: var(--warning-500);
}

.stat-card.processing:hover {
  border-color: var(--warning-400);
  box-shadow: 0 8px 25px rgba(245, 158, 11, 0.15);
}

.stat-card.completed {
  border-color: var(--success-300);
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
}

.stat-card.completed::before {
  background: var(--success-500);
}

.stat-card.completed:hover {
  border-color: var(--success-400);
  box-shadow: 0 8px 25px rgba(16, 185, 129, 0.15);
}

.stat-card.failed {
  border-color: var(--error-300);
  background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%);
}

.stat-card.failed::before {
  background: var(--error-500);
}

.stat-card.failed:hover {
  border-color: var(--error-400);
  box-shadow: 0 8px 25px rgba(239, 68, 68, 0.15);
}

.stat-number {
  font-size: 3rem;
  font-weight: 800;
  color: var(--gray-800);
  margin-bottom: var(--space-2);
  line-height: 1;
}

.stat-label {
  font-size: 1rem;
  color: var(--gray-800);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.help-section {
  margin-top: var(--space-6);
  animation: slideUp 0.8s ease-out 0.4s both;
}

.help-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: 1.375rem;
  color: var(--gray-800);
  font-weight: 600;
}

.help-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

.help-steps {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin: 0;
}

.help-step {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  padding: 20px;
  border-radius: var(--radius-lg);
  background: var(--gray-50);
  border: 1px solid var(--gray-100);
  transition: all var(--transition-normal);
}

.help-step:hover {
  background: white;
  border-color: var(--primary-200);
  box-shadow: var(--shadow-sm);
}

.step-number {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(
    135deg,
    var(--primary-500) 0%,
    var(--primary-600) 100%
  );
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.25rem;
  flex-shrink: 0;
  box-shadow: var(--shadow-md);
}

.step-content {
  flex: 1;
}

.step-content h4 {
  margin: 0 0 var(--space-3) 0;
  color: var(--gray-800);
  font-size: 1.25rem;
  font-weight: 600;
}

.step-content p {
  margin: 0;
  line-height: 1.7;
  color: var(--gray-600);
  font-size: 1rem;
}

.help-notes {
  padding: 20px;
  background: linear-gradient(
    135deg,
    var(--primary-50) 0%,
    var(--primary-100) 100%
  );
  border-radius: var(--radius-lg);
  border-left: 4px solid var(--primary-500);
  border: 1px solid var(--primary-200);
  margin-top: 20px;
}

.help-notes h4 {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: 0 0 var(--space-4) 0;
  color: var(--primary-800);
  font-size: 1.125rem;
  font-weight: 600;
}

.help-notes ul {
  margin: 0;
  padding-left: var(--space-6);
}

.help-notes li {
  margin: var(--space-2) 0;
  line-height: 1.6;
  color: var(--primary-800);
  font-weight: 500;
}

/* Responsive Design */
@media (max-width: 768px) {
  .dashboard {
    padding: 0 var(--space-3);
    gap: var(--space-4);
  }

  .welcome-section {
    padding: var(--space-6) var(--space-4);
    margin-bottom: var(--space-3);
  }

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
    gap: var(--space-3);
    padding: 0 var(--space-2);
  }

  .welcome-section {
    padding: var(--space-4);
    margin-bottom: var(--space-2);
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

/* 統一的なカード余白設定 */
.dashboard :deep(.p-card) {
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--gray-200);
  background: white;
  transition: all var(--transition-normal);
}

.dashboard :deep(.p-card-title) {
  padding: 20px 24px 0 24px;
  margin: 0 0 16px 0;
  color: var(--gray-900);
  font-weight: 600;
  font-size: 1.2rem;
}

.dashboard :deep(.p-card-content) {
  padding: 0 24px 24px 24px;
  color: var(--gray-700);
}

/* 処理統計カードの調整 */
.quick-stats :deep(.p-card-content) {
  padding: 0 24px 24px 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 20px;
  margin: 0;
}

.stat-card {
  text-align: center;
  padding: 24px 16px;
  background: white;
  border-radius: var(--radius-xl);
  border: 2px solid var(--gray-200);
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

/* 使い方セクションの調整 */
.help-section :deep(.p-card-content) {
  padding: 0 24px 24px 24px;
}

.help-steps {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin: 0;
}

.help-step {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  padding: 20px;
  border-radius: var(--radius-lg);
  background: var(--gray-50);
  border: 1px solid var(--gray-100);
  transition: all var(--transition-normal);
}

.help-notes {
  padding: 20px;
  background: linear-gradient(
    135deg,
    var(--primary-50) 0%,
    var(--primary-100) 100%
  );
  border-radius: var(--radius-lg);
  border-left: 4px solid var(--primary-500);
  border: 1px solid var(--primary-200);
  margin-top: 20px;
}
</style>
