import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'

import App from './App.vue'
import router from './router'

import 'primevue/resources/themes/lara-light-blue/theme.css'
import 'primevue/resources/primevue.min.css'
import 'primeicons/primeicons.css'
import 'highlight.js/styles/github-dark.css'

// Custom global styles
import './styles/global.css'

// Basic認証チェック
const checkBasicAuth = () => {
  const username = import.meta.env.VITE_BASIC_AUTH_USERNAME
  const password = import.meta.env.VITE_BASIC_AUTH_PASSWORD

  if (!username || !password) {
    return true // Basic認証が設定されていない場合はスキップ
  }

  // 既に認証済みかチェック
  const authToken = localStorage.getItem('basicAuthToken')
  if (authToken) {
    const [storedUsername, storedPassword] = atob(authToken).split(':')
    if (storedUsername === username && storedPassword === password) {
      return true
    }
  }

  // Basic認証ダイアログ表示
  const enteredUsername = prompt('ユーザー名を入力してください:')
  if (!enteredUsername) return false

  const enteredPassword = prompt('パスワードを入力してください:')
  if (!enteredPassword) return false

  if (enteredUsername === username && enteredPassword === password) {
    // 認証成功 - トークンを保存
    const token = btoa(`${enteredUsername}:${enteredPassword}`)
    localStorage.setItem('basicAuthToken', token)
    return true
  } else {
    alert('認証に失敗しました')
    return false
  }
}

// 認証チェック実行
if (!checkBasicAuth()) {
  document.body.innerHTML =
    '<div style="text-align: center; margin-top: 50px;"><h1>認証が必要です</h1></div>'
  throw new Error('認証が必要です')
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  ripple: true
})
app.use(ToastService)
app.use(ConfirmationService)

// Global directives
app.directive('tooltip', Tooltip)

app.mount('#app')
