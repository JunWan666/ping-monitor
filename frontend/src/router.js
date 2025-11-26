import { createRouter, createWebHistory } from 'vue-router'
import api from './api'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('./components/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/init',
    name: 'InitAdmin',
    component: () => import('./components/InitAdmin.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Main',
    component: () => import('./components/Main.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const token = localStorage.getItem('token')
  
  // 如果访问登录页或初始化页
  if (to.path === '/login' || to.path === '/init') {
    // 如果已登录，跳转首页
    if (token) {
      next('/')
      return
    }
    // 未登录，允许访问
    next()
    return
  }
  
  // 访问其他页面（需要认证）
  if (!token) {
    // 检查是否存在管理员
    try {
      const result = await api.checkAdmin()
      if (result.has_admin) {
        next('/login')
      } else {
        next('/init')
      }
    } catch (error) {
      next('/login')
    }
    return
  }
  
  next()
})

export default router
