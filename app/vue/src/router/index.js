import { createRouter, createWebHistory } from 'vue-router'
import i18n from '@/i18n'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: 'dashboard.title' }
      },
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('@/views/Upload.vue'),
        meta: { title: 'upload.title' }
      },
      {
        path: 'graph',
        name: 'Graph',
        component: () => import('@/views/Graph.vue'),
        meta: { title: 'graph.title' }
      },
      {
        path: 'query',
        name: 'Query',
        component: () => import('@/views/Query.vue'),
        meta: { title: 'query.title' }
      },
      {
        path: 'status',
        name: 'Status',
        component: () => import('@/views/Status.vue'),
        meta: { title: 'status.title' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    const t = i18n.global.t
    document.title = `${t(to.meta.title)} | ${t('app.page_title')}`
  }
  next()
})

export default router

