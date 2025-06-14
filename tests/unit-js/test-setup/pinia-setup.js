// Pinia統合テスト用のセットアップファイル
import { createPinia, setActivePinia } from 'pinia'
import { createTestingPinia } from '@pinia/testing'
import { vi } from 'vitest'

/**
 * テスト用Piniaインスタンスの作成
 */
export function createTestPinia(options = {}) {
  const pinia = createTestingPinia({
    createSpy: vi.fn,
    initialState: {},
    stubActions: false, // アクションを実際に実行
    ...options
  })

  setActivePinia(pinia)
  return pinia
}

/**
 * 本物のPiniaインスタンスの作成（統合テスト用）
 */
export function createRealPinia() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return pinia
}

/**
 * ストアのモック作成ヘルパー
 */
export function createStoreMock(storeName, initialState = {}, actions = {}) {
  const mockStore = {
    $id: storeName,
    $state: { ...initialState },
    $patch: vi.fn(update => {
      if (typeof update === 'function') {
        update(mockStore.$state)
      } else {
        Object.assign(mockStore.$state, update)
      }
    }),
    $reset: vi.fn(() => {
      Object.assign(mockStore.$state, initialState)
    }),
    $subscribe: vi.fn(),
    $onAction: vi.fn(),
    $dispose: vi.fn(),
    ...actions
  }

  // ゲッターのプロキシ
  return new Proxy(mockStore, {
    get(target, prop) {
      if (prop in target) {
        return target[prop]
      }
      // ステートのプロパティを直接アクセス可能にする
      if (prop in target.$state) {
        return target.$state[prop]
      }
      return undefined
    },
    set(target, prop, value) {
      if (prop in target) {
        target[prop] = value
      } else {
        target.$state[prop] = value
      }
      return true
    }
  })
}

/**
 * TasksStoreのモック作成
 */
export function createTasksStoreMock(options = {}) {
  const defaultState = {
    tasks: [],
    loading: false,
    error: null,
    pollingInterval: null,
    activeConnections: new Set()
  }

  const defaultActions = {
    // ファイルアップロード
    uploadFile: vi.fn().mockImplementation(async function(file, progressCallback) {
      // 進捗をシミュレート
      if (progressCallback) {
        for (let i = 0; i <= 100; i += 20) {
          setTimeout(() => progressCallback(i), i * 10)
        }
      }

      const task = {
        task_id: `task-${Date.now()}`,
        status: 'pending',
        video_filename: file.name,
        video_size: file.size,
        upload_timestamp: new Date().toISOString(),
        progress: 0
      }

      // タスクリストに追加
      if (this.tasks && Array.isArray(this.tasks)) {
        this.tasks.push(task)
      }
      return task
    }),

    // タスク取得
    fetchTasks: vi.fn().mockResolvedValue([]),

    // タスクステータス取得
    fetchTaskStatus: vi.fn().mockImplementation(async function(taskId) {
      const task = this.tasks?.find(t => t.task_id === taskId)
      return task || null
    }),

    // タスク削除
    deleteTask: vi.fn().mockImplementation(async function(taskId) {
      if (this.tasks && Array.isArray(this.tasks)) {
        const index = this.tasks.findIndex(t => t.task_id === taskId)
        if (index !== -1) {
          this.tasks.splice(index, 1)
        }
      }
    }),

    // タスク再試行
    retryTask: vi.fn().mockImplementation(async function(taskId) {
      const task = this.tasks?.find(t => t.task_id === taskId)
      if (task) {
        task.status = 'pending'
        task.error_message = null
      }
      return task
    }),

    // ポーリング開始
    startPolling: vi.fn().mockImplementation(function () {
      if (this.pollingInterval) return

      this.pollingInterval = setInterval(() => {
        this.fetchTasks()
      }, 5000)
    }),

    // ポーリング停止
    stopPolling: vi.fn().mockImplementation(function () {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    }),

    // WebSocket接続
    connectWebSocket: vi.fn().mockImplementation(function (taskId) {
      this.activeConnections.add(taskId)
    }),

    // WebSocket切断
    disconnectWebSocket: vi.fn().mockImplementation(function (taskId) {
      this.activeConnections.delete(taskId)
    }),

    // 全WebSocket切断
    disconnectAllWebSockets: vi.fn().mockImplementation(function () {
      this.activeConnections.clear()
    }),

    // エラークリア
    clearError: vi.fn().mockImplementation(function () {
      this.error = null
    })
  }

  // オプションでカスタマイズ
  const state = { ...defaultState, ...options.state }
  const actions = { ...defaultActions, ...options.actions }

  return createStoreMock('tasks', state, actions)
}

/**
 * ストアのゲッター作成ヘルパー
 */
export function createStoreGetters(store) {
  return {
    // タスク関連のゲッター
    getTaskById: id => store.tasks.find(task => task.task_id === id),
    pendingTasks: store.tasks.filter(task => task.status === 'pending'),
    processingTasks: store.tasks.filter(task => task.status === 'processing'),
    completedTasks: store.tasks.filter(task => task.status === 'completed'),
    failedTasks: store.tasks.filter(task => task.status === 'failed'),
    taskStats: {
      total: store.tasks.length,
      pending: store.tasks.filter(t => t.status === 'pending').length,
      processing: store.tasks.filter(t => t.status === 'processing').length,
      completed: store.tasks.filter(t => t.status === 'completed').length,
      failed: store.tasks.filter(t => t.status === 'failed').length
    }
  }
}

/**
 * ストアクリーンアップ関数
 */
export function cleanupStore(store) {
  if (store.pollingInterval) {
    clearInterval(store.pollingInterval)
    store.pollingInterval = null
  }

  if (store.activeConnections) {
    store.activeConnections.clear()
  }

  store.$reset()
}

/**
 * 非同期ストアアクションのテストヘルパー
 */
export async function testAsyncStoreAction(store, actionName, ...args) {
  const action = store[actionName]
  if (!action) {
    throw new Error(`Action ${actionName} not found in store`)
  }

  const loadingBefore = store.loading

  try {
    const result = await action.apply(store, args)
    return { result, error: null }
  } catch (error) {
    return { result: null, error }
  } finally {
    // ローディング状態のリセット確認
    expect(store.loading).toBe(loadingBefore)
  }
}

/**
 * ストア状態変更のテストヘルパー
 */
export function expectStoreStateChange(store, expectedChanges) {
  Object.entries(expectedChanges).forEach(([key, value]) => {
    expect(store[key]).toEqual(value)
  })
}

/**
 * ストアアクション呼び出しのテストヘルパー
 */
export function expectStoreActionCalled(store, actionName, ...expectedArgs) {
  const action = store[actionName]
  expect(action).toHaveBeenCalledWith(...expectedArgs)
}

/**
 * マウントオプション用のPinia設定
 */
export function createPiniaMountOptions(stores = {}, options = {}) {
  const pinia = createTestPinia({
    initialState: options.initialState || {},
    stubActions: options.stubActions !== undefined ? options.stubActions : false
  })

  return {
    global: {
      plugins: [pinia],
      ...options.global
    }
  }
}
