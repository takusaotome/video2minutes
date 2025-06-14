// PrimeVue統合テスト用のセットアップファイル
import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import { vi } from 'vitest'

// PrimeVueコンポーネントのインポート
import Button from 'primevue/button'
import Card from 'primevue/card'
import FileUpload from 'primevue/fileupload'
import ProgressBar from 'primevue/progressbar'
import Badge from 'primevue/badge'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import Checkbox from 'primevue/checkbox'
import RadioButton from 'primevue/radiobutton'
import Chips from 'primevue/chips'

// PrimeVueディレクティブ
import Tooltip from 'primevue/tooltip'
import BadgeDirective from 'primevue/badgedirective'
import Ripple from 'primevue/ripple'

/**
 * PrimeVue統合テスト用のアプリケーション設定を作成
 */
export function createPrimeVueTestApp() {
  const app = createApp({})

  // PrimeVue設定
  app.use(PrimeVue, {
    ripple: false, // テスト環境では無効化
    inputStyle: 'outlined',
    locale: {
      accept: 'はい',
      reject: 'いいえ',
      choose: '選択',
      upload: 'アップロード',
      cancel: 'キャンセル',
      clear: 'クリア',
      close: '閉じる'
    }
  })

  // サービス
  app.use(ToastService)
  app.use(ConfirmationService)

  // コンポーネント
  app.component('Button', Button)
  app.component('Card', Card)
  app.component('FileUpload', FileUpload)
  app.component('ProgressBar', ProgressBar)
  app.component('Badge', Badge)
  app.component('Dialog', Dialog)
  app.component('DataTable', DataTable)
  app.component('Column', Column)
  app.component('InputText', InputText)
  app.component('Textarea', Textarea)
  app.component('Dropdown', Dropdown)
  app.component('Calendar', Calendar)
  app.component('Checkbox', Checkbox)
  app.component('RadioButton', RadioButton)
  app.component('Chips', Chips)

  // ディレクティブ
  app.directive('tooltip', Tooltip)
  app.directive('badge', BadgeDirective)
  app.directive('ripple', Ripple)

  return app
}

/**
 * PrimeVueテスト用のマウントオプション生成
 */
export function createPrimeVueMountOptions(options = {}) {
  const testApp = createPrimeVueTestApp()

  return {
    global: {
      plugins: [
        [
          PrimeVue,
          {
            ripple: false,
            inputStyle: 'outlined'
          }
        ],
        ToastService,
        ConfirmationService,
        ...(options.global?.plugins || [])
      ],
      components: {
        Button,
        Card,
        FileUpload,
        ProgressBar,
        Badge,
        Dialog,
        DataTable,
        Column,
        InputText,
        Textarea,
        Dropdown,
        Calendar,
        Checkbox,
        RadioButton,
        Chips,
        ...(options.global?.components || {})
      },
      directives: {
        tooltip: Tooltip,
        badge: BadgeDirective,
        ripple: Ripple,
        ...(options.global?.directives || {})
      },
      provide: {
        ...(options.global?.provide || {})
      },
      mocks: {
        ...(options.global?.mocks || {})
      },
      stubs: {
        Teleport: true,
        ...(options.global?.stubs || {})
      }
    },
    ...options
  }
}

/**
 * PrimeVueコンポーネントのモック作成（軽量テスト用）
 */
export function createPrimeVueStubs() {
  return {
    // 基本コンポーネント
    Button: {
      template: `
        <button 
          :disabled="disabled" 
          :class="['p-button', severity && 'p-button-' + severity, size && 'p-button-' + size]"
          @click="$emit('click', $event)"
        >
          <i v-if="icon" :class="['p-button-icon', icon]"></i>
          <span v-if="label" class="p-button-label">{{ label }}</span>
          <slot v-else />
        </button>
      `,
      props: ['disabled', 'loading', 'label', 'icon', 'severity', 'size'],
      emits: ['click']
    },

    Card: {
      template: `
        <div class="p-card">
          <div v-if="$slots.header" class="p-card-header">
            <slot name="header" />
          </div>
          <div class="p-card-body">
            <div v-if="$slots.title" class="p-card-title">
              <slot name="title" />
            </div>
            <div v-if="$slots.subtitle" class="p-card-subtitle">
              <slot name="subtitle" />
            </div>
            <div class="p-card-content">
              <slot name="content" />
              <slot />
            </div>
            <div v-if="$slots.footer" class="p-card-footer">
              <slot name="footer" />
            </div>
          </div>
        </div>
      `,
      props: []
    },

    FileUpload: {
      template: `
        <div class="p-fileupload" :class="{ 'p-fileupload-basic': mode === 'basic' }">
          <div v-if="mode !== 'basic'" class="p-fileupload-buttonbar">
            <span class="p-button p-fileupload-choose">
              <input 
                ref="fileInput" 
                type="file" 
                :accept="accept" 
                :multiple="multiple"
                @change="onFileSelect"
                style="display: none;"
              />
              <span>{{ chooseLabel || 'Choose' }}</span>
            </span>
          </div>
          <div class="p-fileupload-content">
            <slot name="empty" />
            <div v-if="files && files.length > 0" class="p-fileupload-files">
              <div v-for="(file, index) in files" :key="index" class="p-fileupload-row">
                <span>{{ file.name }}</span>
                <button @click="removeFile(index)">Remove</button>
              </div>
            </div>
          </div>
        </div>
      `,
      props: {
        mode: { type: String, default: 'advanced' },
        multiple: Boolean,
        accept: String,
        maxFileSize: Number,
        customUpload: Boolean,
        disabled: Boolean,
        chooseLabel: String
      },
      emits: ['select', 'clear', 'uploader', 'remove'],
      data() {
        return {
          files: []
        }
      },
      methods: {
        onFileSelect(event) {
          const selectedFiles = Array.from(event.target.files)
          this.files = [...this.files, ...selectedFiles]
          this.$emit('select', { files: selectedFiles, originalEvent: event })
        },
        removeFile(index) {
          const removedFile = this.files[index]
          this.files.splice(index, 1)
          this.$emit('remove', { file: removedFile, files: this.files })
        },
        clear() {
          this.files = []
          this.$emit('clear')
        }
      },
      expose: ['clear']
    },

    ProgressBar: {
      template: `
        <div class="p-progressbar" role="progressbar" :aria-valuenow="value" aria-valuemin="0" aria-valuemax="100">
          <div class="p-progressbar-value" :style="{ width: value + '%' }"></div>
          <div v-if="showValue" class="p-progressbar-label">{{ value }}%</div>
        </div>
      `,
      props: {
        value: { type: Number, default: 0 },
        showValue: { type: Boolean, default: true }
      }
    },

    Badge: {
      template: `
        <span 
          class="p-badge" 
          :class="[
            severity && 'p-badge-' + severity,
            size && 'p-badge-' + size
          ]"
        >
          {{ value }}
        </span>
      `,
      props: ['value', 'severity', 'size']
    }
  }
}

/**
 * Toast サービスのモック
 */
export function createToastMock() {
  return {
    add: vi.fn(message => {
      console.log('Toast:', message)
    }),
    remove: vi.fn(),
    removeGroup: vi.fn(),
    removeAllGroups: vi.fn(),
    clear: vi.fn()
  }
}

/**
 * Confirmation サービスのモック
 */
export function createConfirmationMock() {
  return {
    require: vi.fn(options => {
      console.log('Confirmation:', options)
      // デフォルトで承認
      if (options.accept) {
        options.accept()
      }
    }),
    close: vi.fn()
  }
}
