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
    // console.error('API错误:', error)
    return Promise.reject(error)
  }
)

export default {
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
  getPingLogs: (hostId, page = 1, pageSize = 20) => {
    const params = { page, page_size: pageSize }
    if (hostId) params.host_id = hostId
    return api.get('/ping/logs', { params })
  },
  
  // 监控数据
  getRecords: (id, hours = 24) => api.get(`/records/${id}?hours=${hours}`),
  getAlerts: (hours = 24) => api.get(`/alerts?hours=${hours}`),
  getDashboard: () => api.get('/dashboard'),
  
  // 系统配置
  getConfig: () => api.get('/config'),
  updateConfig: (data) => api.put('/config', data),
  testNotification: (type) => api.post(`/test-notification/${type}`)
}
