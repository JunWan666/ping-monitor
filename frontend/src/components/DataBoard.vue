<template>
  <div ref="pageRoot" class="databoard-page viewport-page">
    <el-card shadow="never" class="viewport-list-card databoard-card" :class="{ 'databoard-card--trend': activeTab === 'trend' }">
      <template #header>
        <div class="databoard-toolbar">
          <el-radio-group v-model="activeTab" aria-label="看板内容">
            <el-radio-button value="trend">整体趋势</el-radio-button>
            <el-radio-button value="hosts">主机统计</el-radio-button>
          </el-radio-group>
          <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
          <div class="databoard-toolbar__range">
            <span>时间范围</span>
            <el-radio-group v-model="selectedTimeRange" class="databoard-range" aria-label="时间范围" @change="handleTimeRangeChange">
              <el-radio-button v-for="range in ranges" :key="range.value" :value="range.value">{{ range.label }}</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
      <dl class="databoard-metrics">
        <div><dt>监控主机</dt><dd>{{ displayMetric(stats.total_hosts) }}</dd></div>
        <div><dt>平均在线率</dt><dd>{{ displayMetric(stats.avg_online_rate, '%', true) }}</dd></div>
        <div><dt>平均延迟</dt><dd>{{ displayLatencyMetric() }}</dd></div>
        <div><dt>平均丢包率</dt><dd>{{ displayMetric(stats.avg_packet_loss, '%', true) }}</dd></div>
      </dl>
      <section v-show="activeTab === 'trend'" class="databoard-trend" aria-label="整体趋势图">
        <MonitorTrend :points="trendData" :loading="loading" :empty-text="loadError || '此时间范围内没有监控数据'" />
      </section>
      <template v-if="activeTab === 'hosts'">
        <div class="databoard-search">
          <el-input v-model="searchKeyword" placeholder="搜索主机或地址" clearable size="small" aria-label="搜索主机" />
          <el-select v-if="isMobile" :model-value="sortBy" size="small" aria-label="排行指标" @change="prop => handleSortChange({ prop, order: 'descending' })">
            <el-option label="按丢包率" value="avg_packet_loss" /><el-option label="按延迟" value="avg_rtt" /><el-option label="按在线率" value="online_rate" />
          </el-select>
        </div>
        <div v-if="!isMobile" class="viewport-table-area databoard-table" data-page-rows-box v-loading="loading">
          <el-table :data="filteredHostData" size="small" :empty-text="loadError || '暂无主机数据'" @sort-change="handleSortChange">
            <el-table-column label="序号" width="48" align="center"><template #default="{ $index }">{{ numberAt($index) }}</template></el-table-column>
            <el-table-column label="监控目标" min-width="190" show-overflow-tooltip>
              <template #default="{ row }"><div class="table-identity"><strong>{{ row.name }}</strong><small>{{ row.address }}</small></div></template>
            </el-table-column>
            <el-table-column label="在线率" min-width="90" align="center" sortable="custom" prop="online_rate"><template #default="{ row }"><el-tag size="small" effect="plain" :type="getOnlineRateType(row.online_rate)">{{ row.online_rate }}%</el-tag></template></el-table-column>
            <el-table-column label="丢包率" min-width="90" align="center" sortable="custom" prop="avg_packet_loss"><template #default="{ row }">{{ formatHostMetric(row, 'avg_packet_loss', '%') }}</template></el-table-column>
            <el-table-column label="平均延迟" min-width="104" align="center" sortable="custom" prop="avg_rtt"><template #default="{ row }"><span :title="`最低 ${row.min_rtt} ms · 最高 ${row.max_rtt} ms · 检查 ${row.check_count} 次`">{{ formatHostMetric(row, 'avg_rtt', ' ms') }}</span></template></el-table-column>
            <el-table-column label="操作" width="76" align="center"><template #default="{ row }"><el-button size="small" link type="primary" @click="viewHostChart(row)">详情</el-button></template></el-table-column>
          </el-table>
        </div>
        <div v-else class="databoard-mobile-list" data-page-rows-box v-loading="loading">
          <article v-for="(row, index) in filteredHostData" :key="row.id" class="databoard-mobile-row">
            <div><span class="list-number">{{ numberAt(index) }}</span><strong>{{ row.name }}</strong><el-tag size="small" effect="plain" :type="getOnlineRateType(row.online_rate)">在线 {{ row.online_rate }}%</el-tag></div>
            <small>{{ row.address }}</small>
            <div><span>丢包 {{ formatHostMetric(row, 'avg_packet_loss', '%') }} · 延迟 {{ formatHostMetric(row, 'avg_rtt', ' ms') }}</span><el-button size="small" link type="primary" @click="viewHostChart(row)">详情</el-button></div>
          </article>
          <el-empty v-if="!loading && !filteredHostData.length" :description="loadError || '暂无主机数据'" :image-size="34" />
        </div>
        <div class="viewport-table-pager">
          <el-pagination v-model:current-page="currentPage" :page-size="pageSize" :total="filteredAllHostData.length" layout="prev, pager, next" :pager-count="5" small />
        </div>
      </template>
    </el-card>
    <HostHistoryDialog ref="history" />
  </div>
