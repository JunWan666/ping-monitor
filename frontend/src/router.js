import { createRouter, createWebHistory } from 'vue-router'
import api from './api'
import { loadRouteWithRetry } from './lib/asyncLoader'

const routes = [
  {
    path: '/',
    name: 'DataScreen',
    component: loadRouteWithRetry(() => import('./components/DataScreen.vue')),
    meta: { requiresAuth: false }
  },
  {
    path: '/datascreen-preview',
    name: 'DataScreenPreview',
    component: loadRouteWithRetry(() => import('./components/DataScreen.vue')),
    meta: { requiresAuth: true, previewMode: true }
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: loadRouteWithRetry(() => import('./components/AdminLogin.vue')),
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: loadRouteWithRetry(() => import('./components/Login.vue')),
    meta: { requiresAuth: false }
  },
  {
    path: '/init',
    name: 'InitAdmin',
    component: loadRouteWithRetry(() => import('./components/InitAdmin.vue')),
    meta: { requiresAuth: false }
  },
  {
    path: '/admin',
    name: 'Main',
    component: loadRouteWithRetry(() => import('./components/Main.vue')),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const resolveAdminEntry = async () => {
  try {
    const result = await api.checkAdmin()
    return result.has_admin ? '/admin/login' : '/init'
  } catch (error) {
    return '/admin/login'
  }
}

const resolvePublicDataScreenEntry = async (hasToken) => {
  try {
    const result = await api.getPublicDataScreenStatus()
    if (result.enabled) {
      return true
    }
  } catch (error) {
    return hasToken ? '/admin' : '/login'
  }

  return hasToken ? '/admin' : '/login'
}

router.beforeEach(async (to) => {
  const token = localStorage.getItem('token')

  if (to.path === '/') {
    return resolvePublicDataScreenEntry(Boolean(token))
  }

  if (to.path === '/login' || to.path === '/init' || to.path === '/admin/login') {
    if (token) {
      return '/admin'
    }
    return true
  }

  if (to.meta.requiresAuth && !token) {
    return resolveAdminEntry()
  }

  return true
})

export default router
