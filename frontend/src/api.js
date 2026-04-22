import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response && (error.response.status === 401 || error.response.status === 403)) {
      const url = error.config?.url || ''
      if (!url.includes('/auth/')) {
        localStorage.removeItem('token')
        const currentPath = window.location.pathname
        if (currentPath !== '/login' && currentPath !== '/init') {
          window.location.href = '/login'
        }
      }
    }

    return Promise.reject(error)
  }
)

export default {
  checkAdmin: () => apiClient.get('/auth/check'),
  checkAdminExists: () => apiClient.get('/auth/check'),
  initAdmin: (data) => apiClient.post('/auth/init', data),
  login: (data) => apiClient.post('/auth/login', data),
  getCurrentUser: () => apiClient.get('/auth/me'),
  updatePassword: (data) => apiClient.put('/auth/update-password', data),

  getHosts: () => apiClient.get('/hosts'),
  createHost: (data) => apiClient.post('/hosts', data),
  updateHost: (id, data) => apiClient.put(`/hosts/${id}`, data),
  deleteHost: (id) => apiClient.delete(`/hosts/${id}`),
  refreshHostLocation: (id) => apiClient.post(`/hosts/${id}/refresh-location`),
  refreshHostIp: (id) => apiClient.post(`/hosts/${id}/refresh-ip`),

  pingNow: (id, background = false) => {
    const params = background ? { background: true } : {}
    return apiClient.post(`/ping/${id}`, null, { params })
  },
  pingStream: (id, onMessage, onError, onComplete) => {
    const token = localStorage.getItem('token')
    const eventSource = new EventSource(`/api/ping-stream/${id}?token=${token}`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (onMessage) {
          onMessage(data)
        }

        if (data.type === 'complete' || data.type === 'error') {
          eventSource.close()
          if (data.type === 'complete' && onComplete) {
            onComplete()
          }
        }
      } catch (err) {
        console.error('解析 SSE 数据失败:', err)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE 连接错误:', error)
      eventSource.close()
      if (onError) {
        onError(error)
      }
    }

    return eventSource
  },
  pingAll: () => apiClient.post('/ping-all'),
  getPingLogs: (hostId, page = 1, pageSize = 20, status = null, search = null) => {
    const params = { page, page_size: pageSize }
    if (hostId) {
      params.host_id = hostId
    }
    if (status) {
      params.status = status
    }
    if (search) {
      params.search = search
    }
    return apiClient.get('/ping/logs', { params })
  },

  getRecords: (id, hours = 24) => apiClient.get(`/records/${id}?hours=${hours}`),
  getAlerts: (hours = 24, page = 1, pageSize = 20, keyword = null, alertType = null, sentStatus = null) => {
    const params = { hours, page, page_size: pageSize }
    if (keyword) {
      params.keyword = keyword
    }
    if (alertType) {
      params.alert_type = alertType
    }
    if (sentStatus) {
      params.sent_status = sentStatus
    }
    return apiClient.get('/alerts', { params })
  },
  getDashboard: () => apiClient.get('/dashboard'),

  getDataBoardStats: (timeRange, sortBy = 'avg_packet_loss', sortOrder = 'desc') => {
    const params = { sort_by: sortBy, sort_order: sortOrder }
    return apiClient.get(`/databoard/stats/${timeRange}`, { params })
  },
  getHostDetailStats: (hostId, timeRange) => apiClient.get(`/databoard/host/${hostId}/${timeRange}`),

  getConfig: () => apiClient.get('/config'),
  updateConfig: (data) => apiClient.put('/config', data),
  testNotification: (type) => apiClient.post(`/test-notification/${type}`),
  sendReport: (reportType) => apiClient.post(`/reports/${reportType}/send`),

  getSystemLogs: (logType, module, page = 1, pageSize = 50, keyword = null, hours = null) => {
    const params = { page, page_size: pageSize }
    if (logType) {
      params.log_type = logType
    }
    if (module) {
      params.module = module
    }
    if (keyword) {
      params.keyword = keyword
    }
    if (hours) {
      params.hours = hours
    }
    return apiClient.get('/system-logs', { params })
  },
  cleanupSystemLogs: (days = 30) => apiClient.post('/system-logs/cleanup', null, { params: { days } }),

  triggerHourlyAggregation: () => apiClient.post('/data-maintenance/aggregate-hourly'),
  triggerDailyAggregation: () => apiClient.post('/data-maintenance/aggregate-daily'),
  triggerDataCleanup: (days) => apiClient.post('/data-maintenance/cleanup', null, { params: days ? { days } : {} }),

  getVisualConfig: () => apiClient.get('/datascreen/config'),
  updateVisualConfig: (data) => apiClient.put('/datascreen/config', data),
  getDataScreenConfig: () => apiClient.get('/datascreen/config'),
  updateDataScreenConfig: (data) => apiClient.put('/datascreen/config', data),
  getDataScreenPreview: () => apiClient.get('/datascreen/preview'),
  getPublicDataScreenStatus: () => apiClient.get('/public/datascreen/status'),
  getPublicDataScreen: () => apiClient.get('/public/datascreen'),
  getPublicAlerts: (hours = 24, limit = 12) => apiClient.get('/public/alerts', { params: { hours, limit } })
}