</template>

<script setup>
import { computed, onActivated, onBeforeUnmount, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import api from '../api'
import HostHistoryDialog from './HostHistoryDialog.vue'
import MonitorTrend from './MonitorTrend.vue'
import { useViewport } from '../lib/useViewport'
import { usePageRows } from '../lib/usePageRows'

const { isMobile } = useViewport()
const { pageRoot, pageSize } = usePageRows({ rowHeight: 44, mobileRowHeight: () => window.innerHeight <= 340 ? 42 : window.innerHeight <= 430 ? 48 : 72 })
const ranges = [
  { value: '1h', label: '近 1 小时' }, { value: '1d', label: '近 24 小时' },
  { value: '3d', label: '近 3 天' }, { value: '7d', label: '近 7 天' },
  { value: '15d', label: '近 15 天' }, { value: '30d', label: '近 30 天' }
]
const activeTab = ref('trend')
const selectedTimeRange = ref('1d')
const searchKeyword = ref('')
const currentPage = ref(1)
const sortBy = ref('avg_packet_loss')
const sortOrder = ref('desc')
const stats = ref({})
const hostData = ref([])
const trendData = ref([])
const loading = ref(false)
const loadError = ref('')
const history = ref(null)
let latestRefresh = 0
let lastLoadedAt = 0

const hasSamples = computed(() => hostData.value.some(host => Number(host.check_count) > 0) || trendData.value.length > 0)
const hasLatencySamples = computed(() => hostData.value.some(host => Number(host.check_count) > 0 && host.avg_rtt != null && Number(host.avg_packet_loss) < 100))
const displayMetric = (value, unit = '', requiresSamples = false) => value == null || loadError.value || (requiresSamples && !hasSamples.value) ? '—' : `${value}${unit}`
const displayLatencyMetric = () => loadError.value || !hasLatencySamples.value ? '\u2014' : displayMetric(stats.value.avg_rtt, ' ms', true)
const formatHostMetric = (host, key, unit) => {
  if (!Number(host?.check_count)) return '—'
  if (key === 'avg_rtt' && Number(host.avg_packet_loss) >= 100) return '超时'
  return host[key] == null ? '—' : `${host[key]}${unit}`
}
const numberAt = index => (currentPage.value - 1) * pageSize.value + index + 1
const getOnlineRateType = rate => rate >= 95 ? 'success' : rate >= 80 ? 'warning' : 'danger'
const filteredAllHostData = computed(() => {
  const term = searchKeyword.value.trim().toLowerCase()
  return hostData.value.filter(host => !term || [host.name, host.address].some(value => value?.toLowerCase().includes(term)))
})
const filteredHostData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredAllHostData.value.slice(start, start + pageSize.value)
})
const viewHostChart = (host) => history.value.open(host, selectedTimeRange.value, ranges.find(range => range.value === selectedTimeRange.value)?.label)
const loadData = async () => {
  const request = ++latestRefresh
  loading.value = true
  loadError.value = ''
  try {
    const data = await api.getDataBoardStats(selectedTimeRange.value, sortBy.value, sortOrder.value)
    if (request !== latestRefresh) return
    stats.value = data
    hostData.value = data.host_stats || []
    trendData.value = data.trend_data || []
    lastLoadedAt = Date.now()
  } catch {
    if (request !== latestRefresh) return
    hostData.value = []
    trendData.value = []
    loadError.value = '数据加载失败，请刷新重试'
  } finally {
    if (request === latestRefresh) loading.value = false
  }
}
const handleTimeRangeChange = () => {
  currentPage.value = 1
  trendData.value = []
  hostData.value = []
  stats.value = {}
  loadData()
}
const handleSortChange = ({ prop, order }) => {
  sortBy.value = order ? prop : 'avg_packet_loss'
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  currentPage.value = 1
  loadData()
}

watch([pageSize, searchKeyword], () => { currentPage.value = 1 })
watch(() => filteredAllHostData.value.length, total => {
  currentPage.value = Math.min(currentPage.value, Math.max(1, Math.ceil(total / pageSize.value)))
})
onActivated(() => {
  if (!lastLoadedAt || Date.now() - lastLoadedAt > 15000) loadData()
})
onBeforeUnmount(() => { latestRefresh++ })
</script>

