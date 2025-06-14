import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import {
  setupToastMocks,
  mountWithToast,
  globalToastService
} from '../test-setup/toast-mock-fix.js'

describe('Settings - Integration Test', () => {
  let pinia
  let toastService

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    toastService = setupToastMocks()
  })

  it('設定画面の基本テスト', async () => {
    const SettingsStub = {
      template: `
        <div class="settings">
          <h1>設定</h1>
          
          <div class="settings-sections">
            <section class="api-settings">
              <h2>API設定</h2>
              <div class="form-group">
                <label for="api-url">API URL</label>
                <input 
                  id="api-url"
                  v-model="settings.apiUrl" 
                  type="text" 
                  placeholder="http://localhost:8000"
                />
              </div>
              <div class="form-group">
                <label for="timeout">タイムアウト (秒)</label>
                <input 
                  id="timeout"
                  v-model.number="settings.timeout" 
                  type="number" 
                  min="30" 
                  max="600"
                />
              </div>
            </section>
            
            <section class="ai-settings">
              <h2>AI設定</h2>
              <div class="form-group">
                <label for="ai-model">AIモデル</label>
                <select id="ai-model" v-model="settings.aiModel">
                  <option value="gpt-4">GPT-4</option>
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  <option value="claude-3">Claude 3</option>
                </select>
              </div>
              <div class="form-group">
                <label for="language">言語</label>
                <select id="language" v-model="settings.language">
                  <option value="ja">日本語</option>
                  <option value="en">English</option>
                  <option value="ko">한국어</option>
                </select>
              </div>
            </section>
            
            <section class="upload-settings">
              <h2>アップロード設定</h2>
              <div class="form-group">
                <label for="max-file-size">最大ファイルサイズ (MB)</label>
                <input 
                  id="max-file-size"
                  v-model.number="settings.maxFileSize" 
                  type="number" 
                  min="100" 
                  max="5000"
                />
              </div>
              <div class="form-group checkbox-group">
                <input 
                  id="auto-delete"
                  v-model="settings.autoDelete" 
                  type="checkbox"
                />
                <label for="auto-delete">処理完了後に自動削除</label>
              </div>
            </section>
          </div>
          
          <div class="settings-actions">
            <button @click="resetSettings" class="reset-btn">
              リセット
            </button>
            <button @click="saveSettings" class="save-btn" :disabled="!hasChanges">
              保存
            </button>
          </div>
          
          <div v-if="saved" class="save-status">
            設定が保存されました
          </div>
        </div>
      `,
      setup() {
        const { ref, computed, reactive } = require('vue')

        const defaultSettings = {
          apiUrl: 'http://localhost:8000',
          timeout: 300,
          aiModel: 'gpt-4',
          language: 'ja',
          maxFileSize: 1000,
          autoDelete: false
        }

        const settings = reactive({ ...defaultSettings })
        const originalSettings = ref({ ...defaultSettings })
        const saved = ref(false)

        const hasChanges = computed(() => {
          return (
            JSON.stringify(settings) !== JSON.stringify(originalSettings.value)
          )
        })

        const saveSettings = () => {
          // 設定の検証
          if (!settings.apiUrl) {
            globalToastService.add({
              severity: 'error',
              summary: 'エラー',
              detail: 'API URLは必須です'
            })
            return
          }

          if (settings.timeout < 30 || settings.timeout > 600) {
            globalToastService.add({
              severity: 'error',
              summary: 'エラー',
              detail: 'タイムアウトは30秒から600秒の間で設定してください'
            })
            return
          }

          // 保存処理（モック）
          originalSettings.value = { ...settings }
          saved.value = true

          globalToastService.add({
            severity: 'success',
            summary: '成功',
            detail: '設定が保存されました'
          })

          // 状態リセット
          setTimeout(() => {
            saved.value = false
          }, 3000)
        }

        const resetSettings = () => {
          Object.assign(settings, defaultSettings)
          globalToastService.add({
            severity: 'info',
            summary: '情報',
            detail: '設定をリセットしました'
          })
        }

        return {
          settings,
          hasChanges,
          saved,
          saveSettings,
          resetSettings
        }
      }
    }

    const { mountOptions, toastService: testToast } = mountWithToast(
      SettingsStub,
      {
        global: {
          plugins: [pinia]
        }
      }
    )

    const wrapper = mount(SettingsStub, mountOptions)

    // 初期表示の確認
    expect(wrapper.find('.settings').exists()).toBe(true)
    expect(wrapper.find('h1').text()).toBe('設定')

    // フォーム要素の確認
    expect(wrapper.find('#api-url').element.value).toBe('http://localhost:8000')
    expect(wrapper.find('#timeout').element.value).toBe('300')
    expect(wrapper.find('#ai-model').element.value).toBe('gpt-4')
    expect(wrapper.find('#language').element.value).toBe('ja')

    // 初期状態では変更なし
    expect(wrapper.vm.hasChanges).toBe(false)
    expect(wrapper.find('.save-btn').element.disabled).toBe(true)

    // 設定変更
    await wrapper.find('#api-url').setValue('http://api.example.com')
    await wrapper.find('#timeout').setValue(120)
    await wrapper.find('#ai-model').setValue('gpt-3.5-turbo')

    expect(wrapper.vm.hasChanges).toBe(true)
    expect(wrapper.find('.save-btn').element.disabled).toBe(false)

    // 保存
    await wrapper.find('.save-btn').trigger('click')

    expect(globalToastService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'success',
        summary: '成功',
        detail: '設定が保存されました'
      })
    )

    expect(wrapper.vm.saved).toBe(true)
    expect(wrapper.find('.save-status').exists()).toBe(true)

    // リセット
    await wrapper.find('.reset-btn').trigger('click')

    expect(wrapper.vm.settings.apiUrl).toBe('http://localhost:8000')
    expect(wrapper.vm.settings.timeout).toBe(300)
    expect(globalToastService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'info',
        summary: '情報',
        detail: '設定をリセットしました'
      })
    )

    wrapper.unmount()
  })

  it('設定バリデーションテスト', async () => {
    const ValidationTestStub = {
      template: `
        <div class="validation-test">
          <input 
            v-model="apiUrl" 
            @blur="validateApiUrl"
            class="api-url-input"
          />
          <input 
            v-model.number="timeout" 
            @blur="validateTimeout"
            class="timeout-input"
          />
          <button @click="save" class="save-btn">保存</button>
        </div>
      `,
      setup() {
        const { ref } = require('vue')

        const apiUrl = ref('')
        const timeout = ref(0)

        const validateApiUrl = () => {
          if (!apiUrl.value) {
            globalToastService.add({
              severity: 'error',
              summary: 'バリデーションエラー',
              detail: 'API URLは必須です'
            })
          } else if (!apiUrl.value.startsWith('http')) {
            globalToastService.add({
              severity: 'warn',
              summary: '警告',
              detail: 'API URLはhttpまたはhttpsで始まる必要があります'
            })
          }
        }

        const validateTimeout = () => {
          if (timeout.value < 30) {
            globalToastService.add({
              severity: 'error',
              summary: 'バリデーションエラー',
              detail: 'タイムアウトは30秒以上に設定してください'
            })
          } else if (timeout.value > 600) {
            globalToastService.add({
              severity: 'error',
              summary: 'バリデーションエラー',
              detail: 'タイムアウトは600秒以下に設定してください'
            })
          }
        }

        const save = () => {
          validateApiUrl()
          validateTimeout()

          if (
            apiUrl.value &&
            apiUrl.value.startsWith('http') &&
            timeout.value >= 30 &&
            timeout.value <= 600
          ) {
            globalToastService.add({
              severity: 'success',
              summary: '成功',
              detail: '設定が保存されました'
            })
          }
        }

        return {
          apiUrl,
          timeout,
          validateApiUrl,
          validateTimeout,
          save
        }
      }
    }

    const { mountOptions, toastService: testToast } = mountWithToast(
      ValidationTestStub,
      {
        global: {
          plugins: [pinia]
        }
      }
    )

    const wrapper = mount(ValidationTestStub, mountOptions)

    // 無効な値でのテスト
    await wrapper.find('.api-url-input').setValue('')
    await wrapper.find('.api-url-input').trigger('blur')

    expect(globalToastService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'error',
        detail: 'API URLは必須です'
      })
    )

    // プロトコルなしURL
    await wrapper.find('.api-url-input').setValue('example.com')
    await wrapper.find('.api-url-input').trigger('blur')

    expect(globalToastService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'warn',
        detail: 'API URLはhttpまたはhttpsで始まる必要があります'
      })
    )

    // 無効なタイムアウト
    await wrapper.find('.timeout-input').setValue(10)
    await wrapper.find('.timeout-input').trigger('blur')

    expect(globalToastService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'error',
        detail: 'タイムアウトは30秒以上に設定してください'
      })
    )

    // 有効な値での保存
    await wrapper.find('.api-url-input').setValue('https://api.example.com')
    await wrapper.find('.timeout-input').setValue(120)
    await wrapper.find('.save-btn').trigger('click')

    expect(globalToastService.add).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'success',
        detail: '設定が保存されました'
      })
    )

    wrapper.unmount()
  })
})
