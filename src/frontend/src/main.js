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