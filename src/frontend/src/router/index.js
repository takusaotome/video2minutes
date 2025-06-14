import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'
import MinutesView from '@/views/MinutesView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/minutes/:taskId',
      name: 'minutes',
      component: MinutesView,
      props: true
    }
  ]
})

export default router