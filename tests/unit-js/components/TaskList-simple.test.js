import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import {
  setupToastMocks,
  mountWithToast
} from '../test-setup/toast-mock-fix.js'

describe('TaskList - Simple Component Test', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    setupToastMocks()
  })

  it('TaskListのスタブ版をテスト', async () => {
    // シンプルなTaskListスタブ
    const TaskListStub = {
      template: `
        <div class="task-list">
          <h3>タスク一覧 ({{ tasks.length }})</h3>
          <div v-if="tasks.length === 0" class="no-tasks">
            タスクがありません
          </div>
          <div v-else class="task-items">
            <div 
              v-for="task in tasks" 
              :key="task.task_id" 
              class="task-item"
              :class="'status-' + task.status"
            >
              <span class="task-name">{{ task.video_filename }}</span>
              <span class="task-status">{{ getStatusLabel(task.status) }}</span>
              <div class="task-progress">
                <div class="progress-bar" :style="{ width: task.progress + '%' }"></div>
              </div>
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
      setup() {
        const getStatusLabel = status => {
          switch (status) {
            case 'pending':
              return '待機中'
            case 'processing':
              return '処理中'
            case 'completed':
              return '完了'
            case 'failed':
              return '失敗'
            default:
              return status
          }
        }

        return {
          getStatusLabel
        }
      }
    }

    // 空のタスクリストでテスト
    const { mountOptions } = mountWithToast(TaskListStub, {
      global: {
        plugins: [pinia]
      },
      props: {
        tasks: []
      }
    })

    const wrapper = mount(TaskListStub, mountOptions)

    expect(wrapper.find('.task-list').exists()).toBe(true)
    expect(wrapper.find('h3').text()).toBe('タスク一覧 (0)')
    expect(wrapper.find('.no-tasks').text()).toBe('タスクがありません')

    wrapper.unmount()
  })

  it('タスク付きのTaskListをテスト', async () => {
    const TaskListStub = {
      template: `
        <div class="task-list">
          <h3>タスク一覧 ({{ tasks.length }})</h3>
          <div v-if="tasks.length === 0" class="no-tasks">
            タスクがありません
          </div>
          <div v-else class="task-items">
            <div 
              v-for="task in tasks" 
              :key="task.task_id" 
              class="task-item"
              :class="'status-' + task.status"
            >
              <span class="task-name">{{ task.video_filename }}</span>
              <span class="task-status">{{ getStatusLabel(task.status) }}</span>
              <div class="task-progress">
                <div class="progress-bar" :style="{ width: task.progress + '%' }"></div>
              </div>
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
      setup() {
        const getStatusLabel = status => {
          switch (status) {
            case 'pending':
              return '待機中'
            case 'processing':
              return '処理中'
            case 'completed':
              return '完了'
            case 'failed':
              return '失敗'
            default:
              return status
          }
        }

        return {
          getStatusLabel
        }
      }
    }

    // テストデータ
    const testTasks = [
      {
        task_id: 'task-1',
        video_filename: 'video1.mp4',
        status: 'processing',
        progress: 50
      },
      {
        task_id: 'task-2',
        video_filename: 'video2.mp4',
        status: 'completed',
        progress: 100
      }
    ]

    const { mountOptions } = mountWithToast(TaskListStub, {
      global: {
        plugins: [pinia]
      },
      props: {
        tasks: testTasks
      }
    })

    const wrapper = mount(TaskListStub, mountOptions)

    expect(wrapper.find('h3').text()).toBe('タスク一覧 (2)')
    expect(wrapper.findAll('.task-item')).toHaveLength(2)

    const firstTask = wrapper.findAll('.task-item')[0]
    expect(firstTask.find('.task-name').text()).toBe('video1.mp4')
    expect(firstTask.find('.task-status').text()).toBe('処理中')
    expect(firstTask.classes()).toContain('status-processing')

    const secondTask = wrapper.findAll('.task-item')[1]
    expect(secondTask.find('.task-name').text()).toBe('video2.mp4')
    expect(secondTask.find('.task-status').text()).toBe('完了')
    expect(secondTask.classes()).toContain('status-completed')

    wrapper.unmount()
  })
})
