<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">总主机数</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px">{{ dashboard.total_hosts }}</div>
            </div>
            <el-icon :size="40" color="#409eff"><Monitor /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">启用主机</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px; color: #67c23a">{{ dashboard.enabled_hosts }}</div>
            </div>
            <el-icon :size="40" color="#67c23a"><SuccessFilled /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">在线主机</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px; color: #67c23a">{{ onlineHosts }}</div>
            </div>
            <el-icon :size="40" color="#67c23a"><CircleCheckFilled /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">异常主机</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px; color: #f56c6c">{{ abnormalHosts }}</div>
            </div>
            <el-icon :size="40" color="#f56c6c"><CircleCloseFilled /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">近1小时告警</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px; color: #f56c6c">{{ dashboard.recent_alerts }}</div>
            </div>
            <el-icon :size="40" color="#f56c6c"><WarningFilled /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">在线率</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px; color: #e6a23c">{{ onlineRate }}%</div>
            </div>
            <el-icon :size="40" color="#e6a23c"><TrendCharts /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 整体监控数据图表 -->
    <el-card shadow="hover" style="margin-bottom: 20px">
      <template #header>
        <span style="font-weight: bold">监控数据趋势</span>
      </template>
      <div ref="overallChartDom" style="width: 100%; height: 300px"></div>
    </el-card>

    <!-- 主机状态列表 -->
    <el-card shadow="hover" style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: bold">主机状态</span>
          <div style="display: flex; align-items: center; gap: 10px">
            <el-input 
              v-model="searchKeyword" 
              placeholder="搜索主机名称或地址" 
              clearable
              style="width: 280px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select 
              v-model="statusFilter" 
              placeholder="状态筛选" 
              clearable
              style="width: 130px"
            >
              <el-option label="正常" value="正常" />
              <el-option label="异常" value="异常" />
            </el-select>
            <el-button type="success" size="small" @click="pingAllHosts" :loading="pingAllLoading">
              <el-icon><Promotion /></el-icon> 立即Ping全部
            </el-button>
            <el-button type="primary" size="small" @click="loadData" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="filteredHostStatus" style="width: 100%" :row-class-name="getRowClassName">
        <el-table-column label="序号" width="80" align="center" header-align="center">
          <template #default="{ $index }">
            {{ (currentPage - 1) * pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="name" label="主机名称" width="150" align="center" header-align="center" />
        <el-table-column label="地址" width="200" align="center" header-align="center">
          <template #default="{ row }">
            <span 
              @click="copyAddress(row.address)" 
              style="cursor: pointer; color: #409eff; text-decoration: underline"
              :title="'点击复制: ' + row.address"
            >
              {{ row.address }}
            </span>
            <el-icon 
              @click="copyAddress(row.address)" 
              style="margin-left: 5px; cursor: pointer; color: #409eff"
              :title="'复制地址'"
            >
              <CopyDocument />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center" header-align="center">
          <template #header>
            <div @click="handleSort('status')" style="cursor: pointer; user-select: none; position: relative; display: inline-block;">
              <span>状态</span>
              <el-icon style="position: absolute; right: -18px; top: 50%; transform: translateY(-50%);">
                <ArrowUp v-if="sortColumn === 'status' && sortOrder === 'asc'" />
                <ArrowDown v-else />
              </el-icon>
            </div>
          </template>
          <template #default="{ row }">
            <el-tag v-if="row.status === '正常'" type="success">{{ row.status }}</el-tag>
            <el-tag v-else-if="row.status === '异常'" type="danger">{{ row.status }}</el-tag>
            <el-tag v-else type="info">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="丢包率" width="120" align="center" header-align="center">
          <template #header>
            <div @click="handleSort('packet_loss')" style="cursor: pointer; user-select: none; position: relative; display: inline-block;">
              <span>丢包率</span>
              <el-icon style="position: absolute; right: -18px; top: 50%; transform: translateY(-50%);">
                <ArrowUp v-if="sortColumn === 'packet_loss' && sortOrder === 'asc'" />
                <ArrowDown v-else />
              </el-icon>
            </div>
          </template>
          <template #default="{ row }">
            <span v-if="row.packet_loss !== null">{{ row.packet_loss }}%</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="平均延迟" width="120" align="center" header-align="center">
          <template #header>
            <div @click="handleSort('avg_rtt')" style="cursor: pointer; user-select: none; position: relative; display: inline-block;">
              <span>平均延迟</span>
              <el-icon style="position: absolute; right: -18px; top: 50%; transform: translateY(-50%);">
                <ArrowUp v-if="sortColumn === 'avg_rtt' && sortOrder === 'asc'" />
                <ArrowDown v-else />
              </el-icon>
            </div>
          </template>
          <template #default="{ row }">
            <span v-if="row.avg_rtt !== null">{{ row.avg_rtt }}ms</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="最后检查" min-width="180" align="center" header-align="center">
          <template #default="{ row }">
            <span v-if="row.last_check">{{ formatTime(row.last_check) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" header-align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewChart(row)">查看图表</el-button>
            <el-button type="success" size="small" @click="pingHost(row)">立即Ping</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div style="margin-top: 15px; display: flex; justify-content: center">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredAllHosts.length"
          layout="total, sizes, prev, pager, next, jumper"
          :small="true"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 监控图表对话框 -->
    <el-dialog v-model="chartVisible" :title="`${selectedHost?.name} 监控数据`" width="80%">
      <div ref="chartDom" style="width: 100%; height: 400px"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { echarts } from '../lib/echarts'

const loading = ref(false)
const pingAllLoading = ref(false)
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const sortColumn = ref('status')
const sortOrder = ref('desc')
const chartPointLimit = ref(12)
const chartSettingsLoaded = ref(false)
const dashboard = reactive({
  total_hosts: 0,
  enabled_hosts: 0,
  recent_alerts: 0,
  host_status: []
})

const chartVisible = ref(false)
const selectedHost = ref(null)
const chartDom = ref(null)
const overallChartDom = ref(null)
let chartInstance = null
let overallChartInstance = null
let refreshTimer = null
let resizeHandler = null
const lastLoadedAt = ref(0)

const onlineRate = computed(() => {
  if (dashboard.total_hosts === 0) return 0
  const online = dashboard.host_status.filter(h => h.status === '正常').length
  return Math.round((online / dashboard.total_hosts) * 100)
})

const onlineHosts = computed(() => {
  return dashboard.host_status.filter(h => h.status === '正常').length
})

const abnormalHosts = computed(() => {
  return dashboard.host_status.filter(h => h.status === '异常').length
})

// 排序函数
const sortHosts = (hosts) => {
  if (!sortColumn.value) return hosts
  
  return [...hosts].sort((a, b) => {
    let aVal, bVal
    
    switch (sortColumn.value) {
      case 'status':
        // 异常 > 正常 > 未知
        const statusOrder = { '异常': 3, '正常': 2, '未知': 1 }
        aVal = statusOrder[a.status] || 0
        bVal = statusOrder[b.status] || 0
        break
      case 'packet_loss':
        aVal = a.packet_loss ?? -1
        bVal = b.packet_loss ?? -1
        break
      case 'avg_rtt':
        aVal = a.avg_rtt ?? -1
        bVal = b.avg_rtt ?? -1
        break
      default:
        return 0
    }
    
    if (sortOrder.value === 'asc') {
      return aVal - bVal
    } else {
      return bVal - aVal
    }
  })
}

// 搜索和筛选后的所有主机
const filteredAllHosts = computed(() => {
  let result = [...dashboard.host_status]
  
  // 关键字搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(host => 
      host.name.toLowerCase().includes(keyword) || 
      host.address.toLowerCase().includes(keyword)
    )
  }
  
  // 状态筛选
  if (statusFilter.value) {
    result = result.filter(host => host.status === statusFilter.value)
  }
  
  // 排序
  result = sortHosts(result)
  
  return result
})

// 当前页显示的主机
const filteredHostStatus = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredAllHosts.value.slice(start, end)
})

