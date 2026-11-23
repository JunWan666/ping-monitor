<template>
  <div ref="pageRoot" class="dashboard-page viewport-page">
    <section class="dashboard-summary" aria-label="统计概览">
      <div class="dashboard-summary__heading">
        <h3>统计概览</h3>
        <div class="dashboard-row-actions">
          <el-button :icon="Promotion" :loading="pingAllLoading" :disabled="!dashboard.enabled_hosts" size="small" @click="pingAllHosts">Ping 全部</el-button>
          <el-button :icon="Refresh" :loading="loading" size="small" @click="load">刷新</el-button>
        </div>
      </div>
      <div class="dashboard-summary__grid">
        <button type="button" class="dashboard-metric is-host" aria-label="在线主机，筛选当前可达主机" @click="showHosts('online')">
          <span class="dashboard-metric__label"><el-icon><Monitor /></el-icon>在线主机</span><strong>{{ hostLoaded ? onlineHosts : '—' }}<small v-if="hostLoaded"> / {{ dashboard.enabled_hosts }}</small></strong>
          <el-icon class="dashboard-metric__arrow" aria-hidden="true"><ArrowRight /></el-icon>
        </button>
        <button type="button" class="dashboard-metric is-host" aria-label="当前在线率，在线主机占已启用主机的比例，查看启用主机" @click="showHosts('enabled')">
          <span class="dashboard-metric__label"><el-icon><DataLine /></el-icon>当前在线率</span>
          <strong>{{ currentOnlineRate }}</strong>
          <el-icon class="dashboard-metric__arrow" aria-hidden="true"><ArrowRight /></el-icon>
        </button>
        <button type="button" class="dashboard-metric is-problem" @click="showHosts('problem')">
          <span class="dashboard-metric__label"><el-icon><WarningFilled /></el-icon>主机异常 / 离线</span><strong :class="{ 'is-danger': hostProblems }">{{ hostLoaded ? hostProblems : '—' }}</strong>
          <el-icon class="dashboard-metric__arrow" aria-hidden="true"><ArrowRight /></el-icon>
        </button>
        <button type="button" class="dashboard-metric is-domain" @click="section = 'domains'">
          <span class="dashboard-metric__label"><el-icon><Connection /></el-icon>域名需处理</span><strong :class="{ 'is-danger': domainCounts.issues }">{{ domainsAvailable ? domainCounts.issues : '—' }}</strong>
          <el-icon class="dashboard-metric__arrow" aria-hidden="true"><ArrowRight /></el-icon>
        </button>
        <button type="button" class="dashboard-metric is-alert" @click="navigate('alerts')">
          <span class="dashboard-metric__label"><el-icon><Bell /></el-icon>近 1 小时告警</span><strong>{{ hostLoaded ? dashboard.recent_alerts : '—' }}</strong>
          <el-icon class="dashboard-metric__arrow" aria-hidden="true"><ArrowRight /></el-icon>
        </button>
      </div>
      <div v-if="problemHosts.length" class="dashboard-incident">
        <strong>受影响主机</strong>
        <button v-for="host in problemHosts.slice(0, 2)" :key="host.id" type="button" @click="showHosts('problem', host.name)">{{ host.name }}</button>
        <button v-if="problemHosts.length > 2" type="button" @click="showHosts('problem')">另有 {{ problemHosts.length - 2 }} 台</button>
        <span v-if="latestProblemAlert">最近告警 · {{ latestProblemAlert.host_name }} · {{ formatTime(latestProblemAlert.created_at) }}</span>
      </div>
    </section>

    <div class="dashboard-workspace">
      <section class="dashboard-trend-card" aria-label="监控数据趋势">
        <div class="dashboard-trend-heading">
          <h3>监控数据趋势</h3>
          <span>{{ trendRange === '1h' ? '近 1 小时' : '近 24 小时' }}</span>
        </div>
        <MonitorTrend :points="visibleTrend" :loading="loading && !visibleTrend.length" :empty-text="trendError || '暂无监控记录'" compact />
      </section>
      <el-card shadow="never" class="viewport-list-card dashboard-list" :class="{ 'dashboard-list--domains': section === 'domains' }">
      <template #header>
        <div class="dashboard-list__toolbar">
          <el-radio-group v-model="section" size="small" aria-label="监控列表">
            <el-radio-button value="hosts">主机列表</el-radio-button>
            <el-radio-button value="domains">域名监控</el-radio-button>
          </el-radio-group>
          <div class="dashboard-list__actions">
            <el-button size="small" @click="navigate('databoard')">数据看板</el-button>
            <el-button size="small" type="primary" plain @click="navigate(section === 'hosts' ? 'hosts' : 'domains')">{{ section === 'hosts' ? '主机管理' : '域名管理' }}</el-button>
          </div>
        </div>
      </template>

      <div v-if="section === 'hosts'" class="dashboard-list__filters">
        <el-input v-model="search" size="small" clearable placeholder="搜索主机、地址或 IP" aria-label="搜索主机" />
        <el-radio-group v-model="hostFilter" size="small" class="dashboard-status-filters" aria-label="筛选主机状态">
          <el-radio-button v-if="hostFilter === 'online'" value="online">
            <span class="dashboard-status-tab__label">在线</span>
            <small class="dashboard-status-tab__count" :data-tone="hostStatusCounts.online ? 'normal' : 'empty'">{{ hostStatusCounts.online }}</small>
          </el-radio-button>
          <el-radio-button v-if="hostFilter === 'enabled'" value="enabled">
            <span class="dashboard-status-tab__label">已启用</span>
            <small class="dashboard-status-tab__count" :data-tone="hostStatusCounts.enabled ? 'total' : 'empty'">{{ hostStatusCounts.enabled }}</small>
          </el-radio-button>
          <el-radio-button v-for="item in statusOptions" :key="item.value" :value="item.value">
            <span class="dashboard-status-tab__label">{{ item.label }}</span>
            <small class="dashboard-status-tab__count" :data-tone="hostStatusCounts[item.value] ? item.tone : 'empty'">{{ hostStatusCounts[item.value] }}</small>
          </el-radio-button>
        </el-radio-group>
      </div>
      <div v-else-if="domainsAvailable" class="dashboard-list__filters dashboard-domain-summary">
        <span>正常 <b>{{ domainCounts.normal }}</b></span><span>待确认 <b>{{ domainCounts.pending }}</b></span>
        <span>需处理 <b>{{ domainCounts.issues }}</b></span><span>已暂停 <b>{{ domainCounts.paused }}</b></span>
      </div>
      <div v-else class="dashboard-list__filters dashboard-domain-summary dashboard-domain-summary--empty" aria-hidden="true"></div>

      <div v-if="!isMobile" class="viewport-table-area" data-page-rows-box>
        <el-table v-if="section === 'hosts'" :data="pagedRows" height="100%" size="small" :empty-text="hostError || '没有匹配的主机'" @sort-change="handleHostSortChange">
          <el-table-column label="序号" width="48" align="center"><template #default="{ $index }">{{ numberAt($index) }}</template></el-table-column>
          <el-table-column label="监控目标" min-width="170" show-overflow-tooltip>
            <template #default="{ row }"><div class="table-identity"><strong>{{ row.name }}</strong><small>{{ row.address }}</small></div></template>
          </el-table-column>
          <el-table-column prop="status" label="状态" min-width="76" align="center" sortable="custom" :sort-orders="['ascending', 'descending']"><template #default="{ row }"><el-tag size="small" effect="plain" :type="hostState(row).type">{{ hostState(row).label }}</el-tag></template></el-table-column>
          <el-table-column prop="avg_rtt" label="平均延迟" min-width="88" align="center" sortable="custom" :sort-orders="['ascending', 'descending']"><template #default="{ row }">{{ hostMetric(row, 'avg_rtt', ' ms') }}</template></el-table-column>
          <el-table-column prop="packet_loss" label="丢包率" min-width="76" align="center" sortable="custom" :sort-orders="['ascending', 'descending']"><template #default="{ row }">{{ hostMetric(row, 'packet_loss', '%') }}</template></el-table-column>
          <el-table-column v-if="width >= 1000" label="最近检查" min-width="148" show-overflow-tooltip><template #default="{ row }">{{ formatTime(row.last_check) }}</template></el-table-column>
          <el-table-column label="操作" width="112" align="center">
            <template #default="{ row }"><div class="dashboard-row-actions"><el-button size="small" link type="primary" @click="actions.openPing(row)">Ping</el-button><el-button size="small" link type="primary" @click="actions.openHistory(row)">详情</el-button></div></template>
          </el-table-column>
        </el-table>
        <el-table v-else :data="pagedRows" height="100%" size="small" :empty-text="domainError || '还没有配置监控域名'">
          <el-table-column label="序号" width="48" align="center"><template #default="{ $index }">{{ numberAt($index) }}</template></el-table-column>
          <el-table-column label="域名" min-width="130" show-overflow-tooltip><template #default="{ row }"><strong>{{ row.name }}</strong></template></el-table-column>
          <el-table-column label="状态" width="100" align="center"><template #default="{ row }"><el-tag size="small" effect="plain" :type="domainState(row).type">{{ domainState(row).label }}</el-tag></template></el-table-column>
          <el-table-column label="到期日" width="106" show-overflow-tooltip><template #default="{ row }">{{ expiryDate(row) }}</template></el-table-column>
          <el-table-column label="最近检查" min-width="115" show-overflow-tooltip><template #default="{ row }">{{ formatTime(row.last_checked_at) }}</template></el-table-column>
          <el-table-column label="操作" width="62" align="center"><template #default="{ row }"><el-button size="small" link type="primary" @click="navigate('domains', row.id)">详情</el-button></template></el-table-column>
        </el-table>
      </div>

      <div v-else class="dashboard-mobile-rows" data-page-rows-box>
        <article v-for="(row, index) in pagedRows" :key="row.id" class="dashboard-mobile-row">
          <div class="dashboard-mobile-row__head">
            <span class="list-number">{{ numberAt(index) }}</span>
            <strong>{{ row.name }}</strong>
            <el-tag size="small" effect="plain" :type="rowState(row).type">{{ rowState(row).label }}</el-tag>
          </div>
          <template v-if="section === 'hosts'">
            <div class="dashboard-mobile-row__address">{{ row.address }}</div>
            <div class="dashboard-mobile-row__bottom"><span>延迟 {{ hostMetric(row, 'avg_rtt', ' ms') }} · 丢包 {{ hostMetric(row, 'packet_loss', '%') }}</span><div class="dashboard-row-actions"><el-button size="small" link type="primary" @click="actions.openPing(row)">Ping</el-button><el-button size="small" link type="primary" @click="actions.openHistory(row)">详情</el-button></div></div>
          </template>
          <template v-else>
            <div class="dashboard-mobile-row__address">到期 {{ expiryDate(row) }}</div>
            <div class="dashboard-mobile-row__bottom"><span>检查 {{ formatTime(row.last_checked_at) }}</span><el-button size="small" link type="primary" @click="navigate('domains', row.id)">详情</el-button></div>
          </template>
        </article>
        <el-empty v-if="!loading && !pagedRows.length" :description="section === 'hosts' ? (hostError || '没有匹配的主机') : (domainError || '还没有配置监控域名')" :image-size="28" />
      </div>
      <div class="viewport-table-pager dashboard-pager">
        <span>共 {{ activeRows.length }} {{ section === 'hosts' ? '台' : '个' }}</span>
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="activeRows.length" layout="prev, pager, next" :pager-count="5" small />
      </div>
      </el-card>
    </div>
    <DashboardHostActions ref="actions" @ping-complete="load" />
  </div>
