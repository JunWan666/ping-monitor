import { createRouter, createWebHistory } from 'vue-router'
import api from './api'
import { loadRouteWithRetry } from './lib/asyncLoader'

const page = (loader) => loadRouteWithRetry(loader)

const adminChildren = [
  {
    path: 'dashboard',
    name: 'AdminDashboard',
    component: page(() => import('./components/Dashboard.vue')),
    meta: { menuKey: 'dashboard', title: '仪表盘', description: '集中查看监控状态与异常趋势' }
  },
  {
    path: 'datascreen',
    name: 'AdminDataScreen',
    component: page(() => import('./components/DataScreen.vue')),
    meta: { menuKey: 'datascreen', title: '可视化大屏', description: '实时了解节点分布与网络健康度', previewMode: true }
  },
  {
    path: 'databoard',
    name: 'AdminDataBoard',
    component: page(() => import('./components/DataBoard.vue')),
    meta: { menuKey: 'databoard', title: '数据看板', description: '按时间范围分析延迟、丢包与在线率' }
  },
  {
    path: 'hosts',
    name: 'AdminHosts',
    component: page(() => import('./components/HostManage.vue')),
    meta: { menuKey: 'hosts', title: '主机管理', description: '管理监控目标、状态与探测操作' }
  },
  {
    path: 'domains',
    name: 'AdminDomains',
    component: page(() => import('./components/DomainMonitor.vue')),
    props: (route) => ({
      focusRequest: route.query.focus ? { id: Number(route.query.focus) } : null
    }),
    meta: { menuKey: 'domains', title: '域名监控', description: '查看域名解析、到期与 DNS 健康状态' }
  },
  {
    path: 'alerts',
    name: 'AdminAlerts',
    component: page(() => import('./components/AlertList.vue')),
    meta: { menuKey: 'alerts', title: '告警记录', description: '追踪异常对象、发生时间与通知结果' }
  },
  {
    path: 'settings',
    name: 'AdminSettings',
    component: page(() => import('./components/Settings.vue')),
    props: { activeTab: 'settings-basic' },
    meta: { menuKey: 'settings-basic', title: '基本设置', section: 'settings', description: '配置探测、通知与数据保留策略' }
  },
  {
    path: 'settings/datascreen',
    name: 'AdminDataScreenSettings',
    component: page(() => import('./components/DataScreenSettings.vue')),
    meta: { menuKey: 'settings-datascreen', title: '可视化设置', section: 'settings', description: '配置公开大屏、地图与展示策略' }
  },
  {
    path: 'logs/ping',
    name: 'AdminPingLogs',
    component: page(() => import('./components/Settings.vue')),
    props: { activeTab: 'settings-logs' },
    meta: { menuKey: 'settings-logs', title: 'Ping 日志', section: 'settings', description: '检索每次探测的结果与耗时' }
  },
  {
    path: 'logs/system',
    name: 'AdminSystemLogs',
    component: page(() => import('./components/SystemLogs.vue')),
    meta: { menuKey: 'settings-system-logs', title: '系统日志', section: 'settings', description: '查看系统事件、任务与错误记录' }
  },
  {
    path: 'backups',
    name: 'AdminBackups',
    component: page(() => import('./components/DatabaseBackup.vue')),
    meta: { menuKey: 'settings-backup', title: '数据备份', section: 'settings', description: '导出、导入并查看备份任务状态' }
  },
  {
    path: 'change-password',
    name: 'AdminChangePassword',
    component: page(() => import('./components/UserProfile.vue')),
    meta: { menuKey: 'settings-profile', title: '修改密码', section: 'settings', description: '维护管理员账号安全信息' }
  },
  {
    path: 'me',
    name: 'AdminMe',
    component: page(() => import('./components/AdminMobileMe.vue')),
    meta: { menuKey: 'mobile-me', title: '我的', section: 'settings', description: '账号与常用设置' }
  }
]

const routes = [
  {
    path: '/',
    name: 'DataScreen',
    component: page(() => import('./components/DataScreen.vue')),
    meta: { requiresAuth: false }
  },
  {
    path: '/datascreen-preview',
    name: 'DataScreenPreview',
    component: page(() => import('./components/DataScreen.vue')),
    meta: { requiresAuth: true, previewMode: true }
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: page(() => import('./components/AdminLogin.vue')),
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: page(() => import('./components/Login.vue')),
    meta: { requiresAuth: false }
  },
  {
    path: '/init',
    name: 'InitAdmin',
    component: page(() => import('./components/InitAdmin.vue')),
    meta: { requiresAuth: false }
  },
  {
    path: '/admin',
    name: 'Main',
    component: page(() => import('./components/Main.vue')),
    redirect: { name: 'AdminDashboard' },
    meta: { requiresAuth: true },
    children: adminChildren
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: { name: 'AdminDashboard' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ left: 0, top: 0 })
})

const isSafeRedirect = (redirect) => typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')

const withRedirect = (path, redirect) => {
  if (!isSafeRedirect(redirect)) return path
  return { path, query: { redirect } }
}

const resolveAdminEntry = async (redirect) => {
  try {
    const result = await api.checkAdmin()
    return result.has_admin ? withRedirect('/admin/login', redirect) : withRedirect('/init', redirect)
  } catch (error) {
    return withRedirect('/admin/login', redirect)
  }
}

const resolvePublicDataScreenEntry = async (hasToken) => {
  try {
    const result = await api.getPublicDataScreenStatus()
    if (result.enabled) return true
  } catch (error) {
    return hasToken ? { name: 'AdminDashboard' } : '/login'
  }

  return hasToken ? { name: 'AdminDashboard' } : '/login'
}

const resolveLoginRedirect = (to) => {
  const redirect = typeof to.query?.redirect === 'string' ? to.query.redirect : ''
  return isSafeRedirect(redirect) ? redirect : '/admin/dashboard'
}

router.beforeEach(async (to) => {
  const token = localStorage.getItem('token')

  if (to.path === '/') {
    return resolvePublicDataScreenEntry(Boolean(token))
  }

  if (to.path === '/login' || to.path === '/init' || to.path === '/admin/login') {
    if (token) return resolveLoginRedirect(to)
    return true
  }

  if (to.meta.requiresAuth && !token) {
    return resolveAdminEntry(to.fullPath)
  }

  return true
})

export default router