const ensureChartSettings = async (force = false) => {
  if (chartSettingsLoaded.value && !force) {
    return
  }

  try {
    const config = await api.getConfig()
    chartPointLimit.value = Math.max(3, config.dashboard_chart_points || 12)
  } catch (error) {
    console.warn('获取仪表盘图表配置失败，使用默认值', error)
  } finally {
    chartSettingsLoaded.value = true
  }
}

const ensureOverallChart = () => {
  if (!overallChartDom.value) {
    return null
  }

  if (!overallChartInstance) {
    overallChartInstance = echarts.init(overallChartDom.value)
  }

  return overallChartInstance
}

const ensureHostChart = () => {
  if (!chartDom.value) {
    return null
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartDom.value)
  }

  return chartInstance
}

const startRefreshTimer = () => {
  if (refreshTimer) {
    return
  }

  refreshTimer = setInterval(() => {
    if (document.hidden) {
      return
    }
    loadData()
  }, 30000)
}

const stopRefreshTimer = () => {
  if (!refreshTimer) {
    return
  }

  clearInterval(refreshTimer)
  refreshTimer = null
}

const bindResizeListener = () => {
  if (resizeHandler) {
    return
  }

  resizeHandler = () => {
    overallChartInstance?.resize()
    chartInstance?.resize()
  }
  window.addEventListener('resize', resizeHandler)
}

