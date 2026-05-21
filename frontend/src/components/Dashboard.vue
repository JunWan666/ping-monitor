<template>
  <div class="dashboard-page">
    <div
      v-if="isMobile"
      class="dashboard-mobile"
      :class="[`is-${mobileLayoutMode}`]"
      :style="dashboardMobileStyle"
    >
      <div class="dashboard-mobile__topline">
        <div class="dashboard-mobile__updated">
          <span>{{ lastLoadedText }}</span>
        </div>
        <el-button class="dashboard-mobile__refresh" text :loading="loading" @click="loadData">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>

      <el-card shadow="never" class="dashboard-mobile__section is-overview">
        <template #header>
          <div class="dashboard-mobile__section-header">
            <span>状态概览</span>
          </div>
        </template>
        <div class="dashboard-mobile__metrics">
          <div v-for="item in mobileOverviewCards" :key="item.label" class="dashboard-mobile__metric-card">
            <div class="dashboard-mobile__metric-label">{{ item.label }}</div>
            <div class="dashboard-mobile__metric-value" :class="`is-${item.tone}`">{{ item.value }}</div>
            <div class="dashboard-mobile__metric-delta" :class="`is-${item.tone}`">{{ item.delta }}</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="dashboard-mobile__section is-trend">
        <template #header>
          <div class="dashboard-mobile__section-header">
            <span>在线率趋势（近7天）</span>
            <el-select v-model="mobileTrendRange" size="small" class="dashboard-mobile__range-select" @change="loadData">
              <el-option label="7天" value="7d" />
              <el-option label="30天" value="30d" />
            </el-select>
          </div>
        </template>
        <div class="dashboard-mobile__trend-body">
          <div class="dashboard-mobile__trend-legend">
            <div v-for="item in mobileTrendLegend" :key="item.key" class="dashboard-mobile__trend-chip" :class="`is-${item.color}`">
              <span class="dashboard-mobile__trend-chip-label">
                <span class="dashboard-mobile__trend-dot"></span>
                {{ item.label }}
              </span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
          <div ref="overallChartDom" class="dashboard-mobile__chart"></div>
        </div>
      </el-card>

      <el-card shadow="never" class="dashboard-mobile__section is-actions">
        <template #header>
          <div class="dashboard-mobile__section-header">
            <span>快速操作</span>
          </div>
        </template>
        <div class="dashboard-mobile__quick-actions">
          <button v-for="action in quickActions" :key="action.key" type="button" class="dashboard-mobile__action" @click="action.action()">
            <el-icon class="dashboard-mobile__action-icon">
              <component :is="action.icon" />
            </el-icon>
            <span>{{ action.label }}</span>
          </button>
        </div>
      </el-card>
    </div>

    <!-- 统计卡片 -->
    <template v-else>
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
              <div style="font-size: 14px; color: #909399">告警/离线</div>
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
              placeholder="搜索主机名称、地址、IP 或地区" 
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
              <el-option label="离线" value="离线" />
            </el-select>
            <el-button type="success" size="small" @click="pingAllHosts" :loading="pingAllLoading">
              <el-icon><Promotion /></el-icon> 立即Ping全部
            </el-button>
            <el-button type="primary" size="small" @click="loadData" :loading="loading">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
            <el-button size="small" @click="goToHostManage">
              主机管理
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
        <el-table-column label="IP地址" width="180" align="center" header-align="center">
          <template #default="{ row }">
            <span
              v-if="row.resolved_ip"
              @click="copyAddress(row.resolved_ip)"
              style="cursor: pointer; color: #409eff; text-decoration: underline"
              :title="'点击复制: ' + row.resolved_ip"
            >
              {{ row.resolved_ip }}
            </span>
            <span v-else style="color: #909399">未解析</span>
            <el-icon
              @click="refreshIp(row.id, row.name)"
              style="margin-left: 5px; cursor: pointer; color: #67c23a"
              :title="'刷新IP地址'"
            >
              <Refresh />
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
            <el-tag :type="getStatusTagType(row.status)">{{ row.status }}</el-tag>
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
        <el-table-column label="地理位置" width="200" align="center" header-align="center">
          <template #default="{ row }">
            <div v-if="row.location_status === 'success'" style="display: flex; align-items: center; justify-content: center; gap: 5px">
              <el-icon style="color: #67c23a"><Location /></el-icon>
              <span>{{ formatLocation(row) }}</span>
            </div>
            <div v-else-if="row.location_status === 'failed'" style="display: flex; align-items: center; justify-content: center; gap: 5px">
              <el-icon style="color: #f56c6c"><WarningFilled /></el-icon>
              <span style="color: #909399">获取失败</span>
            </div>
            <div v-else style="display: flex; align-items: center; justify-content: center; gap: 5px">
              <el-icon style="color: #909399"><Loading /></el-icon>
              <span style="color: #909399">获取中</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="最后检查" min-width="180" align="center" header-align="center">
          <template #default="{ row }">
            <span v-if="row.last_check">{{ formatTime(row.last_check) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="290" align="center" header-align="center">
          <template #default="{ row }">
            <div style="display: flex; justify-content: center; gap: 6px; flex-wrap: wrap">
              <el-button type="primary" size="small" @click="viewChart(row)">图表</el-button>
              <el-button type="success" size="small" @click="pingHost(row)">Ping</el-button>
              <el-button type="warning" size="small" @click="refreshIp(row.id, row.name)">刷新IP</el-button>
              <el-button type="info" size="small" @click="refreshLocation(row.id, row.name)">刷新位置</el-button>
            </div>
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
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell, Download, Loading, Location, Plus, Promotion, Refresh, WarningFilled } from '@element-plus/icons-vue'
import api from '../api'
import { echarts } from '../lib/echarts'
import { useViewport } from '../lib/useViewport'

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
const mobileTrendRange = ref('7d')
const dashboard = reactive({
  total_hosts: 0,
  enabled_hosts: 0,
  recent_alerts: 0,
  host_status: []
})
const trendStats = reactive({
  avg_online_rate: 0,
  avg_rtt: 0,
  avg_packet_loss: 0,
  trend_data: []
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
const { isMobile, width: viewportWidth, height: viewportHeight } = useViewport()

const mobileLayoutMode = computed(() => {
  if (!isMobile.value) {
    return 'desktop'
  }

  if (viewportWidth.value <= 340 || viewportHeight.value <= 680) {
    return 'compact'
  }

  if (viewportHeight.value <= 780) {
    return 'balanced'
  }

  return 'spacious'
})

const isCompactMobile = computed(() => mobileLayoutMode.value === 'compact')
const mobileChartPointLimit = computed(() => (isCompactMobile.value ? 6 : 8))
const mobileChartHeight = computed(() => {
  if (!isMobile.value) {
    return 300
  }

  if (mobileLayoutMode.value === 'compact') {
    return 150
  }

  if (mobileLayoutMode.value === 'balanced') {
    return 180
  }

  return 200
})

const mobileQuickActionColumns = computed(() => {
  if (!isMobile.value) {
    return 4
  }

  return viewportWidth.value <= 340 ? 2 : 4
})

const mobileTrendLegendColumns = computed(() => {
  if (!isMobile.value) {
    return 3
  }

  return viewportWidth.value <= 340 ? 2 : 3
})

const dashboardMobileStyle = computed(() => ({
  '--dashboard-mobile-chart-height': `${mobileChartHeight.value}px`,
  '--dashboard-mobile-action-columns': String(mobileQuickActionColumns.value),
  '--dashboard-mobile-legend-columns': String(mobileTrendLegendColumns.value)
}))

const isHostOnline = (host) => {
  if (typeof host?.is_online === 'boolean') {
    return host.is_online
  }
  return host?.status === '正常' || host?.status === '异常'
}

const isHostProblem = (host) => host?.status === '异常' || host?.status === '离线'

const getStatusTagType = (status) => {
  if (status === '正常') return 'success'
  if (status === '异常') return 'warning'
  if (status === '离线') return 'danger'
  return 'info'
}

const onlineRate = computed(() => {
  if (dashboard.total_hosts === 0) return 0
  const online = dashboard.host_status.filter(isHostOnline).length
  return Math.round((online / dashboard.total_hosts) * 100)
})

const onlineHosts = computed(() => {
  return dashboard.host_status.filter(isHostOnline).length
})

const abnormalHosts = computed(() => {
  return dashboard.host_status.filter(isHostProblem).length
})

const getTrendDelta = (points = [], field, decimals = 1) => {
  if (!Array.isArray(points) || points.length < 2) {
    return { text: '暂无对比', tone: 'neutral' }
  }

  const first = Number(points[0]?.[field] ?? 0)
  const last = Number(points[points.length - 1]?.[field] ?? 0)
  const diff = last - first
  const sign = diff >= 0 ? '↑' : '↓'
  const absValue = Math.abs(diff).toFixed(decimals)

  return {
    text: `${sign} ${absValue}`,
    tone: diff > 0 ? 'danger' : diff < 0 ? 'success' : 'neutral'
  }
}

const mobileOverviewCards = computed(() => {
  const onlineDelta = getTrendDelta(trendStats.trend_data, 'online_rate', 1)
  const rttDelta = getTrendDelta(trendStats.trend_data, 'avg_rtt', 1)

  return [
    {
      label: '在线率',
      value: `${trendStats.avg_online_rate || 0}%`,
      delta: onlineDelta.text,
      tone: onlineDelta.tone
    },
    {
      label: '平均延迟',
      value: `${trendStats.avg_rtt || 0}ms`,
      delta: rttDelta.text,
      tone: rttDelta.tone
    },
    {
      label: '告警数量',
      value: `${dashboard.recent_alerts || 0}`,
      delta: dashboard.recent_alerts ? '↑ 近24h' : '暂无告警',
      tone: dashboard.recent_alerts ? 'danger' : 'neutral'
    }
  ]
})

const mobileTrendLegend = computed(() => [
  {
    key: 'online',
    label: '在线率',
    value: `${trendStats.avg_online_rate || 0}%`,
    color: 'green'
  },
  {
    key: 'loss',
    label: '丢包率',
    value: `${trendStats.avg_packet_loss || 0}%`,
    color: 'red'
  },
  {
    key: 'rtt',
    label: '延迟',
    value: `${trendStats.avg_rtt || 0}ms`,
    color: 'blue'
  }
])

const quickActions = computed(() => [
  {
    key: 'add-host',
    label: '添加主机',
    icon: Plus,
    action: () => window.dispatchEvent(new CustomEvent('ping-monitor:navigate', { detail: { menu: 'hosts', action: 'add' } }))
  },
  {
    key: 'ping',
    label: 'Ping 检测',
    icon: Promotion,
    action: () => window.dispatchEvent(new CustomEvent('ping-monitor:navigate', { detail: { menu: 'hosts' } }))
  },
  {
    key: 'alerts',
    label: '告警中心',
    icon: Bell,
    action: () => window.dispatchEvent(new CustomEvent('ping-monitor:navigate', { detail: { menu: 'alerts' } }))
  },
  {
    key: 'backup',
    label: '报告导出',
    icon: Download,
    action: () => window.dispatchEvent(new CustomEvent('ping-monitor:navigate', { detail: { menu: 'settings-backup' } }))
  }
])

const lastLoadedText = computed(() => {
  if (!lastLoadedAt.value) {
    return '暂无数据'
  }

  const date = new Date(lastLoadedAt.value)
  if (isMobile.value) {
    return `更新 ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
  }

  return `最后更新：${date.toLocaleString()}`
})

// 排序函数
const sortHosts = (hosts) => {
  if (!sortColumn.value) return hosts
  
  return [...hosts].sort((a, b) => {
    let aVal, bVal
    
    switch (sortColumn.value) {
      case 'status':
        // 离线 > 异常 > 正常 > 未知
        const statusOrder = { '离线': 4, '异常': 3, '正常': 2, '未知': 1 }
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
    result = result.filter(host => {
      const locationText = [host.country, host.province, host.city, host.isp]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return (
        host.name.toLowerCase().includes(keyword) ||
        host.address.toLowerCase().includes(keyword) ||
        String(host.resolved_ip || '').toLowerCase().includes(keyword) ||
        locationText.includes(keyword)
      )
    })
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
  if (row.status === '离线') {
    return 'error-row'
  }
  if (row.status === '异常') {
    return 'warning-row'
  }
  return ''
}

const loadData = async (options = {}) => {
  if (loading.value) {
    return
  }

  loading.value = true
  try {
    await ensureChartSettings(options.forceChartSettings === true)
    const chartRange = isMobile.value ? mobileTrendRange.value : '1h'

    const [dashboardData, databoardData] = await Promise.all([
      api.getDashboard(),
      api.getDataBoardStats(chartRange)
    ])

    Object.assign(dashboard, dashboardData)
    Object.assign(trendStats, databoardData || {})
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

  const mobileChart = isMobile.value
  const compactMobileChart = mobileChart && isCompactMobile.value
  const points = trendData.slice(-(mobileChart ? mobileChartPointLimit.value : chartPointLimit.value))
  const times = points.map(item => item.time)
  const packetLoss = points.map(item => item.avg_packet_loss)
  const avgRtt = points.map(item => item.avg_rtt)
  const onlineRates = points.map(item => item.online_rate)

  instance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: mobileChart ? 'line' : 'cross'
      }
    },
    legend: {
      show: !mobileChart,
      data: ['在线率(%)', '平均丢包率(%)', '平均延迟(ms)'],
      top: 0
    },
    grid: {
      left: mobileChart ? (compactMobileChart ? 4 : 8) : '3%',
      right: mobileChart ? (compactMobileChart ? 4 : 8) : '4%',
      bottom: mobileChart ? (compactMobileChart ? 14 : 22) : '10%',
      top: mobileChart ? (compactMobileChart ? 6 : 10) : '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: {
        rotate: 0,
        interval: mobileChart
          ? Math.max(0, Math.ceil(times.length / (compactMobileChart ? 3 : 4)) - 1)
          : 'auto',
        color: '#9ca3af',
        fontSize: mobileChart ? (compactMobileChart ? 9 : 10) : 12
      },
      axisTick: {
        show: !mobileChart
      },
      boundaryGap: false
    },
    yAxis: [
      {
        type: 'value',
        name: mobileChart ? '' : '百分比(%)',
        position: 'left',
        axisLabel: {
          color: '#9ca3af',
          fontSize: mobileChart ? (compactMobileChart ? 9 : 10) : 12
        },
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
        name: mobileChart ? '' : '延迟(ms)',
        position: 'right',
        axisLabel: {
          color: '#9ca3af',
          fontSize: mobileChart ? (compactMobileChart ? 9 : 10) : 12
        },
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
        showSymbol: !mobileChart,
        lineStyle: {
          width: mobileChart ? (compactMobileChart ? 1.2 : 2) : 2
        },
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
        showSymbol: !mobileChart,
        lineStyle: {
          width: mobileChart ? (compactMobileChart ? 1.2 : 1.4) : 2,
          type: mobileChart ? 'dashed' : 'solid'
        },
        itemStyle: { color: '#f56c6c' },
        areaStyle: mobileChart ? {
          opacity: 0.02
        } : {
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
        showSymbol: !mobileChart,
        lineStyle: {
          width: mobileChart ? (compactMobileChart ? 1.2 : 1.4) : 2,
          type: mobileChart ? 'dotted' : 'solid'
        },
        itemStyle: { color: '#409eff' },
        areaStyle: mobileChart ? {
          opacity: 0.02
        } : {
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
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success(`复制成功: ${address}`)
  }
}

const refreshIp = async (hostId, hostName) => {
  try {
    const response = await api.refreshHostIp(hostId)
    if (response.resolved_ip) {
      ElMessage.success(`${hostName} IP地址刷新成功: ${response.resolved_ip}`)
    } else {
      ElMessage.warning(`${hostName} IP地址解析失败`)
    }
    await loadData()
  } catch (error) {
    console.error('刷新IP地址失败:', error)
    ElMessage.error(`刷新IP地址失败: ${error.response?.data?.detail || error.message}`)
  }
}

const refreshLocation = async (hostId, hostName) => {
  try {
    const response = await api.refreshHostLocation(hostId)
    if (response.location?.status === 'success') {
      ElMessage.success(`${hostName} 地理位置刷新成功`)
    } else {
      ElMessage.warning(`${hostName} 地理位置刷新失败`)
    }
    await loadData()
  } catch (error) {
    console.error('刷新地理位置失败:', error)
    ElMessage.error(`${hostName} 地理位置刷新失败`)
  }
}

const goToHostManage = () => {
  window.dispatchEvent(new CustomEvent('ping-monitor:navigate', { detail: { menu: 'hosts' } }))
}

const formatLocation = (host) => {
  const parts = []
  if (host.country) parts.push(host.country)
  if (host.province) parts.push(host.province)
  if (host.city) parts.push(host.city)
  return parts.length > 0 ? parts.join(' ') : '未知'
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

watch([viewportHeight, isCompactMobile], () => {
  if (!isMobile.value) {
    return
  }

  nextTick(() => {
    overallChartInstance?.resize()
    chartInstance?.resize()

    if (trendStats.trend_data?.length) {
      renderOverallChart(trendStats.trend_data || [])
    }
  })
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
.dashboard-page {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.dashboard-mobile {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.dashboard-mobile.is-compact {
  gap: 6px;
}

.dashboard-mobile__topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 2px 0;
}

.dashboard-mobile.is-compact .dashboard-mobile__topline {
  min-height: 20px;
  padding: 0;
}

.dashboard-mobile__updated {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #6b7280;
}

.dashboard-mobile.is-compact .dashboard-mobile__updated {
  flex-wrap: nowrap;
  font-size: 11px;
  line-height: 1;
}

.dashboard-mobile__refresh {
  padding: 0;
  min-width: 32px;
  color: #3b82f6;
}

.dashboard-mobile__section {
  border-radius: 14px;
  flex: 0 0 auto;
}

.dashboard-mobile__section.is-trend {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.dashboard-mobile__section :deep(.el-card__header) {
  padding: 14px 14px 0;
  border-bottom: none;
}

.dashboard-mobile__section :deep(.el-card__body) {
  padding: 14px;
}

.dashboard-mobile__section.is-trend :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  padding-top: 8px;
}

.dashboard-mobile.is-compact .dashboard-mobile__section :deep(.el-card__header) {
  padding: 8px 10px 0;
}

.dashboard-mobile.is-compact .dashboard-mobile__section :deep(.el-card__body) {
  padding: 8px;
}

.dashboard-mobile.is-compact .dashboard-mobile__section.is-trend :deep(.el-card__body) {
  padding-top: 6px;
}

.dashboard-mobile.is-compact .dashboard-mobile__section.is-overview :deep(.el-card__header),
.dashboard-mobile.is-compact .dashboard-mobile__section.is-actions :deep(.el-card__header) {
  display: none;
}

.dashboard-mobile.is-compact .dashboard-mobile__section.is-overview :deep(.el-card__body),
.dashboard-mobile.is-compact .dashboard-mobile__section.is-actions :deep(.el-card__body) {
  padding: 6px;
}

.dashboard-mobile__trend-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 0;
}

.dashboard-mobile.is-compact .dashboard-mobile__trend-body {
  gap: 5px;
}

.dashboard-mobile__trend-legend {
  display: grid;
  grid-template-columns: repeat(var(--dashboard-mobile-legend-columns, 3), minmax(0, 1fr));
  gap: 6px;
}

.dashboard-mobile.is-balanced .dashboard-mobile__trend-legend,
.dashboard-mobile.is-spacious .dashboard-mobile__trend-legend {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.dashboard-mobile__trend-chip {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border: 1px solid #edf2f7;
  border-radius: 12px;
  background: #fff;
  font-size: 11px;
  color: #6b7280;
}

.dashboard-mobile__trend-chip strong {
  font-size: 14px;
  line-height: 1.1;
  color: #111827;
}

.dashboard-mobile.is-compact .dashboard-mobile__trend-chip {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  padding: 6px 8px;
}

.dashboard-mobile.is-compact .dashboard-mobile__trend-chip strong {
  font-size: 11px;
}

.dashboard-mobile__trend-chip-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dashboard-mobile.is-compact .dashboard-mobile__trend-chip-label {
  gap: 4px;
  min-width: 0;
  font-size: 10px;
}

.dashboard-mobile__trend-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: currentColor;
  flex: 0 0 auto;
}

.dashboard-mobile__trend-chip.is-green {
  color: #67c23a;
}

.dashboard-mobile__trend-chip.is-red {
  color: #f56c6c;
}

.dashboard-mobile__trend-chip.is-blue {
  color: #409eff;
}

.dashboard-mobile__section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.dashboard-mobile__range-select {
  width: 84px;
}

.dashboard-mobile.is-compact .dashboard-mobile__range-select {
  width: 74px;
}

.dashboard-mobile__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.dashboard-mobile.is-compact .dashboard-mobile__metrics {
  gap: 5px;
}

.dashboard-mobile__metric-card {
  padding: 12px 8px;
  border: 1px solid #edf2f7;
  border-radius: 12px;
  background: #fff;
  text-align: center;
}

.dashboard-mobile.is-compact .dashboard-mobile__metric-card {
  padding: 6px 4px;
  border-radius: 10px;
}

.dashboard-mobile__metric-label {
  font-size: 12px;
  color: #6b7280;
}

.dashboard-mobile__metric-value {
  margin-top: 8px;
  font-size: 20px;
  font-weight: 700;
  color: #2563eb;
}

.dashboard-mobile.is-compact .dashboard-mobile__metric-value {
  margin-top: 3px;
  font-size: 16px;
  line-height: 1.1;
}

.dashboard-mobile__metric-value.is-green,
.dashboard-mobile__metric-delta.is-success {
  color: #67c23a;
}

.dashboard-mobile__metric-value.is-blue {
  color: #409eff;
}

.dashboard-mobile__metric-value.is-red,
.dashboard-mobile__metric-delta.is-danger {
  color: #f56c6c;
}

.dashboard-mobile__metric-delta {
  margin-top: 6px;
  font-size: 11px;
}

.dashboard-mobile.is-compact .dashboard-mobile__metric-delta {
  display: none;
}

.dashboard-mobile__chart {
  width: 100%;
  flex: 1 1 auto;
  min-height: var(--dashboard-mobile-chart-height, 150px);
  height: auto;
}

.dashboard-mobile.is-compact .dashboard-mobile__chart {
  min-height: var(--dashboard-mobile-chart-height, 150px);
}

.dashboard-mobile__quick-actions {
  display: grid;
  grid-template-columns: repeat(var(--dashboard-mobile-action-columns, 4), minmax(0, 1fr));
  gap: 10px;
}

.dashboard-mobile.is-balanced .dashboard-mobile__quick-actions,
.dashboard-mobile.is-spacious .dashboard-mobile__quick-actions {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-mobile.is-compact .dashboard-mobile__quick-actions {
  gap: 6px;
}

.dashboard-mobile__action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 10px 6px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  color: #111827;
}

.dashboard-mobile.is-compact .dashboard-mobile__action {
  gap: 2px;
  min-height: 42px;
  padding: 4px 2px;
  border-radius: 10px;
}

.dashboard-mobile__action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 20px;
}

.dashboard-mobile.is-compact .dashboard-mobile__action-icon {
  width: 22px;
  height: 22px;
  font-size: 14px;
}

.dashboard-mobile__action span {
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 500;
}

.dashboard-mobile.is-compact .dashboard-mobile__action span {
  font-size: 11px;
  line-height: 1.1;
}

:deep(.error-row) {
  background-color: #fef0f0 !important;
}

:deep(.error-row:hover > td) {
  background-color: #fde2e2 !important;
}

:deep(.warning-row) {
  background-color: #fff8eb !important;
}

:deep(.warning-row:hover > td) {
  background-color: #fff1d6 !important;
}
</style>
