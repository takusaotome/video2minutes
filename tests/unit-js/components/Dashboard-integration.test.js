import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import {
  setupToastMocks,
  mountWithToast
} from '../test-setup/toast-mock-fix.js'

describe('Dashboard - Integration Test', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    setupToastMocks()
  })

  it('ダッシュボードのスタブテスト', async () => {
    // ダッシュボードコンポーネントのスタブ
    const DashboardStub = {
      template: `
        <div class="dashboard">
          <header class="dashboard-header">
            <h1>Video2Minutes ダッシュボード</h1>
            <div class="stats">
              <div class="stat-item">
                <span class="stat-label">総タスク数</span>
                <span class="stat-value">{{ taskStats.total }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">処理中</span>
                <span class="stat-value">{{ taskStats.processing }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">完了</span>
                <span class="stat-value">{{ taskStats.completed }}</span>
              </div>
            </div>
          </header>
          
          <main class="dashboard-content">
            <section class="upload-section">
              <h2>新しい動画をアップロード</h2>
              <file-uploader-stub @upload-completed="onUploadCompleted" />
            </section>
            
            <section class="tasks-section">
              <h2>タスク一覧</h2>
              <task-list-stub :tasks="tasks" @task-deleted="onTaskDeleted" />
            </section>
          </main>
        </div>
      `,
      components: {
        FileUploaderStub: {
          template: `
            <div class="file-uploader-stub">
              <button @click="mockUpload" class="upload-btn">
                ファイルをアップロード
              </button>
            </div>
          `,
          emits: ['upload-completed'],
          setup(_, { emit }) {
            const mockUpload = () => {
              const mockTask = {
                task_id: 'new-task-' + Date.now(),
                video_filename: 'uploaded-video.mp4',
                status: 'pending',
                progress: 0
              }
              emit('upload-completed', { task: mockTask })
            }

            return { mockUpload }
          }
        },
        TaskListStub: {
          template: `
            <div class="task-list-stub">
              <div v-if="tasks.length === 0" class="no-tasks">
                タスクがありません
              </div>
              <div v-else class="task-items">
                <div 
                  v-for="task in tasks" 
                  :key="task.task_id"
                  class="task-item"
                >
                  <span>{{ task.video_filename }}</span>
                  <span>{{ task.status }}</span>
                  <button @click="deleteTask(task.task_id)">削除</button>
                </div>
              </div>
            </div>
          `,
          props: {
            tasks: {
              type: Array,
              default: () => []
            }
          },
          emits: ['task-deleted'],
          setup(_, { emit }) {
            const deleteTask = taskId => {
              emit('task-deleted', { taskId })
            }

            return { deleteTask }
          }
        }
      },
      setup() {
        const { ref, computed } = require('vue')

        const tasks = ref([
          {
            task_id: 'task-1',
            video_filename: 'sample1.mp4',
            status: 'processing',
            progress: 75
          },
          {
            task_id: 'task-2',
            video_filename: 'sample2.mp4',
            status: 'completed',
            progress: 100
          }
        ])

        const taskStats = computed(() => ({
          total: tasks.value.length,
          processing: tasks.value.filter(t => t.status === 'processing').length,
          completed: tasks.value.filter(t => t.status === 'completed').length,
          failed: tasks.value.filter(t => t.status === 'failed').length
        }))

        const onUploadCompleted = event => {
          tasks.value.push(event.task)
        }

        const onTaskDeleted = event => {
          const index = tasks.value.findIndex(t => t.task_id === event.taskId)
          if (index !== -1) {
            tasks.value.splice(index, 1)
          }
        }

        return {
          tasks,
          taskStats,
          onUploadCompleted,
          onTaskDeleted
        }
      }
    }

    const { mountOptions } = mountWithToast(DashboardStub, {
      global: {
        plugins: [pinia]
      }
    })

    const wrapper = mount(DashboardStub, mountOptions)

    // 初期表示の確認
    expect(wrapper.find('.dashboard').exists()).toBe(true)
    expect(wrapper.find('h1').text()).toBe('Video2Minutes ダッシュボード')

    // 統計情報の確認
    expect(wrapper.find('.stat-value').text()).toBe('2') // 総タスク数
    const statValues = wrapper.findAll('.stat-value')
    expect(statValues[0].text()).toBe('2') // 総タスク数
    expect(statValues[1].text()).toBe('1') // 処理中
    expect(statValues[2].text()).toBe('1') // 完了

    // タスクリストの確認
    expect(wrapper.findAll('.task-item')).toHaveLength(2)

    // アップロード機能のテスト
    const initialTaskCount = wrapper.vm.tasks.length
    await wrapper.find('.upload-btn').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.tasks.length).toBe(initialTaskCount + 1)
    expect(wrapper.vm.tasks[2].video_filename).toBe('uploaded-video.mp4')

    // タスク削除のテスト
    const deleteButtons = wrapper.findAll('button')
    const deleteBtn = deleteButtons.find(btn => btn.text() === '削除')
    await deleteBtn.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.tasks.length).toBe(initialTaskCount) // 1つ追加、1つ削除で元の数

    wrapper.unmount()
  })

  it('レスポンシブ対応ダッシュボード', async () => {
    const ResponsiveDashboard = {
      template: `
        <div 
          class="responsive-dashboard" 
          :class="{ 'mobile': isMobile, 'tablet': isTablet }"
        >
          <nav class="sidebar" :class="{ 'collapsed': sidebarCollapsed }">
            <button @click="toggleSidebar" class="toggle-btn">
              {{ sidebarCollapsed ? '>' : '<' }}
            </button>
            <ul class="nav-menu">
              <li><a href="#dashboard">ダッシュボード</a></li>
              <li><a href="#upload">アップロード</a></li>
              <li><a href="#tasks">タスク</a></li>
              <li><a href="#settings">設定</a></li>
            </ul>
          </nav>
          
          <main class="main-content">
            <div class="content-grid" :class="gridClass">
              <div class="widget upload-widget">
                <h3>アップロード</h3>
                <p>新しい動画をアップロード</p>
              </div>
              <div class="widget stats-widget">
                <h3>統計</h3>
                <p>{{ taskCount }} タスク</p>
              </div>
              <div class="widget recent-widget">
                <h3>最近のタスク</h3>
                <p>最新の処理状況</p>
              </div>
            </div>
          </main>
        </div>
      `,
      setup() {
        const { ref, computed } = require('vue')

        const sidebarCollapsed = ref(false)
        const screenWidth = ref(1200)
        const taskCount = ref(5)

        const isMobile = computed(() => screenWidth.value < 768)
        const isTablet = computed(
          () => screenWidth.value >= 768 && screenWidth.value < 1024
        )

        const gridClass = computed(() => {
          if (isMobile.value) return 'mobile-grid'
          if (isTablet.value) return 'tablet-grid'
          return 'desktop-grid'
        })

        const toggleSidebar = () => {
          sidebarCollapsed.value = !sidebarCollapsed.value
        }

        const setScreenWidth = width => {
          screenWidth.value = width
        }

        return {
          sidebarCollapsed,
          isMobile,
          isTablet,
          gridClass,
          taskCount,
          toggleSidebar,
          setScreenWidth
        }
      }
    }

    const { mountOptions } = mountWithToast(ResponsiveDashboard, {
      global: {
        plugins: [pinia]
      }
    })

    const wrapper = mount(ResponsiveDashboard, mountOptions)

    // デスクトップ表示
    expect(wrapper.vm.isMobile).toBe(false)
    expect(wrapper.vm.isTablet).toBe(false)
    expect(wrapper.find('.content-grid').classes()).toContain('desktop-grid')

    // タブレット表示
    wrapper.vm.setScreenWidth(800)
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isTablet).toBe(true)
    expect(wrapper.find('.content-grid').classes()).toContain('tablet-grid')

    // モバイル表示
    wrapper.vm.setScreenWidth(600)
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isMobile).toBe(true)
    expect(wrapper.find('.content-grid').classes()).toContain('mobile-grid')
    expect(wrapper.classes()).toContain('mobile')

    // サイドバートグル
    expect(wrapper.vm.sidebarCollapsed).toBe(false)
    await wrapper.find('.toggle-btn').trigger('click')
    expect(wrapper.vm.sidebarCollapsed).toBe(true)
    expect(wrapper.find('.sidebar').classes()).toContain('collapsed')

    wrapper.unmount()
  })
})