const unbindResizeListener = () => {
  if (!resizeHandler) {
    return
  }

  window.removeEventListener('resize', resizeHandler)
  resizeHandler = null
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

// 排序处理
const handleSort = (column) => {
  if (sortColumn.value === column) {
    // 切换排序顺序
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    // 新列，默认降序
    sortColumn.value = column
    sortOrder.value = 'desc'
  }
}

// 行样式处理
const getRowClassName = ({ row }) => {
  return row.status === '异常' ? 'error-row' : ''
}

const loadData = async (options = {}) => {
  if (loading.value) {
    return
  }

  loading.value = true
  try {
    await ensureChartSettings(options.forceChartSettings === true)

    const [dashboardData, databoardData] = await Promise.all([
      api.getDashboard(),
      api.getDataBoardStats('1h')
    ])

    Object.assign(dashboard, dashboardData)
    lastLoadedAt.value = Date.now()
    await nextTick()
    renderOverallChart(databoardData.trend_data || [])
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const renderOverallChart = (trendData) => {
  const instance = ensureOverallChart()
  if (!instance) return

  if (!trendData || trendData.length === 0) {
    instance.clear()
    return
  }

  const points = trendData.slice(-chartPointLimit.value)
  const times = points.map(item => item.time)
  const packetLoss = points.map(item => item.avg_packet_loss)
  const avgRtt = points.map(item => item.avg_rtt)
  const onlineRates = points.map(item => item.online_rate)

  instance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['在线率(%)', '平均丢包率(%)', '平均延迟(ms)'],
      top: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: {
        rotate: 45,
        interval: 'auto'
      },
      boundaryGap: false
    },
    yAxis: [
      {
        type: 'value',
        name: '百分比(%)',
        position: 'left',
        axisLine: {
          lineStyle: {
            color: '#67c23a'
          }
        },
        splitLine: {
          show: true,
          lineStyle: {
            type: 'dashed'
          }
        }
      },
      {
        type: 'value',
        name: '延迟(ms)',
        position: 'right',
        axisLine: {
          lineStyle: {
            color: '#409eff'
          }
        },
        splitLine: {
          show: false
        }
      }
    ],
    series: [
      {
        name: '在线率(%)',
        type: 'line',
        data: onlineRates,
        smooth: true,
        itemStyle: { color: '#67c23a' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
              { offset: 1, color: 'rgba(103, 194, 58, 0.05)' }
            ]
          }
        }
      },
      {
        name: '平均丢包率(%)',
        type: 'line',
        data: packetLoss,
        smooth: true,
        itemStyle: { color: '#f56c6c' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(245, 108, 108, 0.3)' },
              { offset: 1, color: 'rgba(245, 108, 108, 0.05)' }
            ]
          }
        }
      },
      {
        name: '平均延迟(ms)',
        type: 'line',
        yAxisIndex: 1,
        data: avgRtt,
        smooth: true,
        itemStyle: { color: '#409eff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
              { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
            ]
          }
        }
      }
    ]
  }, true)
}