<style scoped>
.databoard-page { height: 100%; min-width: 0; min-height: 0; }
.databoard-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 10px; }
.databoard-toolbar__range { grid-column: 1 / -1; display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
.databoard-toolbar__range > span { font-size: 13px; font-weight: 600; color: var(--ink-secondary); }
.databoard-range { display: grid; grid-template-columns: repeat(6, minmax(78px, 1fr)); gap: 4px; padding: 4px; border-radius: 9px; background: #edf2f8; }
.databoard-range :deep(.el-radio-button__inner) { display: grid; place-items: center; width: 100%; min-height: 36px; padding: 4px 10px; border: 0; border-radius: 6px; background: transparent; box-shadow: none; font-size: 14px; font-weight: 600; }
.databoard-range :deep(.el-radio-button.is-active .el-radio-button__inner) { background: var(--brand); color: #fff; }
.databoard-range :deep(.el-radio-button__original-radio:focus-visible + .el-radio-button__inner) { outline: 2px solid var(--brand); outline-offset: 2px; }
.databoard-metrics { display: grid; flex: 0 0 auto; grid-template-columns: repeat(4, minmax(0, 1fr)); border: 1px solid #edf0f5; border-radius: 8px; background: #f8fafc; margin-bottom: 12px; }
.databoard-metrics > div { min-width: 0; padding: 9px 13px; }
.databoard-metrics > div + div { border-inline-start: 1px solid #e8edf3; }
.databoard-metrics dt { color: #526278; font-size: 12px; }
.databoard-metrics dd { margin: 3px 0 0; color: #253751; font-size: 22px; font-weight: 700; }
.databoard-card--trend { flex: 0 1 auto; }
.databoard-card--trend :deep(.el-card__body) { flex: 1 1 auto; }
.databoard-trend { display: flex; align-items: stretch; justify-content: center; flex: 0 1 clamp(250px, 55dvh, 480px); min-height: 0; }
.databoard-search { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.databoard-search :deep(.el-input) { width: min(255px, 100%); }
.databoard-search :deep(.el-select) { width: 108px; flex-shrink: 0; }
.databoard-mobile-list { display: flex; flex: 1 1 0; flex-direction: column; min-height: 0; overflow: hidden; }
.databoard-mobile-row { box-sizing: border-box; flex: 0 0 72px; padding: 4px 2px; border-bottom: 1px solid #edf1f5; font-size: 12px; }
.databoard-mobile-row > div { display: flex; align-items: center; gap: 6px; }
.databoard-mobile-row > div:last-child { justify-content: space-between; }
.databoard-mobile-row strong, .databoard-mobile-row small { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.databoard-mobile-row strong { flex: 1; }
.databoard-mobile-row small { display: block; color: #526278; line-height: 18px; }
@media (max-width: 768px) {
  .databoard-toolbar > :deep(.el-radio-group .el-radio-button__inner) { padding-inline: 9px; }
  .databoard-toolbar__range { display: grid; }
  .databoard-range { grid-template-columns: repeat(6, minmax(0, 1fr)); }
  .databoard-range :deep(.el-radio-button__inner) { padding-inline: 2px; font-size: 12px; }
  .databoard-trend { flex-basis: clamp(230px, 49dvh, 440px); }
  .databoard-metrics { margin-bottom: 7px; }
  .databoard-metrics > div { padding: 5px 4px; }
  .databoard-metrics dt { font-size: 10px; }
  .databoard-metrics dd { font-size: 15px; }
}
@media (max-width: 480px) {
  .databoard-range { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 768px) and (max-height: 430px) and (orientation: landscape) {
  .databoard-mobile-row { flex-basis: 48px; padding-block: 1px; }
  .databoard-mobile-row small { line-height: 13px; }
  .databoard-mobile-row > div { line-height: 14px; }
  @media (max-height: 340px) { .databoard-mobile-row { flex-basis: 42px; } .databoard-mobile-row small { display: none; } .databoard-mobile-row > div { min-height: 18px; } }
  .databoard-card :deep(.el-card__header), .databoard-card :deep(.el-card__body) { padding-block: 4px; }
  .databoard-toolbar { gap: 4px; }
  .databoard-toolbar__range { display: flex; }
  .databoard-range { grid-template-columns: repeat(6, minmax(49px, 1fr)); }
  .databoard-range :deep(.el-radio-button__inner) { min-height: 30px; }
  .databoard-metrics { margin-bottom: 3px; }
  .databoard-metrics > div { display: flex; align-items: center; gap: 4px; padding-block: 2px; }
  .databoard-metrics dd { margin: 0; }
}
</style>
