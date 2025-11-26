import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 添加token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    // 处理401/403错误，跳转到登录页（除非是认证接口）
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      const url = error.config.url
      // 如果不是认证相关的接口，则清除token并跳转
      if (!url.includes('/auth/')) {
        localStorage.removeItem('token')
        const currentPath = window.location.pathname
        // 只有当前不在登录页和初始化页时才跳转
        if (currentPath !== '/login' && currentPath !== '/init') {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default {
  // 认证
  checkAdmin: () => api.get('/auth/check'),
  initAdmin: (data) => api.post('/auth/init', data),
  login: (data) => api.post('/auth/login', data),
  getCurrentUser: () => api.get('/auth/me'),
  updatePassword: (data) => api.put('/auth/update-password', data),
  
  // 主机管理
  getHosts: () => api.get('/hosts'),
  createHost: (data) => api.post('/hosts', data),
  updateHost: (id, data) => api.put(`/hosts/${id}`, data),
  deleteHost: (id) => api.delete(`/hosts/${id}`),
  
  // Ping操作
  pingNow: (id, background = false) => {
    const params = background ? { background: true } : {}
    return api.post(`/ping/${id}`, null, { params })
  },
  pingAll: () => api.post('/ping-all'),
  getPingLogs: (hostId, page = 1, pageSize = 20, status = null) => {
    const params = { page, page_size: pageSize }
    if (hostId) params.host_id = hostId
    if (status) params.status = status
    return api.get('/ping/logs', { params })
  },
  
  // 监控数据
  getRecords: (id, hours = 24) => api.get(`/records/${id}?hours=${hours}`),
  getAlerts: (hours = 24, page = 1, pageSize = 20) => {
    const params = { hours, page, page_size: pageSize }
    return api.get('/alerts', { params })
  },
  getDashboard: () => api.get('/dashboard'),
  
  // 系统配置
  getConfig: () => api.get('/config'),
  updateConfig: (data) => api.put('/config', data),
  testNotification: (type) => api.post(`/test-notification/${type}`)
}