const pingHost = async (host) => {
  try {
    await api.pingNow(host.id, true) // 后台异步执行
    ElMessage.success(`已启动 ${host.name} 的Ping任务`)
    // 3秒后刷新数据
    setTimeout(() => {
      loadData()
    }, 3000)
  } catch (error) {
    ElMessage.error(`Ping失败: ${error.response?.data?.detail || '网络错误'}`)
  }
}

const pingAllHosts = async () => {
  pingAllLoading.value = true
  try {
    const result = await api.pingAll()
    ElMessage.success(`已启动 ${result.count} 个主机的Ping任务`)
    // 5秒后刷新数据（给所有主机足够的ping时间）
    setTimeout(() => {
      loadData()
      pingAllLoading.value = false
    }, 5000)
  } catch (error) {
    pingAllLoading.value = false
    ElMessage.error(`批量Ping失败: ${error.response?.data?.detail || '网络错误'}`)
  }
}

const copyAddress = async (address) => {
  try {
    await navigator.clipboard.writeText(address)
    ElMessage.success(`复制成功: ${address}`)
  } catch (error) {
    // 如果 clipboard API 不可用，使用备用方法
    const textarea = document.createElement('textarea')
    textarea.value = address
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      ElMessage.success(`复制成功: ${address}`)
    } catch (err) {
      ElMessage.error('复制失败，请手动复制')
    }
    document.body.removeChild(textarea)
  }
}

const viewChart = async (host) => {
  selectedHost.value = host
  chartVisible.value = true
  
  await nextTick()
  
  try {
    const records = await api.getRecords(host.id, 24)
    renderChart(records)
  } catch (error) {
    ElMessage.error('加载图表数据失败')
  }
}

const renderChart = (records) => {
  const instance = ensureHostChart()
  if (!instance) return

  if (!records || records.length === 0) {
    instance.clear()
    return
  }

  const times = records.map(r => new Date(r.created_at).toLocaleString()).reverse()
  const packetLoss = records.map(r => r.packet_loss).reverse()
  const avgRtt = records.map(r => r.avg_rtt || 0).reverse()
  
  instance.setOption({
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['丢包率(%)', '平均延迟(ms)']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '丢包率(%)',
        position: 'left'
      },
      {
        type: 'value',
        name: '延迟(ms)',
        position: 'right'
      }
    ],
    series: [
      {
        name: '丢包率(%)',
        type: 'line',
        data: packetLoss,
        smooth: true,
        itemStyle: { color: '#f56c6c' }
      },
      {
        name: '平均延迟(ms)',
        type: 'line',
        yAxisIndex: 1,
        data: avgRtt,
        smooth: true,
        itemStyle: { color: '#409eff' }
      }
    ]
  }, true)
}

const formatTime = (time) => {
  return new Date(time).toLocaleString()
}

watch(chartVisible, (val) => {
  if (val) {
    nextTick(() => {
      chartInstance?.resize()
    })
  }
})

onMounted(() => {
  loadData({ forceChartSettings: true })
  startRefreshTimer()
  bindResizeListener()
})

onActivated(() => {
  bindResizeListener()
  startRefreshTimer()

  nextTick(() => {
    overallChartInstance?.resize()
    chartInstance?.resize()
  })

  if (!lastLoadedAt.value || Date.now() - lastLoadedAt.value > 15000) {
    loadData()
  }
})

onDeactivated(() => {
  stopRefreshTimer()
  unbindResizeListener()
})

onBeforeUnmount(() => {
  stopRefreshTimer()
  unbindResizeListener()

  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  if (overallChartInstance) {
    overallChartInstance.dispose()
    overallChartInstance = null
  }
})
</script>

<style scoped>
:deep(.error-row) {
  background-color: #fef0f0 !important;
}

:deep(.error-row:hover > td) {
  background-color: #fde2e2 !important;
}
</style>