</template>

<script setup>
import { computed, onActivated, onDeactivated, reactive, ref, watch } from 'vue'
import { ArrowRight, Bell, Connection, DataLine, Monitor, Promotion, Refresh, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import DashboardHostActions from './DashboardHostActions.vue'
import MonitorTrend from './MonitorTrend.vue'
import { useViewport } from '../lib/useViewport'
import { usePageRows } from '../lib/usePageRows'
import { domainState, expiryDate } from '../lib/domainPresentation'

const { isMobile, width } = useViewport()
const { pageRoot, pageSize } = usePageRows({ rowHeight: 40, mobileRowHeight: () => window.innerWidth <= 340 ? 64 : 72, maxRows: 5 })
const actions = ref(null)
const loading = ref(false)
const pingAllLoading = ref(false)
const recentHostAlerts = ref([])
const dashboard = reactive({ enabled_hosts: 0, recent_alerts: 0, host_status: [] })
const hostLoaded = ref(false)
const hostError = ref('')
const domainsLoaded = ref(false)
const domainError = ref('')
const domains = ref([])
const section = ref('hosts')
const search = ref('')
const hostFilter = ref('')
const page = ref(1)
const statusOptions = [
  { value: '', label: '全部', tone: 'total' },
  { value: 'problem', label: '异常 / 离线', tone: 'problem' },
  { value: '正常', label: '正常', tone: 'normal' },
  { value: '未知', label: '待检查', tone: 'pending' },
  { value: 'paused', label: '已停用', tone: 'paused' }
]
const hostSort = ref({ prop: '', order: '' })
const trend = ref([])
const trendRange = ref('1h')
const trendError = ref('')
const chartPointLimit = ref(5)
const visibleTrend = computed(() => {
  const maxPoints = chartPointLimit.value
  if (trendRange.value !== '1d' || trend.value.length <= maxPoints) return trend.value.slice(-maxPoints)
  const step = (trend.value.length - 1) / (maxPoints - 1)
  return Array.from({ length: maxPoints }, (_, index) => trend.value[Math.round(index * step)])
})
let timer
let pingRefreshTimer

const hostState = (host) => {
  if (!host.enabled) return { label: '已停用', type: 'info' }
  if (host.status === '正常') return { label: '正常', type: 'success' }
  if (host.status === '异常') return { label: '异常', type: 'warning' }
  if (host.status === '离线') return { label: '离线', type: 'danger' }
  return { label: '待检查', type: 'info' }
}
const isProblem = (host) => host.enabled && ['异常', '离线'].includes(host.status)
const isOnline = host => host.enabled && (host.is_online ?? ['正常', '异常'].includes(host.status))
const onlineHosts = computed(() => dashboard.host_status.filter(isOnline).length)
const currentOnlineRate = computed(() => {
  if (!hostLoaded.value || !dashboard.enabled_hosts) return '—'
  return `${Number((100 * onlineHosts.value / dashboard.enabled_hosts).toFixed(1))}%`
})
const problemHosts = computed(() => dashboard.host_status.filter(isProblem))
const hostProblems = computed(() => problemHosts.value.length)
const latestProblemAlert = computed(() => {
  const ids = new Set(problemHosts.value.map(host => host.id))
  return recentHostAlerts.value.find(alert => ids.has(alert.host_id) && ['unreachable', 'packet_loss'].includes(alert.alert_type))
})
const domainsAvailable = computed(() => domainsLoaded.value && !domainError.value)
const domainCounts = computed(() => {
  const counts = { enabled: 0, normal: 0, issues: 0, pending: 0, paused: 0 }
  for (const domain of domains.value) {
    counts[domainState(domain).category]++
    if (domain.enabled) counts.enabled++
  }
  return counts
})

const searchedHosts = computed(() => {
  const term = search.value.trim().toLowerCase()
  return dashboard.host_status.filter(host => !term || [host.name, host.address, host.resolved_ip].some(value => value?.toLowerCase().includes(term)))
})
const hostStatusCounts = computed(() => {
  const counts = { '': searchedHosts.value.length, problem: 0, '正常': 0, '未知': 0, paused: 0, online: 0, enabled: 0 }
  for (const host of searchedHosts.value) {
    if (!host.enabled) counts.paused++
    else {
      counts.enabled++
      if (isOnline(host)) counts.online++
      if (host.status === '正常') counts['正常']++
      if (hostState(host).label === '待检查') counts['未知']++
      if (isProblem(host)) counts.problem++
    }
  }
  return counts
})
const filteredHosts = computed(() => {
  const rows = searchedHosts.value.filter(host => {
    if (hostFilter.value === 'problem') return isProblem(host)
    if (hostFilter.value === 'online') return isOnline(host)
    if (hostFilter.value === 'enabled') return host.enabled
    if (hostFilter.value === 'paused') return !host.enabled
    return !hostFilter.value || (host.enabled && (hostFilter.value === '未知' ? hostState(host).label === '待检查' : host.status === hostFilter.value))
  })
  const { prop, order } = hostSort.value
  if (prop && order) {
    const direction = order === 'ascending' ? 1 : -1
    const stateRank = host => ({ '离线': 0, '异常': 1, '正常': 2, '待检查': 3, '已停用': 4 }[hostState(host).label] ?? 5)
    const metricValue = host => {
      if (!host.enabled) return null
      if (prop === 'avg_rtt' && (host.status === '离线' || Number(host.packet_loss) >= 100)) return Number.POSITIVE_INFINITY
      const value = Number(host[prop])
      return Number.isFinite(value) ? value : null
    }
    rows.sort((a, b) => {
      let compared = 0
      if (prop === 'status') compared = (stateRank(a) - stateRank(b)) * direction
      else {
        const left = metricValue(a)
        const right = metricValue(b)
        if (left == null || right == null) compared = left == null ? (right == null ? 0 : 1) : -1
        else compared = (left < right ? -1 : left > right ? 1 : 0) * direction
      }
      return compared || a.id - b.id
    })
    return rows
  }
  return rows.sort((a, b) => Number(isProblem(b)) - Number(isProblem(a)) || a.id - b.id)
})
const domainPriority = { issues: 0, pending: 1, normal: 2, paused: 3 }
const sortedDomains = computed(() => domainsAvailable.value
  ? [...domains.value].sort((a, b) => domainPriority[domainState(a).category] - domainPriority[domainState(b).category] || a.name.localeCompare(b.name))
  : [])
const activeRows = computed(() => section.value === 'hosts' ? filteredHosts.value : sortedDomains.value)
const pagedRows = computed(() => activeRows.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
const numberAt = index => (page.value - 1) * pageSize.value + index + 1
const rowState = row => section.value === 'hosts' ? hostState(row) : domainState(row)
const withUnit = (value, unit) => value == null ? '—' : `${value}${unit}`
const hostMetric = (host, key, unit) => {
  if (!host?.enabled) return '—'
  if (key === 'avg_rtt' && (host.status === '离线' || Number(host.packet_loss) >= 100)) return '超时'
  if (host[key] == null) return '尚未检测'
  return `${host[key]}${unit}`
}
const formatTime = value => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'

const showHosts = (filter, term = '') => {
  section.value = 'hosts'
  hostFilter.value = filter
  search.value = term
}
const handleHostSortChange = ({ prop, order }) => {
  hostSort.value = order ? { prop, order } : { prop: '', order: '' }
  page.value = 1
}
const navigate = (menu, domainId) => window.dispatchEvent(new CustomEvent('ping-monitor:navigate', { detail: { menu, domainId } }))
watch([section, pageSize, search, hostFilter], () => { page.value = 1 })
watch(() => activeRows.value.length, total => { page.value = Math.min(page.value, Math.max(1, Math.ceil(total / pageSize.value))) })

const loadTrend = async () => {
  try {
    let range = '1h'
    let result = await api.getDataBoardStats(range)
    if (!result.trend_data?.length) {
      range = '1d'
      result = await api.getDataBoardStats(range)
    }
    trendRange.value = range
    trend.value = result.trend_data || []
    trendError.value = ''
  } catch {
    trend.value = []
    trendError.value = '趋势加载失败，请刷新重试'
  }
}

const load = async () => {
  if (loading.value) return
  loading.value = true
  const [hosts, registration] = await Promise.allSettled([api.getDashboard(), api.getDomains(), loadTrend()])
  if (hosts.status === 'fulfilled') {
    Object.assign(dashboard, hosts.value)
    hostLoaded.value = true
    hostError.value = ''
    if (problemHosts.value.length) {
      try {
        const result = await api.getAlerts(24, 1, 50, null, null, null, 'host')
        recentHostAlerts.value = result.items || []
      } catch {
        recentHostAlerts.value = []
      }
    } else {
      recentHostAlerts.value = []
    }
  } else {
    hostError.value = '主机状态加载失败，请刷新重试'
  }
  if (registration.status === 'fulfilled') {
    domains.value = registration.value
    domainsLoaded.value = true
    domainError.value = ''
  } else {
    domainError.value = registration.reason?.response?.status === 403 ? '仅管理员可查看域名监控' : '域名状态加载失败，请刷新重试'
  }
  loading.value = false
}

const pingAllHosts = async () => {
  pingAllLoading.value = true
  try {
    const result = await api.pingAll()
    ElMessage.success(`已启动 ${result.count} 台主机的 Ping 任务`)
    window.clearTimeout(pingRefreshTimer)
    pingRefreshTimer = window.setTimeout(load, 5000)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '批量 Ping 启动失败')
  } finally {
    pingAllLoading.value = false
  }
}

onActivated(() => {
  api.getConfig().then(config => {
    if (Number.isInteger(config.dashboard_chart_points)) {
      chartPointLimit.value = Math.max(3, Math.min(5, config.dashboard_chart_points))
    }
  }).catch(() => {})
  load()
  timer = window.setInterval(load, 30000)
})
onDeactivated(() => {
  window.clearInterval(timer)
  window.clearTimeout(pingRefreshTimer)
})
</script>

<style scoped>
.dashboard-page { display: flex; flex-direction: column; gap: 10px; height: 100%; min-height: 0; }
.dashboard-summary { flex: 0 0 auto; }
.dashboard-summary__heading, .dashboard-list__toolbar, .dashboard-mobile-row__head, .dashboard-mobile-row__bottom { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.dashboard-summary__heading { margin-bottom: 7px; }
.dashboard-summary__heading h3 { color: #233248; font-size: 16px; }
.dashboard-summary__grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
.dashboard-metric { position: relative; display: grid; align-content: start; gap: 4px; min-width: 0; padding: 12px 33px 11px 13px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: #475569; font: inherit; font-size: 13px; text-align: left; cursor: pointer; }
.dashboard-metric strong { font-size: 28px; line-height: 1.12; color: #223451; font-variant-numeric: tabular-nums; }
.dashboard-metric small { font-size: 14px; font-weight: 500; color: #64748b; }
.dashboard-metric strong.is-danger { color: #c13543; }
.dashboard-incident { display: flex; flex-wrap: wrap; align-items: center; column-gap: 12px; row-gap: 3px; min-width: 0; margin-top: 7px; padding: 6px 9px; border-inline-start: 2px solid #ba4e43; background: #fff5f2; color: #683d38; font-size: 12px; }
.dashboard-incident button { max-width: min(180px, 100%); padding: 0; overflow: hidden; border: 0; background: none; color: var(--brand); font: inherit; text-overflow: ellipsis; white-space: nowrap; }
.dashboard-incident button:hover { text-decoration: underline; }
.dashboard-incident span { min-width: 0; overflow-wrap: anywhere; }
.dashboard-list { min-width: 0; }
.dashboard-list .viewport-table-area { --table-row-height: 40px; }
.dashboard-list__toolbar { flex-wrap: wrap; }
.dashboard-list__actions, .dashboard-row-actions { display: flex; align-items: center; gap: 9px; }
.dashboard-list__actions :deep(.el-button + .el-button), .dashboard-row-actions :deep(.el-button + .el-button) { margin-left: 0; }
.dashboard-list__filters { display: flex; flex: 0 0 30px; align-items: center; gap: 8px; min-height: 30px; margin-bottom: 6px; box-sizing: border-box; }
.dashboard-list__filters :deep(.el-input) { width: min(260px, 100%); }

.dashboard-domain-summary { flex-wrap: wrap; gap: 6px 15px; color: #53657d; font-size: 12px; }
.dashboard-domain-summary b { color: #233248; }
.dashboard-domain-summary--empty { visibility: hidden; }
.dashboard-row-actions { justify-content: center; flex-shrink: 0; }
.dashboard-pager { justify-content: space-between; align-items: center; gap: 4px; color: #64748b; font-size: 12px; }
.dashboard-mobile-rows { display: flex; flex: 1 1 0; flex-direction: column; min-height: 0; overflow: hidden; }
.dashboard-mobile-row { flex: 0 0 72px; box-sizing: border-box; min-width: 0; padding: 4px 2px; border-bottom: 1px solid #eef1f5; font-size: 12px; }
.dashboard-mobile-row__head { justify-content: flex-start; }
.dashboard-mobile-row__head strong, .dashboard-mobile-row__address, .dashboard-mobile-row__bottom > span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dashboard-mobile-row__head strong { flex: 1; }
.dashboard-mobile-row__address, .dashboard-mobile-row__bottom { color: #526278; line-height: 18px; }
.dashboard-mobile-row__bottom { min-height: 22px; }
@media (max-width: 768px) {
  .dashboard-page { gap: 6px; }
  .dashboard-metric { font-size: 11px; }
  .dashboard-metric small { font-size: 10px; }
  .dashboard-list__actions { gap: 5px; }
  .dashboard-list__actions :deep(.el-button) { padding-inline: 6px; }
  .dashboard-list :deep(.el-card__header), .dashboard-list :deep(.el-card__body) { padding: 6px 8px; }
}
@media (max-width: 768px) and (max-height: 430px) and (orientation: landscape) {
  .dashboard-page { gap: 4px; }
  .dashboard-summary__heading { margin-bottom: 3px; }
  .dashboard-metric { display: flex; align-items: center; justify-content: space-between; padding-block: 3px; }
  .dashboard-list :deep(.el-card__header), .dashboard-list :deep(.el-card__body) { padding-block: 3px; }
  .dashboard-list__filters { margin-bottom: 2px; }
  .dashboard-pager { padding-top: 1px; }
}

.dashboard-workspace { display: grid; flex: 1 1 0; min-height: 0; grid-template-rows: minmax(0, 1fr) min(calc(100% - 162px), 367px); gap: 10px; }
.dashboard-trend-card { display: flex; flex-direction: column; min-height: 0; min-width: 0; border: 1px solid #dce5f0; border-radius: 9px; background: #fff; padding: 9px 12px 5px; }
.dashboard-trend-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
.dashboard-trend-heading h3 { font-size: 15px; color: #233248; }
.dashboard-trend-heading span { font-size: 11px; color: #526278; }
.dashboard-metric:hover { border-color: #a6c5fc; background: #f8fbff; }
.dashboard-metric:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
.dashboard-metric__label { display: flex; align-items: center; gap: 6px; font-weight: 600; }
.dashboard-metric__label .el-icon { flex: 0 0 auto; font-size: 15px; color: var(--brand); }
.dashboard-metric.is-problem .dashboard-metric__label .el-icon { color: #b64637; }
.dashboard-metric.is-alert .dashboard-metric__label .el-icon { color: #a26713; }
.dashboard-metric__arrow { position: absolute; inset: 12px 11px auto auto; color: #60758d; font-size: 14px; }
.dashboard-metric:hover .dashboard-metric__arrow, .dashboard-metric:focus-visible .dashboard-metric__arrow { color: var(--brand); }
.dashboard-list__filters { flex-wrap: wrap; }
.dashboard-status-filters { flex-shrink: 0; }
.dashboard-status-filters :deep(.el-radio-button) {
  --el-radio-button-checked-bg-color: #1d4ed8;
  --el-radio-button-checked-border-color: #1d4ed8;
}
.dashboard-status-filters :deep(.el-radio-button__inner) { display: inline-flex; align-items: baseline; justify-content: center; gap: 4px; }
.dashboard-status-tab__label { line-height: 1; }
.dashboard-status-tab__count {
  display: inline-block;
  color: var(--count-color, #64748b);
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.dashboard-status-tab__count[data-tone="total"] { --count-color: var(--brand); --count-active-color: #eff6ff; }
.dashboard-status-tab__count[data-tone="problem"] { --count-color: #b91c1c; --count-active-color: #fee2e2; }
.dashboard-status-tab__count[data-tone="normal"] { --count-color: #15803d; --count-active-color: #dcfce7; }
.dashboard-status-tab__count[data-tone="pending"] { --count-color: #92400e; --count-active-color: #fef3c7; }
.dashboard-status-tab__count[data-tone="paused"] { --count-color: #475569; --count-active-color: #e2e8f0; }
.dashboard-status-filters :deep(.is-active .dashboard-status-tab__count) { color: var(--count-active-color, #dbeafe); }
.dashboard-list :deep(.el-table th.is-sortable .cell) { cursor: pointer; }
@media (min-width: 769px) and (max-width: 900px) {
  .dashboard-trend-card { padding: 5px 8px 2px; }
  .dashboard-list__filters :deep(.el-input) { width: 100%; }
  .dashboard-status-filters :deep(.el-radio-button__inner) { padding-inline: 6px; font-size: 11px; }
}
@media (min-width: 769px) and (max-height: 600px) { .dashboard-workspace { grid-template-rows: minmax(0, 1fr) minmax(0, 57%); } }
@media (max-width: 768px) {
  .dashboard-workspace { grid-template-rows: clamp(118px, 24dvh, 195px) minmax(0, 1fr); gap: 6px; }
  .dashboard-trend-card { padding: 5px 7px 2px; }
  .dashboard-trend-heading h3 { font-size: 13px; }
  .dashboard-metric__label { align-items: flex-start; gap: 3px; line-height: 1.25; }
  .dashboard-metric__label .el-icon { font-size: 11px; flex-shrink: 0; }
  .dashboard-status-filters :deep(.el-radio-button__inner) { padding-inline: 6px; font-size: 11px; }
  .dashboard-metric { grid-column: span 2; gap: 3px; padding: 5px 17px 5px 7px; }
  .dashboard-metric:nth-last-child(-n + 2) { grid-column: span 3; }
  .dashboard-metric__arrow { inset: 6px 4px auto auto; font-size: 11px; }
  .dashboard-metric strong { font-size: 17px; }
  .dashboard-summary__heading { margin-bottom: 3px; }
  .dashboard-summary__heading h3 { font-size: 14px; }
  .dashboard-summary__grid { grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 4px; }
  .dashboard-list__filters { gap: 4px 8px; margin-bottom: 3px; }
  .dashboard-list__filters :deep(.el-input) { width: min(180px, 100%); }
}
@media (max-width: 340px) { .dashboard-mobile-row { flex-basis: 64px; padding-block: 1px; } .dashboard-mobile-row__head strong { font-size: 12px; } .dashboard-mobile-row__address, .dashboard-mobile-row__bottom { line-height: 15px; } }
@media (max-width: 768px) and (max-height: 430px) and (orientation: landscape) {
  .dashboard-workspace { grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr); grid-template-rows: minmax(0, 1fr); }
  .dashboard-workspace:has(.dashboard-list--domains) { grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); }
  .dashboard-summary__heading { display: none; }
  .dashboard-summary__grid { grid-template-columns: repeat(5, minmax(0, 1fr)); height: 100%; align-items: stretch; }
  .dashboard-metric, .dashboard-metric:nth-last-child(-n + 2) { grid-column: auto; }
  .dashboard-metric { display: flex; align-items: center; justify-content: space-between; gap: 5px; padding-inline: 7px 17px; }
  .dashboard-metric__label { flex: 1; }
  .dashboard-metric strong { font-size: 14px; }
  .dashboard-metric__label .el-icon { display: none; }
  .dashboard-list__actions { flex-wrap: wrap; }
  .dashboard-list__filters :deep(.el-input) { display: none; }
}
</style>
