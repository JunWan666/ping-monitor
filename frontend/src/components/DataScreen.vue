<template>
  <div
    ref="screenShellRef"
    class="screen-shell"
    :class="{ 'animations-off': !screenConfig.enable_animation }"
    :style="themeStyle"
  >
    <div class="screen-background">
      <div class="bg-grid"></div>
      <div class="bg-glow bg-glow-a"></div>
      <div class="bg-glow bg-glow-b"></div>
      <div class="bg-scanlines"></div>
      <div class="bg-particles"></div>
    </div>

    <header class="screen-header glass-panel">
      <div class="header-side header-side-left">
        <div class="clock-panel">
          <div class="clock-value">{{ currentTime }}</div>
          <div class="clock-subtitle">上次同步 {{ lastUpdatedLabel }}</div>
        </div>
        <div class="header-status">
          <span class="status-dot"></span>
          公共态势屏
        </div>
      </div>

      <div class="header-center header-center-main">
        <div class="header-kicker">CPOLAR / DIGITAL TWIN</div>
        <h1 class="screen-title">{{ screenTitle }}</h1>
        <div class="header-meta">
          <span class="meta-chip">刷新间隔 {{ screenConfig.refresh_interval }}s</span>
          <span class="meta-chip">{{ screenConfig.enable_3d ? '3D 模式' : '平面模式' }}</span>
          <span class="meta-chip">{{ screenConfig.show_flow_lines ? '流光飞线开启' : '流光飞线关闭' }}</span>
        </div>
      </div>

      <div class="header-side header-side-right">
        <div class="header-actions">
          <button class="header-action-button" type="button" @click="toggleFullscreen">
            <el-icon><FullScreen /></el-icon>
            <span>{{ isFullscreen ? '退出全屏' : '全屏' }}</span>
          </button>
          <button class="header-action-button admin-button" type="button" @click="goToAdmin">
            <el-icon><Setting /></el-icon>
            <span>管理后台</span>
          </button>
        </div>
      </div>
    </header>

    <section
      id="mobile-overview"
      class="metric-grid"
      :class="{ 'is-mobile-active': activeMobileTab === 'overview' }"
    >
      <article
        v-for="metric in metricCards"
        :key="metric.key"
        class="metric-card glass-panel"
        :class="metric.tone"
      >
        <div class="metric-icon">
          <component :is="metric.icon" />
        </div>
        <div class="metric-main">
          <div class="metric-label">{{ metric.label }}</div>
          <div class="metric-value">
            <span>{{ metric.value }}</span>
            <em>{{ metric.unit }}</em>
          </div>
          <div v-if="metric.details" class="metric-detail-row">
            <span
              v-for="detail in metric.details"
              :key="detail.label"
              class="metric-detail"
              :class="detail.tone"
            >
              <i></i>
              <span>{{ detail.label }}</span>
              <strong>{{ detail.value }}</strong>
            </span>
          </div>
          <div v-if="metric.note" class="metric-note">{{ metric.note }}</div>
        </div>
      </article>
    </section>

    <section
      class="mobile-overview-detail glass-panel"
      :class="{ 'is-mobile-active': activeMobileTab === 'overview' }"
    >
      <div class="panel-head">
        <div>
          <div class="panel-kicker">Overview</div>
          <h2>运行概况</h2>
        </div>
        <div class="panel-extra">实时同步</div>
      </div>

      <div class="mobile-health-grid">
        <div
          v-for="item in mobileHealthStats"
          :key="item.label"
          class="mobile-health-item"
          :class="item.tone"
        >
          <label>
            <span></span>
            {{ item.label }}
          </label>
          <strong>{{ item.value }}</strong>
        </div>
      </div>

      <div class="mobile-data-grid">
        <div v-for="item in mobileOverviewStats" :key="item.label" class="mobile-data-item">
          <label>{{ item.label }}</label>
          <strong>{{ item.value }}</strong>
          <span>{{ item.unit }}</span>
        </div>
      </div>

      <div class="mobile-section-title">覆盖热点</div>
      <div class="mobile-chip-row">
        <span v-for="item in topProvinceTags" :key="item.name" class="mobile-chip">
          {{ item.name }}
          <strong>{{ item.value }}台</strong>
        </span>
      </div>

      <div class="mobile-section-title">网络分布</div>
      <div class="mobile-chip-row">
        <span v-for="item in topIspTags" :key="item.name" class="mobile-chip">
          {{ item.name }}
          <strong>{{ item.value }}台</strong>
        </span>
      </div>
    </section>

    <section class="screen-body">
      <aside class="side-column">
        <section class="panel glass-panel trend-panel">
          <div class="panel-head">
            <div>
              <div class="panel-kicker">Performance</div>
              <h2>24H 响应趋势</h2>
            </div>
            <div class="panel-extra">{{ trendSummary }}</div>
          </div>
          <div ref="trendChartRef" class="chart-panel trend-chart"></div>
        </section>

        <section
          id="mobile-alerts"
          class="panel glass-panel alert-panel"
          :class="{ 'is-mobile-active': activeMobileTab === 'alerts' }"
        >
          <div class="panel-head">
            <div>
              <div class="panel-kicker">Alert Stream</div>
              <h2>实时告警滚动</h2>
            </div>
            <div class="panel-extra">{{ alerts.length }} 条</div>
          </div>
          <div class="mobile-alert-summary">
            <span class="warning">告警 {{ summary.warningHosts }} 台</span>
            <span class="danger">离线 {{ summary.offlineHosts }} 台</span>
            <span>最近 {{ alerts.length }} 条</span>
          </div>
          <div class="alert-marquee">
            <div class="alert-list">
              <article
                v-for="(alert, index) in visibleAlerts"
                :key="`${alert.id || alert.created_at || 'empty'}-${index}`"
                class="alert-item"
                :class="alertTone(alert)"
              >
                <div class="alert-topline">
                  <span class="alert-host">{{ alert.host_name || '系统状态' }}</span>
                  <span class="alert-time">{{ formatAlertTime(alert.created_at) }}</span>
                </div>
                <div class="alert-facts">
                  <span v-for="fact in getAlertFacts(alert)" :key="`${alert.id || alert.created_at}-${fact.label}`" class="alert-fact">
                    <label>{{ fact.label }}</label>
                    <strong :class="{ 'alert-fact-status': Boolean(fact.tone) }">
                      <span v-if="fact.tone" class="alert-fact-dot" :class="fact.tone"></span>
                      <span>{{ fact.value }}</span>
                    </strong>
                  </span>
                </div>
              </article>
            </div>
          </div>
        </section>
      </aside>

      <main class="center-column">
        <section
          id="mobile-map"
          class="stage-panel glass-panel"
          :class="{ 'is-mobile-active': activeMobileTab === 'map' }"
        >
          <div class="panel-head stage-head">
            <div>
              <div class="panel-kicker">Main Stage</div>
              <h2>{{ activeMapTitle }}</h2>
            </div>
            <div class="stage-flags">
              <span class="stage-flag">{{ activeCoverageLabel }}</span>
              <span class="stage-flag">地理点位 {{ visibleGeoPointCount }}</span>
              <span class="stage-flag">海外主机 {{ overseasHostCount }}</span>
              <button type="button" class="stage-toggle" :class="{ active: currentMapView === 'china' }" @click="setMapView('china')">
                中国视图
              </button>
              <button type="button" class="stage-toggle" :class="{ active: currentMapView === 'world' }" @click="setMapView('world')">
                全球视图
              </button>
            </div>
          </div>

          <div class="stage-overview">
            <div class="overview-pill">
              <label>在线率</label>
              <strong>{{ summary.onlineRate.toFixed(1) }}%</strong>
            </div>
            <div class="overview-pill">
              <label>平均延迟</label>
              <strong>{{ summary.avgRtt.toFixed(1) }}ms</strong>
            </div>
            <div class="overview-pill">
              <label>异常节点</label>
              <strong>{{ summary.abnormalHosts }}</strong>
            </div>
            <div class="overview-pill">
              <label>当前视图</label>
              <strong>{{ currentMapView === 'china' ? '中国' : '全球' }}</strong>
            </div>
          </div>

          <div class="map-stage" :style="mapStageStyle">
            <div class="map-orbit map-orbit-a"></div>
            <div class="map-orbit map-orbit-b"></div>
            <div class="map-surface">
              <div ref="mapChartRef" class="map-chart"></div>
            </div>

            <div class="stage-hint glass-inset">
              <strong>{{ mapHintTitle }}</strong>
              <span>{{ mapHintText }}</span>
            </div>

            <div class="stage-legend glass-inset">
              <div class="legend-row">
                <span class="legend-dot success"></span>
                <span>区域在线</span>
              </div>
              <div class="legend-row">
                <span class="legend-dot warning"></span>
                <span>区域告警/高延迟</span>
              </div>
              <div class="legend-row">
                <span class="legend-dot danger"></span>
                <span>区域异常/离线</span>
              </div>
              <div class="legend-row">
                <span class="legend-line"></span>
                <span>数据流飞线</span>
              </div>
              <div class="legend-note">{{ legendNote }}</div>
            </div>
          </div>

          <div class="mobile-map-detail">
            <div class="mobile-data-grid">
              <div v-for="item in mobileMapStats" :key="item.label" class="mobile-data-item">
                <label>{{ item.label }}</label>
                <strong>{{ item.value }}</strong>
                <span>{{ item.unit }}</span>
              </div>
            </div>
            <div class="mobile-map-note">{{ legendNote }}</div>
          </div>
        </section>
      </main>

      <aside class="side-column">
        <section class="panel glass-panel distribution-panel">
          <div class="panel-head">
            <div>
              <div class="panel-kicker">Distribution</div>
              <h2>运营商分布</h2>
            </div>
            <div class="panel-extra">TOP {{ ispDistribution.length }}</div>
          </div>
          <div ref="ispChartRef" class="chart-panel donut-chart"></div>
          <div class="tag-cloud">
            <span
              v-for="item in topIspTags"
              :key="item.name"
              class="cloud-tag"
              :title="`${item.name} ${item.value}台`"
            >
              <span class="cloud-tag-name">{{ item.name }}</span>
              <strong class="cloud-tag-value">{{ item.value }}台</strong>
            </span>
          </div>
        </section>

        <section
          id="mobile-ranking"
          class="panel glass-panel ranking-panel"
          :class="{ 'is-mobile-active': activeMobileTab === 'ranking' }"
        >
          <div class="panel-head">
            <div>
              <div class="panel-kicker">Hot Spot</div>
              <h2>响应时间最慢 TOP10</h2>
            </div>
            <div class="panel-extra">按 24H 平均 RTT</div>
          </div>

          <div class="mobile-ranking-summary">
            <span>平均延迟 {{ summary.avgRtt.toFixed(1) }}ms</span>
            <span v-if="slowHosts[0]">最慢 {{ slowHosts[0].avg_rtt.toFixed(1) }}ms</span>
            <span>在线率 {{ summary.onlineRate.toFixed(1) }}%</span>
          </div>

          <div class="ranking-list">
            <article
              v-for="host in slowHosts"
              :key="host.id"
              class="ranking-item"
              :class="host.tone"
            >
              <div class="rank-badge">{{ host.rank }}</div>
              <div class="rank-main">
                <div class="rank-topline">
                  <strong>{{ host.name }}</strong>
                  <span>{{ host.avg_rtt.toFixed(1) }}ms</span>
                </div>
                <div class="rank-subline">
                  <span>{{ host.location }}</span>
                  <span>在线率 {{ host.online_rate.toFixed(1) }}%</span>
                </div>
                <div class="rank-bar">
                  <span :style="{ width: `${host.barWidth}%` }"></span>
                </div>
              </div>
            </article>

            <div v-if="!slowHosts.length" class="empty-state">
              暂无足够数据生成主机排行
            </div>
          </div>
        </section>
      </aside>
    </section>

    <nav class="mobile-tabbar glass-panel" aria-label="移动端大屏导航">
      <button
        type="button"
        :class="{ active: activeMobileTab === 'overview' }"
        @click="setMobileTab('overview')"
      >
        <el-icon><Monitor /></el-icon>
        <span>总览</span>
      </button>
      <button
        type="button"
        :class="{ active: activeMobileTab === 'map' }"
        @click="setMobileTab('map')"
      >
        <el-icon><DataAnalysis /></el-icon>
        <span>地图</span>
      </button>
      <button
        type="button"
        :class="{ active: activeMobileTab === 'alerts' }"
        @click="setMobileTab('alerts')"
      >
        <el-icon><Bell /></el-icon>
        <span>告警</span>
      </button>
      <button
        type="button"
        :class="{ active: activeMobileTab === 'ranking' }"
        @click="setMobileTab('ranking')"
      >
        <el-icon><Timer /></el-icon>
        <span>排行</span>
      </button>
    </nav>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import {
  Bell,
  CircleCheckFilled,
  DataAnalysis,
  FullScreen,
  Monitor,
  Setting,
  Timer
} from '@element-plus/icons-vue'
import api from '../api'

const route = useRoute()
const router = useRouter()

const CHINA_MAP_NAME = 'ping-monitor-china'
const WORLD_MAP_NAME = 'ping-monitor-world'
const VISIBLE_ALERT_COUNT = 5
const WARNING_RTT_THRESHOLD = 100
const LIVE_TREND_POINT_LIMIT = 48

const themePalettes = {
  blue: {
    background: '#000814',
    backgroundAlt: '#03162f',
    panel: 'rgba(7, 20, 43, 0.72)',
    panelInset: 'rgba(10, 29, 58, 0.62)',
    border: 'rgba(30, 144, 255, 0.28)',
    accent: '#1E90FF',
    accentSoft: 'rgba(30, 144, 255, 0.22)',
    map: '#0A192F',
    flow: '#6fe7ff',
    success: '#00FFC3',
    warning: '#FADB14',
    danger: '#FF4D4F',
    text: '#EAF4FF',
    muted: '#89A7C7',
    grid: 'rgba(61, 132, 255, 0.13)'
  },
  green: {
    background: '#03150f',
    backgroundAlt: '#0d2b1d',
    panel: 'rgba(8, 28, 21, 0.72)',
    panelInset: 'rgba(11, 39, 29, 0.64)',
    border: 'rgba(0, 255, 195, 0.22)',
    accent: '#00D7A3',
    accentSoft: 'rgba(0, 215, 163, 0.22)',
    map: '#08231a',
    flow: '#9bffe4',
    success: '#00FFC3',
    warning: '#FADB14',
    danger: '#FF6B6B',
    text: '#E7FFF8',
    muted: '#94C6B7',
    grid: 'rgba(0, 255, 195, 0.11)'
  },
  purple: {
    background: '#140726',
    backgroundAlt: '#25113f',
    panel: 'rgba(25, 10, 48, 0.74)',
    panelInset: 'rgba(37, 16, 68, 0.64)',
    border: 'rgba(120, 127, 255, 0.22)',
    accent: '#7A7FFF',
    accentSoft: 'rgba(122, 127, 255, 0.22)',
    map: '#1b1234',
    flow: '#c2c6ff',
    success: '#00FFC3',
    warning: '#FADB14',
    danger: '#FF4D9B',
    text: '#F4EEFF',
    muted: '#B8ABD7',
    grid: 'rgba(122, 127, 255, 0.12)'
  },
  red: {
    background: '#16060b',
    backgroundAlt: '#331019',
    panel: 'rgba(39, 10, 18, 0.74)',
    panelInset: 'rgba(58, 14, 26, 0.62)',
    border: 'rgba(255, 77, 79, 0.22)',
    accent: '#FF6B6B',
    accentSoft: 'rgba(255, 107, 107, 0.22)',
    map: '#2a1018',
    flow: '#ffb2b3',
    success: '#00FFC3',
    warning: '#FADB14',
    danger: '#FF4D4F',
    text: '#FFF0F1',
    muted: '#DDB4B8',
    grid: 'rgba(255, 107, 107, 0.12)'
  },
  orange: {
    background: '#1d1205',
    backgroundAlt: '#39220e',
    panel: 'rgba(43, 24, 8, 0.74)',
    panelInset: 'rgba(61, 34, 10, 0.62)',
    border: 'rgba(255, 167, 38, 0.22)',
    accent: '#FFA726',
    accentSoft: 'rgba(255, 167, 38, 0.22)',
    map: '#2d1b08',
    flow: '#ffd59b',
    success: '#00FFC3',
    warning: '#FFD666',
    danger: '#FF6B6B',
    text: '#FFF6EB',
    muted: '#D9B992',
    grid: 'rgba(255, 167, 38, 0.12)'
  }
}

const defaultScreenConfig = {
  brand_name: '',
  refresh_interval: 10,
  enable_3d: true,
  enable_animation: true,
  map_view_angle: 45,
  particle_count: 120,
  show_flow_lines: true,
  theme_color: 'blue',
  public_enabled: true
}

const screenConfig = reactive({ ...defaultScreenConfig })
const datascreenPayload = ref({
  total_hosts: 0,
  enabled_hosts: 0,
  recent_alerts: 0,
  host_status: [],
  control_center: null,
  screen_config: { ...defaultScreenConfig }
})
const databoardStats = ref({
  total_hosts: 0,
  avg_online_rate: 0,
  avg_rtt: 0,
  avg_packet_loss: 0,
  host_stats: [],
  trend_data: []
})
const alerts = ref([])
const liveTrendPoints = ref([])
const currentTime = ref('')
const lastUpdatedAt = ref(null)
const loading = ref(false)
const alertCursor = ref(0)
const isPreviewMode = computed(() => Boolean(route.meta?.previewMode))

const resolveInitialMapView = () => {
  if (typeof window === 'undefined') {
    return 'china'
  }

  const mapView = new URLSearchParams(window.location.search).get('mapView')
  return mapView === 'world' ? 'world' : 'china'
}

const currentMapView = ref(resolveInitialMapView())
const activeMobileTab = ref('overview')
const isTouchLikeDevice = ref(false)

const screenShellRef = ref(null)
const trendChartRef = ref(null)
const mapChartRef = ref(null)
const ispChartRef = ref(null)
const provinceCenters = ref(new Map())
const provinceFeatureIndex = ref(new Map())
const worldRegionNames = ref([])
const isFullscreen = ref(false)

let trendChartInstance = null
let mapChartInstance = null
let ispChartInstance = null
let refreshTimer = null
let clockTimer = null
let alertTickerTimer = null
let resizeHandler = null
let chinaMapPromise = null
let worldMapPromise = null
let pinnedMapTooltip = null
let selectedMapProvinceName = null
let mapClickHandler = null
let mapBlankClickHandler = null
let mapRoamHandler = null
let fullscreenChangeHandler = null
const metricFrames = new Map()
const CALLOUT_PROVINCE_LABELS = new Set()
const PROVINCE_CALLOUT_TARGETS = {}
const SELECTED_PROVINCE_REGION_STYLE = {
  itemStyle: {
    areaColor: 'rgba(250, 219, 20, 0.62)',
    borderColor: 'rgba(255, 246, 176, 0.98)',
    borderWidth: 2,
    shadowBlur: 28,
    shadowColor: 'rgba(250, 219, 20, 0.46)'
  },
  label: {
    show: false
  }
}
const mapRoamState = reactive({
  china: {
    zoom: 1
  },
  world: {
    zoom: 1
  }
})

const animatedMetrics = reactive({
  totalHosts: 0,
  onlineHosts: 0,
  abnormalHosts: 0,
  avgRtt: 0,
  recentAlerts: 0
})

const palette = computed(() => themePalettes[screenConfig.theme_color] || themePalettes.blue)
const screenTitle = computed(() => {
  const brandName = normalizeLocation(screenConfig.brand_name)
  return brandName ? `${brandName} 网络监控可视化大屏` : '网络监控可视化大屏'
})

const themeStyle = computed(() => ({
  '--screen-bg': palette.value.background,
  '--screen-bg-alt': palette.value.backgroundAlt,
  '--panel-bg': palette.value.panel,
  '--panel-inset': palette.value.panelInset,
  '--panel-border': palette.value.border,
  '--accent': palette.value.accent,
  '--accent-soft': palette.value.accentSoft,
  '--map-core': palette.value.map,
  '--flow': palette.value.flow,
  '--success': palette.value.success,
  '--warning': palette.value.warning,
  '--danger': palette.value.danger,
  '--text-main': palette.value.text,
  '--text-muted': palette.value.muted,
  '--grid-line': palette.value.grid,
  '--animation-state': screenConfig.enable_animation ? 'running' : 'paused'
}))

const mapTooltipTriggerOn = computed(() => (isTouchLikeDevice.value ? 'click' : 'mousemove|click'))

const mapStageStyle = computed(() => ({
  '--map-tilt': screenConfig.enable_3d && currentMapView.value === 'china' ? `${clamp(screenConfig.map_view_angle * 0.24, 4, 11)}deg` : '0deg',
  '--map-scale': currentMapView.value === 'china' ? (screenConfig.enable_3d ? '1.2' : '1.1') : '1.04',
  '--map-shift-y': currentMapView.value === 'china' ? (screenConfig.enable_3d ? '-1%' : '0%') : '-1.5%'
}))

const hosts = computed(() => datascreenPayload.value.host_status || [])

const getHostStatusType = (host) => {
  if (host?.status_type) {
    return host.status_type
  }
  if (host?.status === '离线') {
    return 'offline'
  }
  if (host?.status === '异常') {
    return 'warning'
  }
  if (host?.status === '正常') {
    return 'normal'
  }
  return 'unknown'
}

const isHostOnline = (host) => {
  if (typeof host?.is_online === 'boolean') {
    return host.is_online
  }
  const statusType = getHostStatusType(host)
  return statusType === 'normal' || statusType === 'warning'
}

const getHostTone = (host) => {
  const statusType = getHostStatusType(host)
  if (statusType === 'offline') {
    return 'abnormal'
  }
  if (statusType === 'warning' || Number(host?.avg_rtt || 0) >= WARNING_RTT_THRESHOLD) {
    return 'warning'
  }
  if (statusType === 'normal') {
    return 'normal'
  }
  return 'neutral'
}

const getHostStatusText = (host) => {
  const statusType = getHostStatusType(host)
  if (statusType === 'offline') {
    return '离线'
  }
  if (statusType === 'warning') {
    return '丢包告警'
  }
  return `${Number(host?.avg_rtt || 0).toFixed(1)}ms`
}

const compareHostsByStatus = (a, b) => {
  const priority = {
    offline: 4,
    warning: 3,
    normal: 2,
    unknown: 1
  }
  const aPriority = priority[getHostStatusType(a)] || 0
  const bPriority = priority[getHostStatusType(b)] || 0
  if (aPriority !== bPriority) {
    return bPriority - aPriority
  }
  return Number(b?.avg_rtt || 0) - Number(a?.avg_rtt || 0)
}

const geoHosts = computed(() =>
  hosts.value
    .map((host) => {
      const coordinates = resolveHostMapCoordinates(host)
      if (!coordinates) {
        return null
      }

      return {
        ...host,
        longitude: coordinates.longitude,
        latitude: coordinates.latitude,
        map_coordinate_source: coordinates.source,
        avg_rtt: Number(host.avg_rtt) || 0,
        country: normalizeCountry(host.country),
        province: normalizeLocation(host.province, '未定位区域'),
        city: normalizeLocation(host.city, ''),
        isp: normalizeIsp(host.isp)
      }
    })
    .filter(Boolean)
)

const domesticGeoHosts = computed(() => geoHosts.value.filter((host) => isChinaHost(host)))
const overseasGeoHosts = computed(() => geoHosts.value.filter((host) => !isChinaHost(host)))
const hasOverseasHosts = computed(() => overseasGeoHosts.value.length > 0)
const controlCenter = computed(() => datascreenPayload.value.control_center || null)
const controlCenterCoords = computed(() => {
  const center = controlCenter.value
  if (hasValidCoordinates(center?.longitude, center?.latitude)) {
    return [Number(center.longitude), Number(center.latitude)]
  }
  return null
})
const controlCenterName = computed(() => {
  const center = controlCenter.value
  if (center?.source === 'default') {
    return '默认监控中心'
  }
  return center?.name || center?.city || center?.province || '监控中心'
})
const controlCenterLabel = computed(() => {
  const center = controlCenter.value
  if (center?.source === 'default') {
    return '默认中心'
  }
  return center?.city || center?.province || '监控中心'
})

const provinceLabelPoints = computed(() =>
  Array.from(provinceCenters.value.entries())
    .map(([name, center]) => {
      const normalizedName = normalizeProvince(name)
      if (CALLOUT_PROVINCE_LABELS.has(normalizedName)) {
        return null
      }

      const provinceEntry = provinceHostIndex.value.get(normalizedName)
      return {
        name,
        value: [...center, 1],
        labelName: shortenProvinceName(name),
        tone: getProvinceTone(provinceEntry)
      }
    })
    .filter(Boolean)
)

const crowdedProvinceCallouts = computed(() =>
  Array.from(provinceCenters.value.entries())
    .map(([name, center]) => {
      const normalizedName = normalizeProvince(name)
      const target = PROVINCE_CALLOUT_TARGETS[normalizedName]
      if (!target) {
        return null
      }

      const provinceEntry = provinceHostIndex.value.get(normalizedName)
      const tone = getProvinceTone(provinceEntry)

      return {
        name,
        tone,
        labelName: shortenProvinceName(name),
        value: [...target, 1],
        sourceValue: [...center, 1],
        hosts: provinceEntry?.hosts || [],
        normalCount: provinceEntry?.normalCount || 0,
        warningCount: provinceEntry?.warningCount || 0,
        abnormalCount: provinceEntry?.abnormalCount || 0,
        avgRtt: provinceEntry?.avgRtt || 0,
        tooltipType: 'province'
      }
    })
    .filter(Boolean)
)

const crowdedProvinceCalloutLines = computed(() =>
  crowdedProvinceCallouts.value.map((item) => ({
    coords: [item.sourceValue.slice(0, 2), item.value.slice(0, 2)],
    lineStyle: {
      color: getProvinceCalloutColor(item.tone),
      width: 1.15,
      opacity: 0.82
    }
  }))
)

const crowdedProvinceAnchorPoints = computed(() =>
  crowdedProvinceCallouts.value.map((item) => ({
    ...item,
    value: item.sourceValue
  }))
)

const provinceHostIndex = computed(() => {
  const provinceMap = new Map()

  domesticGeoHosts.value.forEach((host) => {
    const provinceKey = normalizeProvince(host.province)
    if (!provinceKey) {
      return
    }

    if (!provinceMap.has(provinceKey)) {
      provinceMap.set(provinceKey, {
        name: provinceKey,
        hosts: [],
        normalCount: 0,
        warningCount: 0,
        abnormalCount: 0,
        avgRttTotal: 0
      })
    }

    const entry = provinceMap.get(provinceKey)
    entry.hosts.push({
      id: host.id,
      name: host.name,
      status: host.status,
      status_type: host.status_type,
      packet_loss: host.packet_loss,
      avg_rtt: host.avg_rtt,
      city: host.city,
      address: host.address
    })
    entry.avgRttTotal += host.avg_rtt

    if (getHostStatusType(host) === 'offline') {
      entry.abnormalCount += 1
    } else {
      entry.normalCount += 1
      if (getHostStatusType(host) === 'warning' || host.avg_rtt >= WARNING_RTT_THRESHOLD) {
        entry.warningCount += 1
      }
    }
  })

  provinceMap.forEach((entry) => {
    entry.hosts.sort(compareHostsByStatus)
    entry.avgRtt = entry.hosts.length ? entry.avgRttTotal / entry.hosts.length : 0
    delete entry.avgRttTotal
  })

  return provinceMap
})

const provinceMapSeriesData = computed(() =>
  provinceDistribution.value.map((item) => {
    const provinceEntry = provinceHostIndex.value.get(normalizeProvince(item.name))
    const tone = getProvinceTone(provinceEntry)
    const isCrowdedRegion = CALLOUT_PROVINCE_LABELS.has(normalizeProvince(item.name))
    return {
      name: item.name,
      value: item.value,
      hosts: provinceEntry?.hosts || [],
      normalCount: provinceEntry?.normalCount || 0,
      warningCount: provinceEntry?.warningCount || 0,
      abnormalCount: provinceEntry?.abnormalCount || 0,
      avgRtt: provinceEntry?.avgRtt || 0,
      tone,
      isCrowdedRegion,
      itemStyle: getProvinceAreaStyle(tone, item.value, false, isCrowdedRegion),
      emphasis: {
        itemStyle: getProvinceAreaStyle(tone, item.value, true, isCrowdedRegion)
      }
    }
  })
)

const mapPointClusters = computed(() => {
  const clusterMap = new Map()

  geoHosts.value.forEach((host) => {
    const key = `${host.longitude.toFixed(3)}:${host.latitude.toFixed(3)}`

    if (!clusterMap.has(key)) {
      clusterMap.set(key, {
        id: key,
        longitude: host.longitude,
        latitude: host.latitude,
        country: host.country,
        province: host.province,
        city: host.city,
        hosts: [],
        avgRttTotal: 0,
        abnormalCount: 0,
        warningCount: 0
      })
    }

    const cluster = clusterMap.get(key)
    cluster.hosts.push({
      id: host.id,
      name: host.name,
      status: host.status,
      status_type: host.status_type,
      packet_loss: host.packet_loss,
      avg_rtt: host.avg_rtt,
      country: host.country,
      address: host.address,
      city: host.city
    })
    cluster.avgRttTotal += host.avg_rtt

    if (getHostStatusType(host) === 'offline') {
      cluster.abnormalCount += 1
    } else if (getHostStatusType(host) === 'warning' || host.avg_rtt >= WARNING_RTT_THRESHOLD) {
      cluster.warningCount += 1
    }
  })

  return Array.from(clusterMap.values())
    .map((cluster) => {
      const hostCount = cluster.hosts.length
      const avgRtt = hostCount ? cluster.avgRttTotal / hostCount : 0
      const tone = cluster.abnormalCount > 0 ? 'abnormal' : cluster.warningCount > 0 || avgRtt >= 100 ? 'warning' : 'normal'

      cluster.hosts.sort(compareHostsByStatus)

      return {
        id: cluster.id,
        name: cluster.city || cluster.province || cluster.hosts[0]?.name || '未知点位',
        value: [cluster.longitude, cluster.latitude, avgRtt],
        avgRtt,
        hostCount,
        province: cluster.province,
        city: cluster.city,
        tone,
        abnormalCount: cluster.abnormalCount,
        warningCount: cluster.warningCount,
        hosts: cluster.hosts,
        country: normalizeCountry(cluster.hosts[0]?.country || cluster.country),
        isDomestic: isChinaHost(cluster),
        location: [cluster.country, cluster.province, cluster.city].filter(Boolean).join(' / ') || cluster.hosts[0]?.address || '位置未知'
      }
    })
    .sort((a, b) => b.hostCount - a.hostCount || b.avgRtt - a.avgRtt)
})

const domesticMapPointClusters = computed(() => mapPointClusters.value.filter((point) => point.isDomestic))
const overseasMapPointClusters = computed(() => mapPointClusters.value.filter((point) => !point.isDomestic))

const summary = computed(() => {
  const totalHosts = Number(datascreenPayload.value.total_hosts) || hosts.value.length
  const onlineHosts = hosts.value.filter(isHostOnline).length
  const offlineHosts = hosts.value.filter((host) => getHostStatusType(host) === 'offline').length
  const warningHosts = hosts.value.filter((host) => {
    const statusType = getHostStatusType(host)
    return statusType !== 'offline' && (statusType === 'warning' || Number(host.avg_rtt || 0) >= WARNING_RTT_THRESHOLD)
  }).length
  const abnormalHosts = warningHosts + offlineHosts
  const avgRtt = Number(databoardStats.value.avg_rtt) || average(hosts.value.map((host) => Number(host.avg_rtt) || 0))
  const onlineRate = totalHosts > 0 ? (onlineHosts / totalHosts) * 100 : 0

  return {
    totalHosts,
    onlineHosts,
    warningHosts,
    offlineHosts,
    abnormalHosts,
    avgRtt,
    onlineRate,
    recentAlerts: Number(datascreenPayload.value.recent_alerts) || alerts.value.length
  }
})

const activeProvinceCount = computed(() => provinceDistribution.value.length)
const activeCountryCount = computed(() => countryDistribution.value.length)
const geoPointCount = computed(() => mapPointClusters.value.length)
const visibleGeoPointCount = computed(() => (currentMapView.value === 'china' ? domesticMapPointClusters.value.length : mapPointClusters.value.length))
const overseasHostCount = computed(() => overseasGeoHosts.value.length)
const activeMapTitle = computed(() => (currentMapView.value === 'china' ? '中国节点数字孪生地图' : '全球节点跨境链路视图'))
const activeCoverageLabel = computed(() => (currentMapView.value === 'china' ? `覆盖省份 ${activeProvinceCount.value}` : `覆盖国家 ${activeCountryCount.value}`))
const mapHintTitle = computed(() => (currentMapView.value === 'china' ? '中国地图热点分布' : '全球节点跨境链路'))
const mapHintText = computed(() =>
  currentMapView.value === 'china'
    ? (hasOverseasHosts.value ? '默认展示中国地图，海外主机可切换到全球视图查看飞线与点位，支持滚轮缩放与左键拖动。' : '默认展示中国地图，悬停查看，点击可固定详情卡并滚动主机列表，支持滚轮缩放与左键拖动。')
    : '全球视图会缩小中国版图并优先突显海外节点与跨境飞线，支持滚轮缩放与左键拖动。'
)
const legendNote = computed(() =>
  currentMapView.value === 'china'
    ? (hasOverseasHosts.value ? '海外主机可切到全球视图查看，详情卡支持点击固定，地图支持漫游。' : '悬停查看，点击固定，详情卡支持滚动，地图支持漫游。')
    : '全球视图会弱化国内点位、突出海外链路，点击节点可固定详情卡，地图支持漫游。'
)

const provinceDistribution = computed(() => {
  const counter = new Map()
  domesticGeoHosts.value.forEach((host) => {
    const province = normalizeProvince(host.province)
    if (!province) {
      return
    }
    counter.set(province, (counter.get(province) || 0) + 1)
  })

  return Array.from(counter.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
})

const countryDistribution = computed(() => {
  const counter = new Map()

  geoHosts.value.forEach((host) => {
    const country = normalizeCountry(host.country)
    if (!country) {
      return
    }

    counter.set(country, (counter.get(country) || 0) + 1)
  })

  return Array.from(counter.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
})

const worldMapSeriesData = computed(() =>
  worldRegionNames.value.map((name) => ({
    name
  }))
)

const ispDistribution = computed(() => {
  const counter = new Map()
  hosts.value.forEach((host) => {
    const isp = normalizeIsp(host.isp)
    counter.set(isp, (counter.get(isp) || 0) + 1)
  })

  return Array.from(counter.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6)
})

const topIspTags = computed(() => ispDistribution.value.slice(0, 6))
const topProvinceTags = computed(() => provinceDistribution.value.slice(0, 6))

const mobileHealthStats = computed(() => [
  { label: '在线', value: `${summary.value.onlineHosts} 台`, tone: 'success' },
  { label: '告警', value: `${summary.value.warningHosts} 台`, tone: 'warning' },
  { label: '离线', value: `${summary.value.offlineHosts} 台`, tone: 'danger' },
  { label: '在线率', value: `${summary.value.onlineRate.toFixed(1)}%`, tone: 'success' }
])

const mobileOverviewStats = computed(() => [
  { label: '覆盖省份', value: activeProvinceCount.value, unit: '个' },
  { label: '覆盖国家', value: activeCountryCount.value, unit: '个' },
  { label: '地理点位', value: geoPointCount.value, unit: '个' },
  { label: '海外主机', value: overseasHostCount.value, unit: '台' }
])

const mobileMapStats = computed(() => [
  { label: '当前视图', value: currentMapView.value === 'china' ? '中国' : '全球', unit: '' },
  { label: '显示点位', value: visibleGeoPointCount.value, unit: '个' },
  { label: currentMapView.value === 'china' ? '覆盖省份' : '覆盖国家', value: currentMapView.value === 'china' ? activeProvinceCount.value : activeCountryCount.value, unit: '个' },
  { label: '海外主机', value: overseasHostCount.value, unit: '台' }
])

const trendChartData = computed(() => {
  const history = databoardStats.value.trend_data || []
  const liveTail = liveTrendPoints.value.slice(-8)

  if (!history.length) {
    return liveTrendPoints.value
  }

  return [...history.slice(-24), ...liveTail]
})

const slowHosts = computed(() => {
  const source = databoardStats.value.host_stats?.length
    ? databoardStats.value.host_stats
    : hosts.value.map((host) => ({
        id: host.id,
        name: host.name,
        avg_rtt: Number(host.avg_rtt) || 0,
        online_rate: isHostOnline(host) ? 100 : 0,
        address: host.address
      }))

  const ranked = [...source]
    .filter((host) => Number(host.avg_rtt) > 0)
    .sort((a, b) => Number(b.avg_rtt || 0) - Number(a.avg_rtt || 0))
    .slice(0, 10)

  const maxRtt = ranked[0]?.avg_rtt || 1

  return ranked.map((host, index) => ({
    ...host,
    rank: index + 1,
    tone: Number(host.online_rate) < 95 ? 'danger' : Number(host.avg_rtt) > 100 ? 'warning' : 'success',
    barWidth: Math.max(14, Math.round((Number(host.avg_rtt || 0) / maxRtt) * 100)),
    location: normalizeLocation(host.address, '地址未知')
  }))
})

const visibleAlerts = computed(() => {
  if (!alerts.value.length) {
    return [
      {
        id: 'placeholder',
        host_name: '态势感知',
        message: '当前时间窗口内暂无异常告警，大屏处于平稳监控状态。',
        created_at: new Date().toISOString(),
        alert_type: 'info'
      }
    ]
  }

  const count = Math.min(VISIBLE_ALERT_COUNT, alerts.value.length)
  return Array.from({ length: count }, (_, index) => alerts.value[(alertCursor.value + index) % alerts.value.length])
})

const metricCards = computed(() => [
  {
    key: 'totalHosts',
    label: '监控主机',
    value: formatMetric(animatedMetrics.totalHosts),
    unit: '台',
    note: `已定位 ${geoPointCount.value} 个地理节点`,
    icon: Monitor,
    tone: 'tone-accent'
  },
  {
    key: 'onlineHosts',
    label: '在线主机',
    value: formatMetric(animatedMetrics.onlineHosts),
    unit: '台',
    note: `在线率 ${summary.value.onlineRate.toFixed(1)}%`,
    icon: CircleCheckFilled,
    tone: 'tone-success'
  },
  {
    key: 'abnormalHosts',
    label: '告警/离线',
    value: formatMetric(animatedMetrics.abnormalHosts),
    unit: '台',
    note: summary.value.abnormalHosts > 0 ? '' : '当前未发现告警或离线节点',
    details: [
      { label: '告警', value: `${summary.value.warningHosts} 台`, tone: 'warning' },
      { label: '离线', value: `${summary.value.offlineHosts} 台`, tone: 'danger' }
    ],
    icon: DataAnalysis,
    tone: 'tone-alert'
  },
  {
    key: 'avgRtt',
    label: '平均延迟',
    value: formatMetric(animatedMetrics.avgRtt, 1),
    unit: 'ms',
    note: '取过去 24 小时全局平均 RTT',
    icon: Timer,
    tone: 'tone-warning'
  },
  {
    key: 'recentAlerts',
    label: '近 1H 告警',
    value: formatMetric(animatedMetrics.recentAlerts),
    unit: '条',
    note: '实时滚动展示最新告警事件',
    icon: Bell,
    tone: 'tone-accent'
  }
])

const trendSummary = computed(() => {
  const points = databoardStats.value.trend_data?.length || 0
  if (points) {
    return liveTrendPoints.value.length ? `${points} 个历史点 + 实时尾迹` : `${points} 个采样点`
  }

  return liveTrendPoints.value.length ? `实时采样 ${liveTrendPoints.value.length} 点` : '等待趋势样本'
})

const lastUpdatedLabel = computed(() => {
  if (!lastUpdatedAt.value) {
    return '等待首轮同步'
  }
  return formatFullTime(lastUpdatedAt.value)
})

const goToAdmin = () => {
  router.push('/admin/login')
}

const setMobileTab = async (tab) => {
  activeMobileTab.value = tab
  await nextTick()

  screenShellRef.value?.scrollTo?.({ top: 0, behavior: 'smooth' })
  window.setTimeout(() => {
    trendChartInstance?.resize()
    mapChartInstance?.resize()
    ispChartInstance?.resize()
  }, 320)
}

const syncFullscreenState = () => {
  if (typeof document === 'undefined') {
    return
  }

  isFullscreen.value = Boolean(document.fullscreenElement)
}

const toggleFullscreen = async () => {
  if (typeof document === 'undefined') {
    return
  }

  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
      return
    }

    const target = screenShellRef.value || document.documentElement
    await target.requestFullscreen?.()
  } catch (error) {
    console.error('切换全屏失败:', error)
  }
}

const syncMapViewQuery = (view) => {
  if (typeof window === 'undefined') {
    return
  }

  const url = new URL(window.location.href)
  if (view === 'world') {
    url.searchParams.set('mapView', 'world')
  } else {
    url.searchParams.delete('mapView')
  }

  window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`)
}

const setMapView = async (view) => {
  if (currentMapView.value === view) {
    return
  }

  currentMapView.value = view
  syncMapViewQuery(view)
  clearPinnedMapTooltip()
  await nextTick()
  renderMapChart()
}

const normalizeScreenConfig = (payload = {}) => ({
  brand_name: normalizeLocation(payload.brand_name, defaultScreenConfig.brand_name),
  refresh_interval: clamp(Number(payload.refresh_interval) || defaultScreenConfig.refresh_interval, 1, 60),
  enable_3d: payload.enable_3d ?? defaultScreenConfig.enable_3d,
  enable_animation: payload.enable_animation ?? defaultScreenConfig.enable_animation,
  map_view_angle: clamp(Number(payload.map_view_angle) || defaultScreenConfig.map_view_angle, 0, 90),
  particle_count: clamp(Number(payload.particle_count) || defaultScreenConfig.particle_count, 0, 1000),
  show_flow_lines: payload.show_flow_lines ?? defaultScreenConfig.show_flow_lines,
  theme_color: payload.theme_color || defaultScreenConfig.theme_color
})

const applyScreenConfig = (payload = {}) => {
  Object.assign(screenConfig, normalizeScreenConfig(payload))
}

const updateClock = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const loadChinaMap = async () => {
  if (!chinaMapPromise) {
    chinaMapPromise = fetch('/china-full.json')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`地图资源加载失败: ${response.status}`)
        }
        return response.json()
      })
      .then((geoJson) => {
        echarts.registerMap(CHINA_MAP_NAME, geoJson)
        const centerEntries = []
        const featureEntries = []

        ;(geoJson.features || []).forEach((feature) => {
          const props = feature.properties || {}
          const center = props.centroid || props.center
          if (!props.name) {
            return
          }

          if (Array.isArray(center)) {
            centerEntries.push([props.name, center])
          }
          featureEntries.push([normalizeProvince(props.name), feature])
        })

        provinceCenters.value = new Map(centerEntries)
        provinceFeatureIndex.value = new Map(featureEntries)
      })
  }

  return chinaMapPromise
}

const loadWorldMap = async () => {
  if (!worldMapPromise) {
    worldMapPromise = fetch('/world.json')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`地图资源加载失败: ${response.status}`)
        }
        return response.json()
      })
      .then((geoJson) => {
        echarts.registerMap(WORLD_MAP_NAME, geoJson)
        worldRegionNames.value = Array.from(
          new Set(
            (geoJson.features || [])
              .map((feature) => feature?.properties?.name)
              .filter(Boolean)
          )
        )
      })
  }

  return worldMapPromise
}

const fetchScreenData = async () => {
  if (loading.value) {
    return
  }

  loading.value = true
  try {
    const screenDataRequest = isPreviewMode.value ? api.getDataScreenPreview() : api.getPublicDataScreen()
    const alertDataRequest = isPreviewMode.value ? api.getAlerts(24, 1, 12) : api.getPublicAlerts(24, 12)
    const [screenData, alertData, trendData] = await Promise.all([
      screenDataRequest,
      alertDataRequest,
      api.getDataBoardStats('1d', 'avg_rtt', 'desc')
    ])

    datascreenPayload.value = {
      total_hosts: screenData.total_hosts || 0,
      enabled_hosts: screenData.enabled_hosts || 0,
      recent_alerts: screenData.recent_alerts || 0,
      host_status: screenData.host_status || [],
      control_center: screenData.control_center || null,
      screen_config: screenData.screen_config || { ...defaultScreenConfig }
    }
    databoardStats.value = {
      total_hosts: trendData.total_hosts || 0,
      avg_online_rate: Number(trendData.avg_online_rate) || 0,
      avg_rtt: Number(trendData.avg_rtt) || 0,
      avg_packet_loss: Number(trendData.avg_packet_loss) || 0,
      host_stats: trendData.host_stats || [],
      trend_data: trendData.trend_data || []
    }
    alerts.value = alertData.items || []
    applyScreenConfig(screenData.screen_config)
    lastUpdatedAt.value = new Date()
    appendLiveTrendPoint()
    animateMetrics()
    resetRefreshTimer()
    resetAlertTicker()
    await renderCharts()
  } catch (error) {
    console.error('加载可视化大屏数据失败:', error)
    if (!isPreviewMode.value && error?.response?.status === 403) {
      router.replace('/login')
    }
  } finally {
    loading.value = false
  }
}

const appendLiveTrendPoint = () => {
  if (!summary.value.totalHosts) {
    return
  }

  const now = new Date()
  const point = {
    time: now.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }),
    avg_packet_loss: Number(average(hosts.value.map((host) => Number(host.packet_loss) || 0)).toFixed(2)),
    avg_rtt: Number(summary.value.avgRtt.toFixed(2)),
    online_rate: Number(summary.value.onlineRate.toFixed(2)),
    source: 'live'
  }
  const latestPoint = liveTrendPoints.value.at(-1)

  if (latestPoint?.time === point.time) {
    liveTrendPoints.value = [...liveTrendPoints.value.slice(0, -1), point]
    return
  }

  liveTrendPoints.value = [...liveTrendPoints.value, point].slice(-LIVE_TREND_POINT_LIMIT)
}

const animateMetrics = () => {
  const targets = {
    totalHosts: summary.value.totalHosts,
    onlineHosts: summary.value.onlineHosts,
    abnormalHosts: summary.value.abnormalHosts,
    avgRtt: Number(summary.value.avgRtt.toFixed(1)),
    recentAlerts: summary.value.recentAlerts
  }

  Object.entries(targets).forEach(([key, target]) => {
    tweenMetric(key, target)
  })
}

const tweenMetric = (key, target) => {
  if (metricFrames.has(key)) {
    cancelAnimationFrame(metricFrames.get(key))
  }

  const startValue = Number(animatedMetrics[key]) || 0
  const duration = 900
  const startTime = performance.now()

  const step = (now) => {
    const progress = clamp((now - startTime) / duration, 0, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedMetrics[key] = startValue + (target - startValue) * eased

    if (progress < 1) {
      metricFrames.set(key, requestAnimationFrame(step))
    } else {
      animatedMetrics[key] = target
      metricFrames.delete(key)
    }
  }

  metricFrames.set(key, requestAnimationFrame(step))
}

const resetRefreshTimer = () => {
  clearInterval(refreshTimer)
  refreshTimer = setInterval(() => {
    fetchScreenData()
  }, screenConfig.refresh_interval * 1000)
}

const resetAlertTicker = () => {
  clearInterval(alertTickerTimer)
  alertCursor.value = 0

  if (alerts.value.length > VISIBLE_ALERT_COUNT) {
    alertTickerTimer = setInterval(() => {
      alertCursor.value = (alertCursor.value + 1) % alerts.value.length
    }, 3200)
  }
}

const initCharts = () => {
  if (trendChartRef.value && !trendChartInstance) {
    trendChartInstance = echarts.init(trendChartRef.value)
  }
  if (mapChartRef.value && !mapChartInstance) {
    mapChartInstance = echarts.init(mapChartRef.value)
  }
  if (ispChartRef.value && !ispChartInstance) {
    ispChartInstance = echarts.init(ispChartRef.value)
  }
}

const renderCharts = async () => {
  await nextTick()
  initCharts()
  await Promise.all([loadChinaMap(), loadWorldMap()])
  renderTrendChart()
  renderMapChart()
  renderIspChart()
}

const renderTrendChart = () => {
  if (!trendChartInstance) {
    return
  }

  const trendData = trendChartData.value
  const latestTrendPoint = trendData.at(-1)
  const hasHistoricalTrend = Boolean(databoardStats.value.trend_data?.length)
  const isLiveFallback = !hasHistoricalTrend && trendData.length > 0
  const showLiveSymbols = isLiveFallback || trendData.length <= 2

  trendChartInstance.setOption(
    {
      animationDuration: 800,
      animationDurationUpdate: 900,
      animationEasingUpdate: 'cubicOut',
      backgroundColor: 'transparent',
      grid: {
        top: 54,
        right: 18,
        bottom: 26,
        left: 42
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(5, 16, 34, 0.95)',
        borderColor: palette.value.border,
        textStyle: {
          color: palette.value.text
        }
      },
      legend: {
        top: 1,
        right: 2,
        data: ['平均延迟', '平均在线率'],
        itemWidth: 10,
        itemHeight: 10,
        textStyle: {
          color: palette.value.muted,
          fontSize: 11
        }
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: trendData.map((item) => item.time),
        axisLine: {
          lineStyle: {
            color: 'rgba(137, 167, 199, 0.26)'
          }
        },
        axisLabel: {
          color: palette.value.muted,
          fontSize: 11
        }
      },
      yAxis: [
        {
          type: 'value',
          name: 'RTT',
          axisLine: { show: false },
          splitLine: {
            lineStyle: {
              color: 'rgba(137, 167, 199, 0.12)',
              type: 'dashed'
            }
          },
          axisLabel: {
            color: palette.value.muted,
            formatter: '{value}ms'
          }
        },
        {
          type: 'value',
          name: '在线率',
          min: 0,
          max: 100,
          axisLine: { show: false },
          splitLine: { show: false },
          axisLabel: {
            color: palette.value.muted,
            formatter: '{value}%'
          }
        }
      ],
      series: [
        {
          name: '平均延迟',
          type: 'line',
          smooth: true,
          showSymbol: showLiveSymbols,
          symbol: 'circle',
          symbolSize: 6,
          data: trendData.map((item) => Number(item.avg_rtt) || 0),
          lineStyle: {
            width: 3,
            color: palette.value.accent
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: `${palette.value.accent}AA` },
              { offset: 1, color: 'rgba(12, 24, 46, 0.05)' }
            ])
          }
        },
        {
          name: '平均在线率',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          showSymbol: showLiveSymbols,
          symbol: 'circle',
          symbolSize: 5,
          data: trendData.map((item) => Number(item.online_rate) || 0),
          lineStyle: {
            width: 2,
            type: 'dashed',
            color: palette.value.success
          }
        },
        {
          name: '实时延迟点',
          type: 'effectScatter',
          coordinateSystem: 'cartesian2d',
          tooltip: { show: false },
          rippleEffect: {
            scale: 3.2,
            brushType: 'stroke'
          },
          symbolSize: 9,
          z: 8,
          data: latestTrendPoint ? [[latestTrendPoint.time, Number(latestTrendPoint.avg_rtt) || 0]] : [],
          itemStyle: {
            color: palette.value.accent,
            shadowBlur: 16,
            shadowColor: `${palette.value.accent}99`
          }
        },
        {
          name: '实时在线率点',
          type: 'effectScatter',
          coordinateSystem: 'cartesian2d',
          yAxisIndex: 1,
          tooltip: { show: false },
          rippleEffect: {
            scale: 2.8,
            brushType: 'stroke'
          },
          symbolSize: 7,
          z: 8,
          data: latestTrendPoint ? [[latestTrendPoint.time, Number(latestTrendPoint.online_rate) || 0]] : [],
          itemStyle: {
            color: palette.value.success,
            shadowBlur: 12,
            shadowColor: `${palette.value.success}77`
          }
        }
      ]
    },
    true
  )
}

const renderMapChart = () => {
  if (!mapChartInstance) {
    return
  }

  clearPinnedMapTooltip(true)

  const isChinaView = currentMapView.value === 'china'
  const activeRoamState = mapRoamState[currentMapView.value]
  const activeMapName = isChinaView ? CHINA_MAP_NAME : WORLD_MAP_NAME
  const activeGeoCenter = isChinaView ? ['48.8%', '60%'] : ['50%', '54%']
  const activeLayoutSize = isChinaView ? '154%' : '124%'
  const controlCenterValue = controlCenterCoords.value
  const roamScaleLimit = isChinaView ? { min: 1, max: 4.6 } : { min: 0.85, max: 6 }
  const roamOption = {
    zoom: Number(activeRoamState?.zoom) || 1,
    scaleLimit: roamScaleLimit,
    ...(Array.isArray(activeRoamState?.center) ? { center: activeRoamState.center } : {})
  }
  const provinceValues = isChinaView ? provinceMapSeriesData.value : worldMapSeriesData.value
  const activeClusters = isChinaView ? domesticMapPointClusters.value : mapPointClusters.value
  const domesticPoints = isChinaView ? activeClusters : domesticMapPointClusters.value
  const overseasPoints = isChinaView ? [] : overseasMapPointClusters.value
  const abnormalPoints = activeClusters.filter((point) => point.tone === 'abnormal')
  const warningPoints = activeClusters.filter((point) => point.tone === 'warning')
  const normalPoints = activeClusters.filter((point) => point.tone === 'normal')

  const flowSources = isChinaView
    ? [...abnormalPoints, ...warningPoints, ...normalPoints].slice(0, 36)
    : dedupeClustersById([
        ...overseasPoints,
        ...domesticPoints.filter((point) => point.tone === 'abnormal'),
        ...domesticPoints.filter((point) => point.tone === 'warning'),
        ...domesticPoints
      ]).slice(0, 18)
  const flowLines = screenConfig.show_flow_lines && Array.isArray(controlCenterValue)
    ? flowSources.map((point) => ({
        coords: [controlCenterValue, point.value.slice(0, 2)]
      }))
    : []
  const overseasLabelPoints = !isChinaView
    ? overseasPoints.map((point) => ({
        ...point,
        labelName: point.country || point.city || point.name
      }))
    : []

  mapChartInstance.setOption(
    {
      backgroundColor: 'transparent',
      animationDuration: 900,
      animationDurationUpdate: 1000,
      tooltip: {
        trigger: 'item',
        triggerOn: mapTooltipTriggerOn.value,
        enterable: !isTouchLikeDevice.value,
        confine: true,
        appendToBody: true,
        alwaysShowContent: false,
        hideDelay: isTouchLikeDevice.value ? 0 : 140,
        transitionDuration: 0.12,
        padding: 0,
        borderWidth: 1,
        backgroundColor: 'rgba(5, 16, 34, 0.96)',
        borderColor: palette.value.border,
        extraCssText: isTouchLikeDevice.value
          ? 'box-shadow: 0 18px 42px rgba(0, 0, 0, 0.42); border-radius: 14px; max-width: min(320px, calc(100vw - 24px)); overflow: hidden;'
          : 'box-shadow: 0 18px 48px rgba(0, 0, 0, 0.38); border-radius: 18px; max-width: 360px; overflow: hidden;',
        textStyle: {
          color: palette.value.text
        },
        position: getTooltipPosition,
        formatter: (params) => {
          if (isPinnedProvinceTooltip(params)) {
            return buildProvinceTooltip({
              ...params,
              name: params.data?.name || params.name,
              data: params.data
            })
          }

          if (params.data?.tooltipType === 'control-center') {
            return ''
          }

          if (params.seriesType === 'map') {
            return ''
          }

          if (params.seriesType === 'lines') {
            return ''
          }

          return hasHostPointTooltip(params) ? buildPointTooltip(params) : ''
        }
      },
      geo: {
        map: activeMapName,
        roam: true,
        silent: false,
        layoutCenter: activeGeoCenter,
        layoutSize: activeLayoutSize,
        regions: isChinaView ? getSelectedProvinceRegions() : [],
        ...roamOption,
        itemStyle: {
          areaColor: isChinaView ? 'rgba(7, 20, 41, 0.26)' : 'rgba(11, 24, 44, 0.22)',
          borderColor: isChinaView ? 'rgba(98, 173, 255, 0.18)' : 'rgba(92, 156, 255, 0.18)',
          borderWidth: isChinaView ? 0.85 : 0.55
        },
        emphasis: {
          disabled: true
        }
      },
      series: [
        {
          type: 'map',
          map: activeMapName,
          coordinateSystem: 'geo',
          geoIndex: 0,
          silent: true,
          zlevel: 0,
          itemStyle: {
            areaColor: isChinaView ? 'rgba(6, 18, 36, 0.96)' : 'rgba(10, 28, 52, 0.92)',
            borderColor: isChinaView ? 'rgba(94, 168, 255, 0.3)' : 'rgba(102, 171, 255, 0.3)',
            borderWidth: isChinaView ? 1.05 : 0.95,
            shadowBlur: isChinaView ? 28 : 14,
            shadowColor: isChinaView ? 'rgba(7, 24, 48, 0.96)' : 'rgba(8, 22, 44, 0.82)'
          },
          emphasis: {
            disabled: true
          },
          data: provinceValues
        },
        {
          type: 'map',
          map: activeMapName,
          coordinateSystem: 'geo',
          geoIndex: 0,
          silent: !isChinaView,
          selectedMode: false,
          zlevel: 1,
          regions: isChinaView ? getSelectedProvinceRegions() : [],
          label: {
            show: false
          },
          itemStyle: {
            areaColor: isChinaView ? 'rgba(10, 29, 54, 0.92)' : 'rgba(14, 34, 61, 0.82)',
            borderColor: isChinaView ? 'rgba(136, 208, 255, 0.54)' : 'rgba(145, 206, 255, 0.34)',
            borderWidth: isChinaView ? 1.28 : 1.02,
            shadowBlur: isChinaView ? 14 : 12,
            shadowColor: isChinaView ? 'rgba(30, 144, 255, 0.18)' : 'rgba(56, 137, 255, 0.16)'
          },
          emphasis: {
            itemStyle: {
              areaColor: isChinaView ? undefined : 'rgba(18, 45, 84, 0.92)',
              borderColor: isChinaView ? undefined : 'rgba(186, 230, 255, 0.48)',
              borderWidth: isChinaView ? 1.62 : 1.28,
              shadowBlur: isChinaView ? 22 : 18
            },
            label: {
              show: false
            }
          },
          data: provinceValues
        },
        {
          type: 'scatter',
          coordinateSystem: 'geo',
          silent: true,
          zlevel: 2,
          symbolSize: 1,
          data: isChinaView ? provinceLabelPoints.value : [],
          itemStyle: {
            color: 'rgba(0, 0, 0, 0)'
          },
          label: {
            show: isChinaView,
            position: 'inside',
            color: 'rgba(228, 240, 255, 0.94)',
            fontSize: 11,
            fontWeight: 600,
            textBorderColor: 'rgba(3, 12, 24, 0.96)',
            textBorderWidth: 2,
            formatter: (params) => params.data.labelName
          },
          labelLayout: {
            hideOverlap: true
          }
        },
        {
          type: 'lines',
          coordinateSystem: 'geo',
          zlevel: 2,
          silent: true,
          data: isChinaView ? crowdedProvinceCalloutLines.value : [],
          lineStyle: {
            width: 1.1,
            opacity: 0.82,
            curveness: 0.08
          }
        },
        {
          type: 'effectScatter',
          coordinateSystem: 'geo',
          zlevel: 2,
          silent: true,
          data: isChinaView ? crowdedProvinceAnchorPoints.value : [],
          symbolSize: 5,
          rippleEffect: {
            scale: 2.6,
            brushType: 'stroke'
          },
          itemStyle: {
            color: (params) => getProvinceCalloutColor(params.data?.tone),
            shadowBlur: 12,
            shadowColor: 'rgba(123, 199, 255, 0.48)'
          }
        },
        {
          type: 'scatter',
          coordinateSystem: 'geo',
          zlevel: 3,
          data: isChinaView ? crowdedProvinceCallouts.value : [],
          symbolSize: 6,
          itemStyle: {
            color: (params) => getProvinceCalloutColor(params.data?.tone),
            borderWidth: 1.2,
            borderColor: 'rgba(255, 255, 255, 0.72)',
            shadowBlur: 10,
            shadowColor: 'rgba(6, 18, 36, 0.5)'
          },
          label: {
            show: isChinaView,
            position: 'right',
            distance: 8,
            color: (params) => getProvinceLabelColor(params.data?.tone),
            fontSize: 11,
            fontWeight: 700,
            padding: [5, 10],
            backgroundColor: 'rgba(6, 18, 36, 0.82)',
            borderRadius: 999,
            borderColor: 'rgba(123, 199, 255, 0.3)',
            borderWidth: 1,
            formatter: (params) => params.data.labelName
          }
        },
        {
          type: 'lines',
          coordinateSystem: 'geo',
          zlevel: 3,
          effect: {
            show: screenConfig.enable_animation && screenConfig.show_flow_lines,
            constantSpeed: isChinaView ? 35 : 30,
            trailLength: isChinaView ? 0.2 : 0.14,
            symbolSize: isChinaView ? 3 : 2.4
          },
          lineStyle: {
            color: palette.value.flow,
            width: isChinaView ? 1 : 0.9,
            opacity: isChinaView ? 0.24 : 0.18,
            curveness: isChinaView ? 0.16 : 0.1
          },
          data: flowLines
        },
        {
          type: 'effectScatter',
          coordinateSystem: 'geo',
          zlevel: 4,
          data: normalPoints,
          symbolSize: (value, params) => getClusterSymbolSize(params?.data, 0, currentMapView.value),
          showEffectOn: 'render',
          rippleEffect: {
            scale: isChinaView ? 3.8 : 3,
            brushType: 'stroke'
          },
          label: {
            show: false,
            position: 'top',
            distance: 4,
            color: 'rgba(214, 232, 255, 0.76)',
            fontSize: 9,
            formatter: (params) => params.data.hostCount > 2 ? `${params.data.hostCount}台` : ''
          },
          itemStyle: {
            color: palette.value.success,
            shadowBlur: 14,
            shadowColor: `${palette.value.success}88`
          }
        },
        {
          type: 'effectScatter',
          coordinateSystem: 'geo',
          zlevel: 5,
          data: warningPoints,
          symbolSize: (value, params) => getClusterSymbolSize(params?.data, 2, currentMapView.value),
          rippleEffect: {
            scale: isChinaView ? 4.3 : 3.5,
            brushType: 'stroke'
          },
          label: {
            show: false,
            position: 'top',
            distance: 4,
            color: palette.value.warning,
            fontSize: 9,
            fontWeight: 600,
            formatter: (params) => params.data.hostCount > 1 ? `${params.data.hostCount}台` : ''
          },
          itemStyle: {
            color: palette.value.warning,
            shadowBlur: 16,
            shadowColor: `${palette.value.warning}88`
          }
        },
        {
          type: 'effectScatter',
          coordinateSystem: 'geo',
          zlevel: 6,
          data: abnormalPoints,
          symbolSize: (value, params) => getClusterSymbolSize(params?.data, 4, currentMapView.value),
          rippleEffect: {
            scale: isChinaView ? 4.8 : 4,
            brushType: 'stroke'
          },
          label: {
            show: false,
            position: 'top',
            distance: 5,
            color: palette.value.text,
            fontWeight: 'bold',
            fontSize: 10,
            formatter: (params) => params.data.hostCount > 0 ? `${params.data.hostCount}台` : ''
          },
          itemStyle: {
            color: palette.value.danger,
            shadowBlur: 18,
            shadowColor: `${palette.value.danger}AA`
          }
        },
        {
          type: 'scatter',
          coordinateSystem: 'geo',
          zlevel: 6,
          silent: true,
          symbolSize: 1,
          data: overseasLabelPoints,
          itemStyle: {
            color: 'rgba(0, 0, 0, 0)'
          },
          label: {
            show: !isChinaView,
            position: 'right',
            distance: 10,
            color: 'rgba(231, 241, 255, 0.94)',
            fontSize: 11,
            fontWeight: 600,
            padding: [4, 8],
            backgroundColor: 'rgba(6, 18, 36, 0.74)',
            borderRadius: 999,
            borderColor: 'rgba(123, 199, 255, 0.26)',
            borderWidth: 1,
            formatter: (params) => params.data.labelName
          }
        },
        {
          type: 'scatter',
          coordinateSystem: 'geo',
          zlevel: 7,
          symbol: 'diamond',
          symbolSize: isChinaView ? 12 : 10,
          itemStyle: {
            color: palette.value.accent,
            shadowBlur: 12,
            shadowColor: `${palette.value.accent}88`
          },
          label: {
            show: false,
            position: 'right',
            color: palette.value.text,
            fontSize: isChinaView ? 12 : 11,
            formatter: isChinaView ? `${controlCenterLabel.value}` : `${controlCenterLabel.value}`
          },
          data: Array.isArray(controlCenterValue)
            ? [
                {
                  name: '监控中心',
                  value: [...controlCenterValue, 1],
                  tooltipType: 'control-center'
                }
              ]
            : []
        }
      ]
    },
    true
  )

  bindMapChartInteractions()
}

const renderIspChart = () => {
  if (!ispChartInstance) {
    return
  }

  const data = ispDistribution.value.length
    ? ispDistribution.value
    : [{ name: '暂无数据', value: 1 }]
  const chartRect = ispChartRef.value?.getBoundingClientRect?.()
  const chartWidth = chartRect?.width || 260
  const chartHeight = chartRect?.height || 196
  const chartCenterYPercent = chartHeight < 170 ? 45 : 43
  const centerX = chartWidth / 2
  const centerY = chartHeight * (chartCenterYPercent / 100)

  ispChartInstance.setOption(
    {
      animationDuration: 800,
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(5, 16, 34, 0.96)',
        borderColor: palette.value.border,
        textStyle: {
          color: palette.value.text
        }
      },
      legend: {
        show: false,
        bottom: 0,
        itemWidth: 9,
        itemHeight: 9,
        itemGap: 8,
        textStyle: {
          color: palette.value.muted,
          fontSize: 10
        }
      },
      series: [
        {
          type: 'pie',
          left: 4,
          right: 4,
          top: 4,
          bottom: 28,
          radius: ['45%', '62%'],
          center: ['50%', `${chartCenterYPercent}%`],
          startAngle: 94,
          avoidLabelOverlap: true,
          minAngle: 1,
          minShowLabelAngle: 1.8,
          itemStyle: {
            borderColor: 'rgba(3, 10, 22, 0.9)',
            borderWidth: 3
          },
          label: {
            show: true,
            position: 'outside',
            alignTo: 'edge',
            edgeDistance: 12,
            bleedMargin: 4,
            distanceToLabelLine: 7,
            color: palette.value.text,
            fontSize: 10,
            lineHeight: 14,
            formatter: (params) => {
              const percent = Number(params.percent) || 0
              return percent >= 2 ? `${params.name}\n${percent.toFixed(1)}%` : ''
            }
          },
          labelLayout: {
            hideOverlap: false,
            moveOverlap: 'shiftY'
          },
          labelLine: {
            show: true,
            length: 13,
            length2: 22,
            smooth: 0.16,
            maxSurfaceAngle: 80,
            lineStyle: {
              color: palette.value.muted,
              width: 1
            }
          },
          data,
          color: [
            palette.value.accent,
            palette.value.success,
            palette.value.warning,
            palette.value.danger,
            '#8EC5FF',
            '#5B8CFF'
          ]
        }
      ],
      graphic: [
        {
          type: 'text',
          x: centerX,
          y: centerY - 23,
          silent: true,
          z: 10,
          style: {
            text: '运营商',
            fill: palette.value.muted,
            fontSize: 10,
            fontWeight: 600,
            textAlign: 'center',
            textVerticalAlign: 'middle'
          }
        },
        {
          type: 'text',
          x: centerX,
          y: centerY,
          silent: true,
          z: 10,
          style: {
            text: `${hosts.value.length}台`,
            fill: palette.value.text,
            fontSize: 22,
            fontWeight: 700,
            textAlign: 'center',
            textVerticalAlign: 'middle'
          }
        }
      ]
    },
    true
  )
}

const getProvinceTone = (entry) => {
  if (!entry?.hosts?.length) {
    return 'idle'
  }

  if ((entry.abnormalCount || 0) > 0) {
    return 'abnormal'
  }

  if ((entry.warningCount || 0) > 0 || Number(entry.avgRtt || 0) >= WARNING_RTT_THRESHOLD) {
    return 'warning'
  }

  return 'normal'
}

const getProvinceAreaStyle = (tone, hostCount = 0, highlighted = false, crowdedRegion = false) => {
  const intensity = clamp(0.18 + hostCount * 0.022 + (highlighted ? 0.1 : 0), 0.22, 0.5)
  const borderBoost = crowdedRegion ? 0.22 : 0
  const shadowBoost = crowdedRegion ? 4 : 0

  if (tone === 'abnormal') {
    return {
      areaColor: `rgba(255, 77, 79, ${intensity.toFixed(2)})`,
      borderColor: highlighted ? 'rgba(255, 160, 162, 0.96)' : 'rgba(255, 124, 128, 0.82)',
      borderWidth: (highlighted ? 1.7 : 1.25) + borderBoost,
      shadowBlur: (highlighted ? 22 : 14) + shadowBoost,
      shadowColor: 'rgba(255, 77, 79, 0.36)'
    }
  }

  if (tone === 'warning') {
    return {
      areaColor: `rgba(250, 219, 20, ${Math.min(intensity + 0.04, 0.48).toFixed(2)})`,
      borderColor: highlighted ? 'rgba(255, 238, 138, 0.96)' : 'rgba(250, 219, 20, 0.84)',
      borderWidth: (highlighted ? 1.6 : 1.2) + borderBoost,
      shadowBlur: (highlighted ? 20 : 12) + shadowBoost,
      shadowColor: 'rgba(250, 219, 20, 0.3)'
    }
  }

  if (tone === 'normal') {
    return {
      areaColor: `rgba(0, 255, 195, ${Math.min(intensity + 0.02, 0.42).toFixed(2)})`,
      borderColor: highlighted ? 'rgba(160, 255, 234, 0.96)' : 'rgba(0, 255, 195, 0.8)',
      borderWidth: (highlighted ? 1.5 : 1.15) + borderBoost,
      shadowBlur: (highlighted ? 18 : 10) + shadowBoost,
      shadowColor: 'rgba(0, 255, 195, 0.24)'
    }
  }

  return {
    areaColor: palette.value.map,
    borderColor: 'rgba(123, 199, 255, 0.34)',
    borderWidth: (highlighted ? 1.35 : 1.05) + borderBoost,
    shadowBlur: (highlighted ? 16 : 8) + shadowBoost,
    shadowColor: 'rgba(30, 144, 255, 0.1)'
  }
}

const getProvinceLabelColor = (tone) => {
  if (tone === 'abnormal') {
    return '#FFE4E5'
  }
  if (tone === 'warning') {
    return '#FFF5C0'
  }
  if (tone === 'normal') {
    return '#D9FFF5'
  }
  return 'rgba(228, 240, 255, 0.95)'
}

const getProvinceCalloutColor = (tone) => {
  if (tone === 'abnormal') {
    return 'rgba(255, 124, 128, 0.92)'
  }
  if (tone === 'warning') {
    return 'rgba(250, 219, 20, 0.92)'
  }
  if (tone === 'normal') {
    return 'rgba(0, 255, 195, 0.88)'
  }
  return 'rgba(123, 199, 255, 0.86)'
}

const getToneMeta = (tone) => {
  if (tone === 'abnormal') {
    return {
      label: '异常/离线',
      badgeStyle: 'background: rgba(255, 77, 79, 0.18); color: #ffd7d8; border: 1px solid rgba(255, 77, 79, 0.35);'
    }
  }
  if (tone === 'warning') {
    return {
      label: '告警/高延迟',
      badgeStyle: 'background: rgba(250, 219, 20, 0.14); color: #fff0a6; border: 1px solid rgba(250, 219, 20, 0.3);'
    }
  }
  if (tone === 'normal') {
    return {
      label: '在线',
      badgeStyle: 'background: rgba(0, 255, 195, 0.14); color: #d6fff4; border: 1px solid rgba(0, 255, 195, 0.28);'
    }
  }
  return {
    label: '无节点',
    badgeStyle: 'background: rgba(123, 199, 255, 0.12); color: #d9e9ff; border: 1px solid rgba(123, 199, 255, 0.24);'
  }
}

const escapeHtml = (value) =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')

const shortenIspName = (value, maxLength = 10) => {
  const source = normalizeLocation(value, '未知运营商')
  const headLength = Math.max(4, maxLength - 2)
  return source.length > maxLength ? `${source.slice(0, headLength)}…` : source
}

const renderTooltipCard = ({ title, tone, stats = [], hosts = [], sectionTitle = '主机列表', emptyText = '暂无主机数据' }) => {
  const toneMeta = getToneMeta(tone)

  const statRows = stats
    .map(
      (item) => `
        <div style="padding: 8px 10px; border-radius: 12px; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.04); min-width: 0;">
          <div style="font-size: 11px; color: #89A7C7; margin-bottom: 4px;">${escapeHtml(item.label)}</div>
          <div style="font-size: 14px; color: #EAF4FF; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(item.value)}</div>
        </div>
      `
    )
    .join('')

  const hostRows = hosts.length
    ? hosts
        .map((host) => {
          const toneKey = getHostTone(host)
          const hostTone = getToneMeta(toneKey)
          const hostDetail = getHostStatusText(host)
          const location = [host.city, host.address].filter(Boolean).join(' · ')

          return `
            <div style="display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 10px; align-items: start; padding: 9px 10px; border-radius: 12px; background: rgba(255, 255, 255, 0.035); border: 1px solid rgba(255, 255, 255, 0.04);">
              <span style="width: 8px; height: 8px; border-radius: 999px; margin-top: 6px; ${hostTone.badgeStyle}"></span>
              <div style="min-width: 0;">
                <div style="font-size: 13px; color: #EAF4FF; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(host.name || '未命名主机')}</div>
                <div style="margin-top: 4px; font-size: 11px; color: #89A7C7; line-height: 1.45; word-break: break-all;">${escapeHtml(location || '位置未知')}</div>
              </div>
              <div style="font-size: 11px; color: #EAF4FF; white-space: nowrap;">${escapeHtml(hostDetail)}</div>
            </div>
          `
        })
        .join('')
    : `<div style="padding: 12px 10px; border-radius: 12px; background: rgba(255, 255, 255, 0.03); color: #89A7C7; font-size: 12px;">${escapeHtml(emptyText)}</div>`
  const cardWidth = isTouchLikeDevice.value ? 'min(296px, calc(100vw - 48px))' : '340px'
  const hostListMaxHeight = isTouchLikeDevice.value ? '160px' : '220px'

  return `
    <div style="width: ${cardWidth}; max-width: ${cardWidth}; padding: ${isTouchLikeDevice.value ? '12px' : '14px'};">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
        <strong style="font-size: 16px; color: #EAF4FF; line-height: 1.3;">${escapeHtml(title)}</strong>
        <span style="flex: 0 0 auto; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; ${toneMeta.badgeStyle}">${toneMeta.label}</span>
      </div>
      <div style="margin-top: 8px; font-size: 11px; color: #89A7C7;">${isTouchLikeDevice.value ? '点击点位或省份查看详情，点击空白关闭。' : '悬停查看，点击可固定，列表支持滚动。'}</div>
      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 12px;">
        ${statRows}
      </div>
      <div style="margin-top: 12px; margin-bottom: 8px; font-size: 11px; color: #9EC7FF; letter-spacing: 0.04em;">${escapeHtml(sectionTitle)}</div>
      <div style="display: grid; gap: 8px; max-height: ${hostListMaxHeight}; overflow: auto; padding-right: 4px;">
        ${hostRows}
      </div>
    </div>
  `
}

const getTooltipPosition = (point, params, dom, rect, size) => {
  const [x, y] = Array.isArray(point) ? point : [0, 0]
  const tooltipWidth = dom?.offsetWidth || 340
  const tooltipHeight = dom?.offsetHeight || 260
  const chartRect = mapChartRef.value?.getBoundingClientRect()
  const baseX = (chartRect?.left || 0) + x
  const baseY = (chartRect?.top || 0) + y
  const viewWidth = typeof window !== 'undefined' ? window.innerWidth : size?.viewSize?.[0] || 0
  const viewHeight = typeof window !== 'undefined' ? window.innerHeight : size?.viewSize?.[1] || 0

  if (isTouchLikeDevice.value) {
    const bottomSafeArea = 88
    const left = Math.max(12, Math.round((viewWidth - tooltipWidth) / 2))
    const preferredTop = baseY + tooltipHeight + bottomSafeArea + 12 > viewHeight
      ? baseY - tooltipHeight - 12
      : baseY + 12
    const top = clamp(preferredTop, 12, Math.max(12, viewHeight - tooltipHeight - bottomSafeArea))
    return [left, top]
  }

  const left = baseX + tooltipWidth + 18 > viewWidth ? Math.max(12, baseX - tooltipWidth - 18) : baseX + 18
  const top = baseY + tooltipHeight + 18 > viewHeight ? Math.max(12, baseY - tooltipHeight - 18) : baseY + 18

  return [left, top]
}

const getProvinceTooltipHosts = (params) => {
  if (!params) {
    return []
  }

  const provinceName = params.data?.name || params.name
  const provinceEntry = provinceHostIndex.value.get(normalizeProvince(provinceName))
  return provinceEntry?.hosts || params.data?.hosts || []
}

const isProvinceTooltipTarget = (params) => {
  if (!params || params.componentType !== 'series') {
    return false
  }

  return currentMapView.value === 'china' && (params.seriesType === 'map' || params.data?.tooltipType === 'province')
}

const isPinnedProvinceTooltip = (params) => {
  if (!pinnedMapTooltip || pinnedMapTooltip.kind !== 'province' || !isProvinceTooltipTarget(params)) {
    return false
  }

  const paramsProvinceName = params.data?.name || params.name
  const isSameProvince = pinnedMapTooltip.dataIndex != null
    ? pinnedMapTooltip.dataIndex === params.dataIndex
    : normalizeProvince(pinnedMapTooltip.name) === normalizeProvince(paramsProvinceName)

  return (
    pinnedMapTooltip.seriesIndex === params.seriesIndex &&
    isSameProvince &&
    getProvinceTooltipHosts(params).length > 0
  )
}

const hasHostPointTooltip = (params) => {
  const hostsAtPoint = params?.data?.hosts || []
  return params?.componentType === 'series' && params.data?.tooltipType !== 'province' && hostsAtPoint.length > 0
}

const resolveProvinceRegionName = (provinceName) => {
  const normalizedName = normalizeProvince(provinceName)
  if (!normalizedName) {
    return provinceName
  }

  const matchedRegion = Array.from(provinceCenters.value.keys()).find(
    (name) => normalizeProvince(name) === normalizedName
  )
  return matchedRegion || provinceName
}

const getSelectedProvinceRegions = () => {
  if (!selectedMapProvinceName) {
    return []
  }

  return [
    {
      name: resolveProvinceRegionName(selectedMapProvinceName),
      ...SELECTED_PROVINCE_REGION_STYLE
    }
  ]
}

const syncSelectedProvinceRegion = () => {
  if (!mapChartInstance) {
    return
  }

  const regions = getSelectedProvinceRegions()
  mapChartInstance.setOption(
    {
      geo: [
        {
          regions
        }
      ],
      series: [
        {},
        {
          regions
        }
      ]
    },
    false
  )
}

const syncPinnedMapTooltip = () => {
  if (!mapChartInstance) {
    return
  }

  mapChartInstance.setOption(
    {
      tooltip: {
        triggerOn: pinnedMapTooltip ? 'click' : mapTooltipTriggerOn.value,
        enterable: Boolean(pinnedMapTooltip) && !isTouchLikeDevice.value,
        alwaysShowContent: Boolean(pinnedMapTooltip),
        hideDelay: pinnedMapTooltip || isTouchLikeDevice.value ? 0 : 140
      }
    },
    false
  )

  if (pinnedMapTooltip) {
    mapChartInstance.dispatchAction({
      type: 'showTip',
      seriesIndex: pinnedMapTooltip.seriesIndex,
      ...(pinnedMapTooltip.dataIndex != null
        ? { dataIndex: pinnedMapTooltip.dataIndex }
        : { name: resolveProvinceRegionName(pinnedMapTooltip.name) }),
      position: pinnedMapTooltip.position
    })
  } else {
    mapChartInstance.dispatchAction({ type: 'hideTip' })
  }
}

const clearPinnedMapTooltip = (silent = false) => {
  const hadSelectedProvince = Boolean(selectedMapProvinceName)

  pinnedMapTooltip = null
  selectedMapProvinceName = null

  if (hadSelectedProvince) {
    syncSelectedProvinceRegion()
  }

  if (!silent) {
    syncPinnedMapTooltip()
  }
}

const bindMapChartInteractions = () => {
  if (!mapChartInstance) {
    return
  }

  if (mapClickHandler) {
    mapChartInstance.off('click', mapClickHandler)
  }

  if (mapBlankClickHandler) {
    mapChartInstance.getZr().off('click', mapBlankClickHandler)
  }

  if (mapRoamHandler) {
    mapChartInstance.off('georoam', mapRoamHandler)
  }

  mapClickHandler = (params) => {
    if (isProvinceTooltipTarget(params)) {
      const provinceHosts = getProvinceTooltipHosts(params)
      if (!provinceHosts.length) {
        clearPinnedMapTooltip()
        return
      }

      const provinceName = params.data?.name || params.name
      const nextTooltip = {
        kind: 'province',
        seriesIndex: params.seriesIndex,
        dataIndex: params.dataIndex,
        name: provinceName,
        position: [params.event?.offsetX || 0, params.event?.offsetY || 0]
      }

      if (
        pinnedMapTooltip?.kind === 'province' &&
        normalizeProvince(pinnedMapTooltip.name) === normalizeProvince(provinceName)
      ) {
        clearPinnedMapTooltip()
        return
      }

      selectedMapProvinceName = provinceName
      pinnedMapTooltip = nextTooltip
      syncSelectedProvinceRegion()
      syncPinnedMapTooltip()
      return
    }

    if (hasHostPointTooltip(params)) {
      const nextTooltip = {
        kind: 'host',
        seriesIndex: params.seriesIndex,
        dataIndex: params.dataIndex,
        position: [params.event?.offsetX || 0, params.event?.offsetY || 0]
      }

      if (
        pinnedMapTooltip?.kind === 'host' &&
        pinnedMapTooltip.seriesIndex === nextTooltip.seriesIndex &&
        pinnedMapTooltip.dataIndex === nextTooltip.dataIndex
      ) {
        clearPinnedMapTooltip()
        return
      }

      selectedMapProvinceName = null
      syncSelectedProvinceRegion()
      pinnedMapTooltip = nextTooltip
      syncPinnedMapTooltip()
      return
    }

    clearPinnedMapTooltip()
  }

  mapBlankClickHandler = (event) => {
    if (!event.target) {
      clearPinnedMapTooltip()
    }
  }

  mapRoamHandler = () => {
    clearPinnedMapTooltip(true)
    mapChartInstance?.dispatchAction({ type: 'hideTip' })

    const geoOption = mapChartInstance?.getOption()?.geo?.[0]
    if (!geoOption) {
      return
    }

    mapRoamState[currentMapView.value].zoom = Number(geoOption.zoom) || 1
    if (Array.isArray(geoOption.center) && geoOption.center.length === 2) {
      mapRoamState[currentMapView.value].center = geoOption.center.map((value) => Number(value))
    }
  }

  mapChartInstance.on('click', mapClickHandler)
  mapChartInstance.getZr().on('click', mapBlankClickHandler)
  mapChartInstance.on('georoam', mapRoamHandler)
}

const buildProvinceTooltip = (params) => {
  const provinceName = shortenProvinceName(params.name)
  const normalizedName = normalizeProvince(params.name)
  const provinceEntry = provinceHostIndex.value.get(normalizedName)
  const provinceHosts = provinceEntry?.hosts || params.data?.hosts || []
  const normalCount = provinceEntry?.normalCount ?? params.data?.normalCount ?? 0
  const warningCount = provinceEntry?.warningCount ?? params.data?.warningCount ?? 0
  const abnormalCount = provinceEntry?.abnormalCount ?? params.data?.abnormalCount ?? 0
  const avgRtt = provinceEntry?.avgRtt ?? params.data?.avgRtt ?? 0
  const tone = params.data?.tone || getProvinceTone(provinceEntry)
  const titleSuffix = normalizedName === '香港' || normalizedName === '澳门' ? '区域状态' : '省域状态'

  return renderTooltipCard({
    title: `${provinceName} ${titleSuffix}`,
    tone,
    stats: [
      { label: '主机数', value: `${provinceHosts.length} 台` },
      { label: '在线', value: `${normalCount} 台` },
      { label: '告警/高延迟', value: `${warningCount} 台` },
      { label: '异常', value: `${abnormalCount} 台` },
      { label: '平均 RTT', value: `${Number(avgRtt || 0).toFixed(1)}ms` }
    ],
    hosts: provinceHosts,
    sectionTitle: '主机列表',
    emptyText: '当前省份暂无已定位主机。'
  })
}

const buildPointTooltip = (params) => {
  const data = params.data || {}
  const hostsAtPoint = data.hosts || []

  return renderTooltipCard({
    title: data.location || params.name || '地图点位',
    tone: data.tone || 'normal',
    stats: [
      { label: '聚合主机', value: `${data.hostCount || hostsAtPoint.length || 0} 台` },
      { label: '平均 RTT', value: `${Number(data.avgRtt || 0).toFixed(1)}ms` },
      { label: '异常', value: `${data.abnormalCount || 0} 台` },
      { label: '告警/高延迟', value: `${data.warningCount || 0} 台` }
    ],
    hosts: hostsAtPoint,
    sectionTitle: '点位主机',
    emptyText: '当前点位暂无主机详情。'
  })
}

const buildControlCenterTooltip = () => {
  const center = controlCenter.value || {}
  const stats = [
    center.ip ? { label: '公网 IP', value: center.ip } : null,
    center.province ? { label: '所在地区', value: [center.province, center.city].filter(Boolean).join(' / ') } : null,
    center.isp ? { label: '网络', value: center.isp } : null,
    center.source && center.source !== 'default' ? { label: '定位来源', value: center.source } : null
  ].filter(Boolean)

  return renderTooltipCard({
    title: `${controlCenterName.value}监控中心`,
    tone: 'normal',
    stats: stats.length ? stats : [{ label: '状态', value: center.source === 'default' ? '定位失败，已回退默认中心点' : '监控中心定位中' }],
    hosts: [],
    sectionTitle: '说明',
    emptyText: '当前节点作为监控中心，用于展示数据飞线的汇聚位置。'
  })
}

const renderProvinceTooltip = (params) => {
  const provinceName = shortenProvinceName(params.name)
  const normalizedName = normalizeProvince(params.name)
  const provinceEntry = provinceHostIndex.value.get(normalizedName)
  const provinceHosts = provinceEntry?.hosts || params.data?.hosts || []
  const abnormalCount = provinceEntry?.abnormalCount ?? params.data?.abnormalCount ?? 0
  const normalCount = provinceEntry?.normalCount ?? params.data?.normalCount ?? 0
  const avgRtt = provinceEntry?.avgRtt ?? params.data?.avgRtt ?? 0

  if (!provinceHosts.length) {
    return `<strong>${provinceName}</strong><br/>暂无已定位主机`
  }

  const hostList = provinceHosts
    .slice(0, 8)
    .map((host) => `• ${host.name} ${host.city ? `(${host.city})` : ''} - ${getHostStatusText(host)}`)
    .join('<br/>')

  const extraCount = provinceHosts.length - Math.min(8, provinceHosts.length)

  return [
    `<strong>${provinceName}</strong>`,
    `主机数：${provinceHosts.length}`,
    `在线 / 异常：${normalCount} / ${abnormalCount}`,
    `平均 RTT：${Number(avgRtt).toFixed(1)}ms`,
    '<span style="display:block;margin:8px 0 4px;color:#9ec7ff;">主机列表</span>',
    hostList,
    extraCount > 0 ? `<span style="display:block;margin-top:4px;color:#89A7C7;">… 还有 ${extraCount} 台主机</span>` : ''
  ].join('<br/>')
}

const renderPointTooltip = (params) => {
  const data = params.data || {}
  const hostsAtPoint = data.hosts || []
  const hostList = hostsAtPoint
    .slice(0, 8)
    .map((host) => `• ${host.name} - ${getHostStatusText(host)}`)
    .join('<br/>')

  const extraCount = hostsAtPoint.length - Math.min(8, hostsAtPoint.length)

  return [
    `<strong>${data.location || params.name || '地图点位'}</strong>`,
    `聚合主机：${data.hostCount || hostsAtPoint.length || 0} 台`,
    `平均 RTT：${Number(data.avgRtt || 0).toFixed(1)}ms`,
    `异常 / 高延迟：${data.abnormalCount || 0} / ${data.warningCount || 0}`,
    hostList ? '<span style="display:block;margin:8px 0 4px;color:#9ec7ff;">点位主机</span>' : '',
    hostList,
    extraCount > 0 ? `<span style="display:block;margin-top:4px;color:#89A7C7;">… 还有 ${extraCount} 台主机</span>` : ''
  ]
    .filter(Boolean)
    .join('<br/>')
}

const dedupeClustersById = (clusters = []) => {
  const seen = new Set()

  return clusters.filter((cluster) => {
    const key = cluster?.id || `${cluster?.value?.[0] || ''}:${cluster?.value?.[1] || ''}`
    if (!key || seen.has(key)) {
      return false
    }

    seen.add(key)
    return true
  })
}

const getClusterSymbolSize = (cluster, extra = 0, view = 'china') => {
  const isWorldView = view === 'world'

  if (!cluster) {
    return (isWorldView ? 5 : 7) + extra
  }

  if (isWorldView) {
    const growth = cluster.isDomestic ? 0.42 : 0.72
    const base = cluster.isDomestic ? 3.8 : 5.2
    const min = cluster.isDomestic ? 4.5 + extra : 6 + extra
    const max = cluster.isDomestic ? 9.5 + extra : 13.5 + extra
    return clamp(base + (cluster.hostCount || 1) * growth + extra, min, max)
  }

  return clamp(4.9 + (cluster.hostCount || 1) * 0.78 + extra, 5.2 + extra, 14.6 + extra)
}

const formatMetric = (value, digits = 0) => {
  const numeric = Number(value) || 0
  return digits > 0 ? numeric.toFixed(digits) : Math.round(numeric).toString()
}

const alertTone = (alert) => {
  const message = alert?.message || ''
  const alertType = alert?.alert_type || ''
  if (alertType === 'info') {
    return 'is-success'
  }
  if (message.includes('恢复') || alertType === 'recovery') {
    return 'is-success'
  }
  if (message.includes('丢包') || alertType === 'packet_loss') {
    return 'is-warning'
  }
  return 'is-danger'
}

const formatAlertTime = (value) => {
  if (!value) {
    return '--:--:--'
  }
  return new Date(value).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getAlertPlainLines = (alert) => {
  const rawMessage = String(alert?.message || '')
  if (!rawMessage) {
    return []
  }

  return rawMessage
    .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|h\d)>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.replace(/[#>*`|_]+/g, ' ').replace(/\s+/g, ' ').trim())
    .filter(Boolean)
}

const cleanAlertValue = (value) =>
  String(value || '')
    .replace(/[\u{1F300}-\u{1FAFF}]/gu, '')
    .replace(/\s+/g, ' ')
    .trim()

const extractAlertValue = (lines, label) => {
  const matchedLine = lines.find((line) => line.replace(/\s+/g, '').startsWith(label))
  if (!matchedLine) {
    return ''
  }

  const value = matchedLine.split(/[：:]/).slice(1).join(':')
  return cleanAlertValue(value)
}

const getAlertFacts = (alert) => {
  const lines = getAlertPlainLines(alert)
  const fallbackStatus =
    alert?.alert_type === 'recovery'
      ? '已恢复'
      : alert?.alert_type === 'packet_loss'
        ? '丢包告警'
        : alert?.alert_type === 'info'
          ? '监控平稳'
          : '异常提醒'

  const status = extractAlertValue(lines, '状态') || extractAlertValue(lines, '告警级别') || fallbackStatus
  const packetLoss = extractAlertValue(lines, '丢包率')
  const latency = extractAlertValue(lines, '平均延迟')

  const facts = [
    { label: '状态', value: status || fallbackStatus, tone: alertTone(alert) },
    packetLoss ? { label: '丢包', value: packetLoss } : null,
    latency ? { label: '延迟', value: latency } : null
  ].filter(Boolean)

  return facts.length ? facts : [{ label: '状态', value: fallbackStatus, tone: alertTone(alert) }]
}

const shortenProvinceName = (value) => normalizeProvince(value) || value

const formatFullTime = (value) => {
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const normalizeProvince = (value) => {
  const province = normalizeLocation(value)
  if (!province) {
    return ''
  }

  return province
    .replace(/特别行政区$/u, '')
    .replace(/壮族自治区$/u, '')
    .replace(/回族自治区$/u, '')
    .replace(/维吾尔自治区$/u, '')
    .replace(/自治区$/u, '')
    .replace(/省$/u, '')
    .replace(/市$/u, '')
}

const normalizeCountry = (value) => {
  const country = normalizeLocation(value)
  if (!country) {
    return ''
  }

  const lowerCountry = country.toLowerCase()

  if (
    lowerCountry === 'cn' ||
    lowerCountry.includes('china') ||
    country.includes('中国') ||
    country.includes('香港') ||
    country.includes('澳门') ||
    country.includes('台湾')
  ) {
    return '中国'
  }

  return country
}

const hasValidCoordinates = (longitude, latitude) => {
  const lng = longitude === '' || longitude === null || longitude === undefined ? NaN : Number(longitude)
  const lat = latitude === '' || latitude === null || latitude === undefined ? NaN : Number(latitude)

  return Number.isFinite(lng) && Number.isFinite(lat) && Math.abs(lng) <= 180 && Math.abs(lat) <= 90 && !(lng === 0 && lat === 0)
}

const isChinaCoordinate = (longitude, latitude) => {
  const lng = Number(longitude)
  const lat = Number(latitude)
  return Number.isFinite(lng) && Number.isFinite(lat) && lng >= 73 && lng <= 135 && lat >= 18 && lat <= 54
}

const getProvinceCenterByName = (provinceName) => {
  const normalizedName = normalizeProvince(provinceName)
  if (!normalizedName) {
    return null
  }

  const matchedEntry = Array.from(provinceCenters.value.entries()).find(
    ([name]) => normalizeProvince(name) === normalizedName
  )
  const center = matchedEntry?.[1]
  return Array.isArray(center) && center.length >= 2 ? [Number(center[0]), Number(center[1])] : null
}

const isPointInRing = ([longitude, latitude], ring = []) => {
  let inside = false

  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const pointI = ring[i]
    const pointJ = ring[j]
    if (!Array.isArray(pointI) || !Array.isArray(pointJ)) {
      continue
    }

    const xi = Number(pointI[0])
    const yi = Number(pointI[1])
    const xj = Number(pointJ[0])
    const yj = Number(pointJ[1])
    if (![xi, yi, xj, yj].every(Number.isFinite)) {
      continue
    }

    const intersects = ((yi > latitude) !== (yj > latitude)) &&
      longitude < ((xj - xi) * (latitude - yi)) / (yj - yi || Number.EPSILON) + xi
    if (intersects) {
      inside = !inside
    }
  }

  return inside
}

const isPointInPolygon = (point, polygon = []) => {
  if (!Array.isArray(polygon[0]) || !isPointInRing(point, polygon[0])) {
    return false
  }

  return !polygon.slice(1).some((hole) => isPointInRing(point, hole))
}

const isPointInFeature = (point, feature) => {
  const geometry = feature?.geometry
  if (!geometry) {
    return false
  }

  if (geometry.type === 'Polygon') {
    return isPointInPolygon(point, geometry.coordinates)
  }

  if (geometry.type === 'MultiPolygon') {
    return geometry.coordinates.some((polygon) => isPointInPolygon(point, polygon))
  }

  return false
}

const resolveHostMapCoordinates = (host) => {
  const country = normalizeCountry(host?.country)
  const province = normalizeProvince(host?.province)
  const hasCoordinates = hasValidCoordinates(host?.longitude, host?.latitude)
  const longitude = Number(host?.longitude)
  const latitude = Number(host?.latitude)
  const isDomestic = country === '中国' || Boolean(province)
  const provinceCenter = getProvinceCenterByName(province)

  if (!isDomestic) {
    return hasCoordinates ? { longitude, latitude, source: 'raw' } : null
  }

  if (!province) {
    return hasCoordinates ? { longitude, latitude, source: 'raw' } : null
  }

  if (hasCoordinates) {
    const feature = provinceFeatureIndex.value.get(province)
    if (!feature || isPointInFeature([longitude, latitude], feature)) {
      return { longitude, latitude, source: 'raw' }
    }

    if (provinceCenter) {
      return { longitude: provinceCenter[0], latitude: provinceCenter[1], source: 'province-center' }
    }

    return { longitude, latitude, source: 'raw' }
  }

  if (provinceCenter) {
    return { longitude: provinceCenter[0], latitude: provinceCenter[1], source: 'province-center' }
  }

  return null
}

const isChinaHost = (host) => normalizeCountry(host?.country) === '中国' || isChinaCoordinate(host?.longitude, host?.latitude)

const normalizeIsp = (value) => {
  const source = normalizeLocation(value, '未知网络')
  const lowerSource = source.toLowerCase()

  if (source === '????' || lowerSource.includes('unknown')) {
    return '未知网络'
  }

  if (lowerSource.includes('hangzhou alibaba advertising')) {
    return 'Hangzhou A'
  }
  if (lowerSource.includes('alibaba.com')) {
    return 'Alibaba.com'
  }
  if (lowerSource.includes('aliyun') || lowerSource.includes('alicloud')) {
    return 'Aliyun'
  }
  if (lowerSource.includes('chinanet hubei')) {
    return 'CHINANET H'
  }
  if (lowerSource.includes('chinanet jiangsu')) {
    return 'CHINANET J'
  }
  if (lowerSource.includes('china telecom')) {
    return 'China Tele'
  }
  if (lowerSource.includes('china unicom')) {
    return 'China Unicom'
  }
  if (lowerSource.includes('china mobile')) {
    return 'China Mobile'
  }
  if (lowerSource.includes('oracle america')) {
    return 'Oracle Ame'
  }
  if (lowerSource.includes('oracle')) {
    return 'Oracle'
  }
  if (lowerSource.includes('tencent')) {
    return 'Tencent'
  }
  if (lowerSource.includes('huawei')) {
    return 'Huawei'
  }

  return source.length > 12 ? `${source.slice(0, 10)}..` : source
}

const normalizeLocation = (value, fallback = '') => {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

const average = (values) => {
  const validValues = values.filter((value) => Number(value) > 0)
  if (!validValues.length) {
    return 0
  }
  return validValues.reduce((total, value) => total + Number(value), 0) / validValues.length
}

const clamp = (value, min, max) => Math.min(Math.max(value, min), max)

const detectTouchLikeDevice = () => {
  if (typeof window === 'undefined') {
    return false
  }

  const hasCoarsePointer = window.matchMedia?.('(hover: none), (pointer: coarse)').matches
  return Boolean(hasCoarsePointer || navigator.maxTouchPoints > 0 || window.innerWidth <= 720)
}

const syncInputMode = () => {
  const nextTouchMode = detectTouchLikeDevice()
  const changed = isTouchLikeDevice.value !== nextTouchMode
  isTouchLikeDevice.value = nextTouchMode

  if (changed && mapChartInstance) {
    renderMapChart()
  }
}

onMounted(async () => {
  syncInputMode()
  updateClock()
  syncFullscreenState()
  clockTimer = setInterval(updateClock, 1000)
  await nextTick()
  initCharts()
  await fetchScreenData()

  resizeHandler = () => {
    syncInputMode()
    trendChartInstance?.resize()
    mapChartInstance?.resize()
    ispChartInstance?.resize()
    renderIspChart()
  }
  window.addEventListener('resize', resizeHandler)
  window.visualViewport?.addEventListener('resize', resizeHandler)

  fullscreenChangeHandler = () => {
    syncFullscreenState()
    resizeHandler?.()
  }
  document.addEventListener('fullscreenchange', fullscreenChangeHandler)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
  clearInterval(clockTimer)
  clearInterval(alertTickerTimer)

  metricFrames.forEach((frame) => cancelAnimationFrame(frame))
  metricFrames.clear()

  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
    window.visualViewport?.removeEventListener('resize', resizeHandler)
  }

  if (fullscreenChangeHandler) {
    document.removeEventListener('fullscreenchange', fullscreenChangeHandler)
  }

  if (mapClickHandler) {
    mapChartInstance?.off('click', mapClickHandler)
  }

  if (mapRoamHandler) {
    mapChartInstance?.off('georoam', mapRoamHandler)
  }

  if (mapBlankClickHandler) {
    mapChartInstance?.getZr().off('click', mapBlankClickHandler)
  }

  trendChartInstance?.dispose()
  mapChartInstance?.dispose()
  ispChartInstance?.dispose()
})
</script>

<style scoped>
.screen-shell {
  position: relative;
  height: 100vh;
  height: 100dvh;
  min-height: 0;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  color: var(--text-main);
  background:
    radial-gradient(circle at top, rgba(30, 144, 255, 0.12), transparent 35%),
    linear-gradient(135deg, var(--screen-bg) 0%, var(--screen-bg-alt) 55%, #02060f 100%);
  box-sizing: border-box;
}

.screen-background,
.bg-grid,
.bg-glow,
.bg-scanlines,
.bg-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bg-grid {
  background-image:
    linear-gradient(var(--grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 0.88), transparent 95%);
}

.bg-glow {
  filter: blur(72px);
  opacity: 0.38;
}

.bg-glow-a {
  background: radial-gradient(circle, var(--accent-soft) 0%, transparent 60%);
  width: 38vw;
  height: 38vw;
  top: -8vw;
  left: -8vw;
  animation: drift-a 18s ease-in-out infinite alternate;
}

.bg-glow-b {
  background: radial-gradient(circle, rgba(0, 255, 195, 0.12) 0%, transparent 60%);
  width: 30vw;
  height: 30vw;
  right: -10vw;
  bottom: -8vw;
  animation: drift-b 20s ease-in-out infinite alternate;
}

.bg-scanlines {
  background: linear-gradient(
    to bottom,
    transparent 0%,
    rgba(255, 255, 255, 0.035) 50%,
    transparent 100%
  );
  background-size: 100% 6px;
  opacity: 0.18;
}

.bg-particles {
  opacity: 0.5;
  background-image:
    radial-gradient(circle at 15% 20%, rgba(255, 255, 255, 0.22) 0 1px, transparent 1px),
    radial-gradient(circle at 35% 80%, rgba(255, 255, 255, 0.18) 0 1px, transparent 1px),
    radial-gradient(circle at 75% 25%, rgba(255, 255, 255, 0.18) 0 1px, transparent 1px),
    radial-gradient(circle at 82% 70%, rgba(255, 255, 255, 0.16) 0 1px, transparent 1px);
  animation: particle-float 24s linear infinite;
  animation-play-state: var(--animation-state);
}

.glass-panel,
.glass-inset {
  position: relative;
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  box-shadow:
    0 20px 50px rgba(0, 0, 0, 0.32),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(18px);
}

.glass-panel::before,
.glass-inset::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.045), transparent 40%);
}

.glass-panel {
  border-radius: 24px;
}

.glass-inset {
  border-radius: 18px;
  background: var(--panel-inset);
}

.screen-header {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) minmax(520px, auto) minmax(240px, 1fr);
  gap: 14px;
  align-items: center;
  padding: 14px 20px;
}

.header-side {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
}

.header-side-left {
  justify-self: start;
  align-items: flex-start;
}

.header-side-right {
  justify-self: end;
  align-items: flex-end;
}

.header-kicker,
.panel-kicker {
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.screen-title {
  margin: 6px 0 8px;
  font-size: clamp(24px, 1.8vw, 34px);
  font-weight: 700;
  letter-spacing: 0.03em;
  color: var(--text-main);
  text-shadow: 0 0 30px rgba(30, 144, 255, 0.24);
}

.header-meta,
.stage-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-chip,
.stage-flag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--text-muted);
  font-size: 11px;
}

.header-center {
  text-align: center;
}

.header-center-main {
  align-self: center;
}

.header-center-main .header-meta {
  justify-content: center;
}

.clock-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.clock-value {
  font-size: clamp(20px, 1.55vw, 28px);
  font-weight: 700;
  letter-spacing: 0.08em;
}

.clock-subtitle {
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-muted);
}

.header-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--success);
  box-shadow: 0 0 14px var(--success);
  animation: pulse-dot 1.8s ease-in-out infinite;
  animation-play-state: var(--animation-state);
}

.header-action-button,
.admin-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 44px;
  padding: 10px 16px;
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), transparent);
  color: var(--text-main);
  line-height: 1;
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.header-action-button:hover,
.admin-button:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.24);
}

.stage-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.035);
  color: var(--text-muted);
  font-size: 11px;
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.stage-toggle:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.18);
}

.stage-toggle.active {
  background: var(--accent-soft);
  border-color: rgba(123, 199, 255, 0.42);
  color: var(--text-main);
  box-shadow: 0 0 20px rgba(30, 144, 255, 0.12);
}

.metric-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  min-height: 96px;
  min-width: 0;
}

.metric-icon {
  width: 50px;
  height: 50px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 22px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--accent);
}

.metric-card.tone-success .metric-icon {
  color: var(--success);
}

.metric-card.tone-danger .metric-icon {
  color: var(--danger);
}

.metric-card.tone-alert .metric-icon {
  color: var(--warning);
  background: linear-gradient(135deg, rgba(250, 219, 20, 0.14), rgba(255, 77, 79, 0.13));
  box-shadow: inset 0 0 0 1px rgba(250, 219, 20, 0.12), 0 0 18px rgba(255, 77, 79, 0.12);
}

.metric-card.tone-warning .metric-icon {
  color: var(--warning);
}

.metric-label {
  font-size: 12px;
  color: var(--text-muted);
}

.metric-main {
  min-width: 0;
}

.metric-value {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 6px;
  font-size: 28px;
  font-weight: 700;
}

.metric-value em {
  font-style: normal;
  font-size: 13px;
  color: var(--text-muted);
}

.metric-detail-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  min-width: 0;
}

.metric-detail {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.25;
  white-space: nowrap;
}

.metric-detail i {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  flex: 0 0 auto;
}

.metric-detail strong {
  color: var(--text-main);
  font-weight: 700;
}

.metric-detail.warning {
  color: #fff0a6;
  border-color: rgba(250, 219, 20, 0.2);
  background: rgba(250, 219, 20, 0.08);
}

.metric-detail.warning i {
  background: var(--warning);
  box-shadow: 0 0 10px var(--warning);
}

.metric-detail.danger {
  color: #ffd7d8;
  border-color: rgba(255, 77, 79, 0.22);
  background: rgba(255, 77, 79, 0.08);
}

.metric-detail.danger i {
  background: var(--danger);
  box-shadow: 0 0 10px var(--danger);
}

.metric-note {
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-muted);
}

.screen-body {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(236px, 20%) minmax(760px, 60%) minmax(236px, 20%);
  gap: 14px;
  flex: 1;
  min-height: 0;
}

.side-column,
.center-column {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}

.panel,
.stage-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 14px;
}

.side-column .panel {
  flex: 1;
}

.distribution-panel {
  flex: 1.06;
}

.ranking-panel {
  flex: 0.94;
}

.stage-panel {
  flex: 1;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-head h2 {
  margin: 4px 0 0;
  font-size: 18px;
}

.panel-extra {
  color: var(--text-muted);
  font-size: 11px;
  padding-top: 6px;
}

.chart-panel {
  min-height: 0;
  flex: 1;
}

.trend-chart,
.donut-chart {
  min-height: 220px;
}

.distribution-panel .donut-chart {
  min-height: 196px;
}

.alert-marquee {
  position: relative;
  overflow: hidden;
  min-height: 0;
  flex: 1;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-item {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.alert-item.is-danger {
  border-color: rgba(255, 77, 79, 0.24);
  box-shadow: inset 0 0 0 1px rgba(255, 77, 79, 0.06);
}

.alert-item.is-warning {
  border-color: rgba(250, 219, 20, 0.22);
  box-shadow: inset 0 0 0 1px rgba(250, 219, 20, 0.06);
}

.alert-item.is-success {
  border-color: rgba(0, 255, 195, 0.22);
  box-shadow: inset 0 0 0 1px rgba(0, 255, 195, 0.06);
}

.alert-topline {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.alert-host {
  color: var(--text-main);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alert-facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.alert-fact {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.alert-fact label {
  font-size: 10px;
  color: var(--text-muted);
}

.alert-fact strong {
  font-size: 12px;
  color: var(--text-main);
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alert-fact-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.alert-fact-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 999px;
}

.alert-fact-dot.is-success {
  background: var(--success);
  box-shadow: 0 0 10px var(--success);
}

.alert-fact-dot.is-warning {
  background: var(--warning);
  box-shadow: 0 0 10px var(--warning);
}

.alert-fact-dot.is-danger {
  background: var(--danger);
  box-shadow: 0 0 10px var(--danger);
}

.stage-head {
  margin-bottom: 8px;
}

.stage-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 8px;
}

.overview-pill {
  padding: 9px 11px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.overview-pill label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
}

.overview-pill strong {
  display: block;
  margin-top: 4px;
  font-size: 17px;
}

.map-stage {
  position: relative;
  flex: 1;
  min-height: 0;
  border-radius: 26px;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 58%, rgba(30, 144, 255, 0.18), transparent 44%),
    radial-gradient(circle at 50% 78%, rgba(0, 255, 195, 0.08), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 36%),
    rgba(2, 10, 22, 0.75);
}

.map-orbit {
  position: absolute;
  inset: 50% auto auto 50%;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 999px;
  transform: translate(-50%, -50%);
  animation: orbit-spin 24s linear infinite;
  animation-play-state: var(--animation-state);
  opacity: 0.5;
}

.map-orbit-a {
  width: 66%;
  height: 66%;
  border-top-color: rgba(255, 255, 255, 0.12);
}

.map-orbit-b {
  width: 84%;
  height: 84%;
  border-left-color: rgba(255, 255, 255, 0.08);
  animation-direction: reverse;
}

.map-surface {
  position: absolute;
  inset: -18px -30px -22px -30px;
  border-radius: 24px;
  overflow: hidden;
  transform: perspective(2200px) rotateX(var(--map-tilt)) scale(var(--map-scale)) translateY(var(--map-shift-y));
  transform-origin: center 58%;
}

.map-chart {
  width: 100%;
  height: 100%;
}

.stage-hint {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 2;
  width: min(250px, calc(100% - 28px));
  padding: 12px 14px;
}

.stage-hint strong {
  display: block;
  font-size: 15px;
  letter-spacing: 0.04em;
}

.stage-hint span {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-muted);
}

.stage-legend {
  position: absolute;
  left: 14px;
  bottom: 14px;
  z-index: 2;
  padding: 10px 12px;
  min-width: 164px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  color: var(--text-muted);
}

.legend-row + .legend-row {
  margin-top: 8px;
}

.legend-dot,
.legend-line {
  display: inline-block;
  flex: 0 0 auto;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.legend-dot.success {
  background: var(--success);
  box-shadow: 0 0 12px var(--success);
}

.legend-dot.warning {
  background: var(--warning);
  box-shadow: 0 0 12px var(--warning);
}

.legend-dot.danger {
  background: var(--danger);
  box-shadow: 0 0 12px var(--danger);
}

.legend-line {
  width: 18px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--flow), transparent);
}

.legend-note {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 10px;
  line-height: 1.45;
  color: var(--text-muted);
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px 8px;
  margin-top: 2px;
}

.cloud-tag {
  max-width: calc(50% - 4px);
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.045);
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1;
  overflow: hidden;
}

.cloud-tag-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cloud-tag-value {
  flex: 0 0 auto;
  color: var(--text-main);
  font-size: 10px;
  font-weight: 700;
}

.ranking-list {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 6px;
  overflow: auto;
  min-height: 0;
  padding-right: 4px;
}

.ranking-item {
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.ranking-item.success {
  border-color: rgba(0, 255, 195, 0.1);
}

.ranking-item.warning {
  border-color: rgba(250, 219, 20, 0.16);
}

.ranking-item.danger {
  border-color: rgba(255, 77, 79, 0.16);
}

.rank-badge {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-soft), transparent);
}

.rank-topline,
.rank-subline {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.rank-topline strong {
  font-size: 12px;
  line-height: 1.2;
}

.rank-topline span,
.rank-subline span {
  font-size: 10px;
  color: var(--text-muted);
}

.rank-subline {
  margin-top: 2px;
}

.rank-bar {
  height: 6px;
  margin-top: 6px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
}

.rank-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--danger), var(--warning), var(--accent));
  box-shadow: 0 0 18px rgba(255, 107, 107, 0.24);
}

.empty-state {
  padding: 18px;
  text-align: center;
  color: var(--text-muted);
  border: 1px dashed rgba(255, 255, 255, 0.12);
  border-radius: 18px;
}

.alert-shift-move,
.alert-shift-enter-active,
.alert-shift-leave-active {
  transition: all 0.45s ease;
}

.alert-shift-enter-from,
.alert-shift-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

.ranking-list::-webkit-scrollbar {
  width: 6px;
}

.ranking-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
}

.mobile-tabbar {
  display: none;
}

.mobile-overview-detail,
.mobile-map-detail,
.mobile-alert-summary,
.mobile-ranking-summary {
  display: none;
}

.animations-off .map-orbit,
.animations-off .bg-particles,
.animations-off .status-dot {
  animation-play-state: paused;
}

@media (max-width: 1600px) {
  .metric-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
  }

  .metric-card {
    gap: 10px;
    padding: 12px 14px;
  }

  .metric-icon {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    font-size: 19px;
  }

  .metric-value {
    font-size: 23px;
  }

  .metric-detail-row {
    gap: 4px;
  }

  .metric-detail {
    padding: 3px 5px;
    font-size: 10px;
  }

  .screen-body {
    grid-template-columns: minmax(250px, 23%) minmax(520px, 54%) minmax(250px, 23%);
  }

  .stage-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-height: 1100px) {
  .screen-shell {
    padding: 12px 14px;
    gap: 10px;
  }

  .screen-header {
    padding: 12px 18px;
  }

  .metric-card {
    min-height: 84px;
    padding: 12px 14px;
  }

  .metric-icon {
    width: 46px;
    height: 46px;
    font-size: 20px;
  }

  .metric-value {
    font-size: 24px;
  }

  .panel,
  .stage-panel {
    padding: 12px;
  }

  .trend-chart,
  .donut-chart {
    min-height: 200px;
  }

  .distribution-panel .donut-chart {
    min-height: 178px;
  }

  .map-surface {
    inset: -14px -20px -18px -20px;
    transform: perspective(2100px) rotateX(calc(var(--map-tilt) * 0.92)) scale(var(--map-scale)) translateY(var(--map-shift-y));
  }
}

@media (max-height: 860px) and (min-width: 1281px) {
  .screen-shell {
    padding: 10px 12px;
    gap: 8px;
  }

  .screen-header {
    padding: 10px 16px;
    gap: 10px;
  }

  .header-side {
    gap: 6px;
  }

  .screen-title {
    margin: 4px 0 6px;
    font-size: clamp(22px, 1.65vw, 30px);
  }

  .header-action-button,
  .admin-button {
    min-height: 38px;
    padding: 8px 12px;
    border-radius: 13px;
  }

  .metric-grid {
    gap: 8px;
  }

  .metric-card {
    min-height: 72px;
    padding: 10px 12px;
  }

  .metric-icon {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    font-size: 18px;
  }

  .metric-value {
    margin-top: 3px;
    font-size: 21px;
  }

  .metric-note,
  .metric-detail-row {
    margin-top: 4px;
  }

  .screen-body,
  .side-column,
  .center-column {
    gap: 10px;
  }

  .panel,
  .stage-panel {
    padding: 10px;
  }

  .panel-head {
    margin-bottom: 6px;
  }

  .panel-head h2 {
    margin-top: 2px;
    font-size: 16px;
  }

  .trend-chart,
  .donut-chart {
    min-height: 160px;
  }

  .distribution-panel .donut-chart {
    min-height: 144px;
  }

  .stage-overview {
    margin-bottom: 6px;
  }

  .overview-pill {
    padding: 7px 9px;
  }

  .overview-pill strong {
    margin-top: 2px;
    font-size: 15px;
  }

  .stage-hint {
    top: 10px;
    left: 10px;
    padding: 9px 11px;
  }

  .stage-legend {
    left: 10px;
    bottom: 10px;
    padding: 8px 10px;
  }
}

@media (max-width: 1420px) and (min-width: 1281px) {
  .screen-header {
    grid-template-columns: minmax(190px, 0.75fr) minmax(420px, auto) minmax(190px, 0.75fr);
  }

  .screen-body {
    grid-template-columns: minmax(220px, 22%) minmax(520px, 56%) minmax(220px, 22%);
  }
}

@media (max-width: 1100px) {
  .screen-shell {
    height: 100vh;
    height: 100dvh;
    min-height: 0;
    padding: 14px;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .screen-header {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .header-side-left,
  .header-side-right {
    justify-self: center;
    align-items: center;
  }

  .header-actions {
    justify-content: center;
  }

  .screen-body {
    grid-template-columns: 1fr;
    flex: none;
  }

  .side-column .panel,
  .stage-panel {
    flex: none;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .map-stage {
    min-height: clamp(460px, 62vh, 620px);
  }

  .stage-hint {
    top: 18px;
    left: 18px;
    width: min(240px, calc(100% - 36px));
  }

  .stage-legend {
    left: 18px;
    bottom: 18px;
  }

  .map-surface {
    inset: 0;
    transform: none;
  }
}

@media (max-width: 720px) {
  .screen-shell {
    height: 100vh;
    height: 100dvh;
    min-height: 0;
    padding: 10px 10px calc(82px + env(safe-area-inset-bottom));
    gap: 10px;
    overflow: hidden;
    scroll-padding-top: 0;
    scroll-padding-bottom: 0;
    background:
      radial-gradient(circle at 50% -8%, rgba(30, 144, 255, 0.2), transparent 34%),
      linear-gradient(180deg, #020712 0%, var(--screen-bg) 45%, #02060f 100%);
  }

  .screen-header,
  .metric-card,
  .panel,
  .stage-panel {
    border-radius: 18px;
  }

  .screen-header {
    flex: 0 0 auto;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 10px;
    align-items: center;
    padding: 12px;
    text-align: left;
  }

  .header-center-main {
    grid-column: 1 / -1;
    order: 1;
    text-align: left;
  }

  .header-side-left {
    order: 2;
    justify-self: start;
    align-items: flex-start;
  }

  .header-side-right {
    order: 3;
    justify-self: end;
    align-items: flex-end;
  }

  .header-kicker,
  .header-meta,
  .clock-subtitle {
    display: none;
  }

  .header-status {
    font-size: 12px;
  }

  .header-actions {
    flex-wrap: nowrap;
    gap: 8px;
  }

  .header-action-button,
  .admin-button {
    min-height: 36px;
    width: 36px;
    padding: 0;
    border-radius: 12px;
    gap: 0;
  }

  .header-action-button span,
  .admin-button span {
    display: none;
  }

  .metric-grid {
    display: none;
    grid-template-columns: none;
    gap: 10px;
    margin: 0 -12px;
    padding: 0 12px 2px;
    min-height: 108px;
    overflow-x: auto;
    scroll-snap-type: x proximity;
    scrollbar-width: none;
  }

  .metric-grid::-webkit-scrollbar {
    display: none;
  }

  .metric-card {
    flex: 0 0 152px;
    min-height: 106px;
    align-items: flex-start;
    gap: 10px;
    padding: 12px;
    scroll-snap-align: start;
  }

  .metric-card:first-child {
    display: none;
  }

  .metric-icon {
    width: 34px;
    height: 34px;
    border-radius: 11px;
    font-size: 17px;
  }

  .metric-label {
    font-size: 11px;
  }

  .metric-value {
    margin-top: 4px;
    font-size: 22px;
  }

  .metric-detail-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .metric-detail {
    padding: 2px 0;
    border: 0;
    background: transparent;
  }

  .mobile-overview-detail.is-mobile-active {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-height: 0;
    gap: 10px;
    overflow: hidden;
    padding: 10px;
    border-radius: 20px;
  }

  .mobile-health-grid,
  .mobile-data-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 7px;
  }

  .mobile-health-item,
  .mobile-data-item {
    min-width: 0;
    padding: 8px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  .mobile-health-item label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--text-muted);
  }

  .mobile-health-item label span {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--accent);
  }

  .mobile-health-item.success label span {
    background: var(--success);
    box-shadow: 0 0 10px var(--success);
  }

  .mobile-health-item.warning label span {
    background: var(--warning);
    box-shadow: 0 0 10px var(--warning);
  }

  .mobile-health-item.danger label span {
    background: var(--danger);
    box-shadow: 0 0 10px var(--danger);
  }

  .mobile-health-item strong,
  .mobile-data-item strong {
    display: block;
    margin-top: 4px;
    color: var(--text-main);
    font-size: 17px;
  }

  .mobile-data-item label,
  .mobile-data-item span {
    display: block;
    font-size: 11px;
    color: var(--text-muted);
  }

  .mobile-section-title {
    margin: 0 0 -4px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .mobile-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    min-height: 0;
    overflow: hidden;
  }

  .mobile-chip {
    max-width: 100%;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 8px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid rgba(255, 255, 255, 0.06);
    color: var(--text-muted);
    font-size: 11px;
    line-height: 1;
  }

  .mobile-chip strong {
    color: var(--text-main);
    font-size: 11px;
  }

  .stage-overview {
    grid-template-columns: 1fr;
  }

  .screen-body {
    display: contents;
    flex: 0 0 auto;
    min-height: 0;
    overflow: visible;
  }

  .center-column {
    order: 1;
  }

  .screen-body > .side-column:first-child {
    order: 2;
  }

  .screen-body > .side-column:last-child {
    order: 3;
  }

  .trend-panel,
  .distribution-panel {
    display: none;
  }

  .side-column,
  .center-column {
    display: contents;
    gap: 12px;
  }

  #mobile-map,
  #mobile-alerts,
  #mobile-ranking {
    display: none;
  }

  #mobile-map.is-mobile-active,
  #mobile-alerts.is-mobile-active,
  #mobile-ranking.is-mobile-active {
    display: flex;
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
  }

  .screen-title {
    margin: 0;
    font-size: 21px;
    line-height: 1.25;
    letter-spacing: 0;
  }

  .clock-value {
    font-size: 16px;
    letter-spacing: 0.04em;
  }

  .stage-panel {
    padding: 10px;
    border-radius: 22px;
  }

  .stage-head {
    align-items: center;
    gap: 10px;
  }

  .stage-head h2 {
    font-size: 17px;
  }

  .stage-flags {
    justify-content: flex-start;
    gap: 6px;
  }

  .stage-toggle {
    padding: 5px 8px;
    font-size: 10px;
  }

  .stage-flag,
  .stage-overview {
    display: none;
  }

  .map-stage {
    flex: 1 1 auto;
    min-height: 0;
    height: auto;
    border-radius: 20px;
    background:
      radial-gradient(circle at 50% 55%, rgba(30, 144, 255, 0.22), transparent 42%),
      radial-gradient(circle at 50% 82%, rgba(0, 255, 195, 0.1), transparent 25%),
      rgba(2, 10, 22, 0.82);
  }

  .map-surface {
    inset: 0;
    transform: none;
  }

  .stage-hint,
  .stage-legend {
    display: none;
  }

  .mobile-map-detail {
    flex: 0 0 auto;
    display: block;
    margin-top: 6px;
  }

  .mobile-map-detail .mobile-data-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 5px;
  }

  .mobile-map-detail .mobile-data-item {
    padding: 6px 4px;
    border-radius: 10px;
    text-align: center;
  }

  .mobile-map-detail .mobile-data-item label,
  .mobile-map-detail .mobile-data-item span {
    font-size: 10px;
  }

  .mobile-map-detail .mobile-data-item strong {
    margin-top: 2px;
    font-size: 13px;
    white-space: nowrap;
  }

  .mobile-map-note {
    margin-top: 4px;
    padding: 0 2px;
    color: var(--text-muted);
    font-size: 10px;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .panel {
    flex: 1 1 auto;
    min-height: 0;
    padding: 10px;
    border-radius: 20px;
  }

  .panel-head {
    flex: 0 0 auto;
    align-items: center;
    margin-bottom: 8px;
  }

  .panel-head h2 {
    margin-top: 2px;
    font-size: 17px;
  }

  .panel-extra {
    padding-top: 0;
  }

  .mobile-alert-summary,
  .mobile-ranking-summary {
    flex: 0 0 auto;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
  }

  .mobile-alert-summary span,
  .mobile-ranking-summary span {
    display: inline-flex;
    align-items: center;
    min-height: 24px;
    padding: 0 8px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.045);
    color: var(--text-muted);
    font-size: 11px;
  }

  .mobile-alert-summary .warning {
    color: #fff0a6;
    background: rgba(250, 219, 20, 0.08);
  }

  .mobile-alert-summary .danger {
    color: #ffd7d8;
    background: rgba(255, 77, 79, 0.08);
  }

  .alert-marquee {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
  }

  .alert-list,
  .ranking-list {
    flex: 1 1 auto;
    min-height: 0;
    gap: 6px;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding-right: 2px;
    -webkit-overflow-scrolling: touch;
  }

  .alert-item,
  .ranking-item {
    border-radius: 14px;
  }

  .alert-item {
    padding: 8px 9px;
  }

  .alert-facts {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 5px;
    margin-top: 6px;
  }

  .alert-fact {
    padding: 6px 7px;
    border-radius: 10px;
  }

  .ranking-item {
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 7px;
    padding: 8px;
  }

  .rank-badge {
    width: 32px;
    height: 32px;
    border-radius: 10px;
  }

  .mobile-tabbar {
    position: fixed;
    z-index: 30;
    left: 10px;
    right: 10px;
    bottom: max(8px, env(safe-area-inset-bottom));
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 5px;
    padding: 6px;
    border-radius: 20px;
    background: rgba(5, 16, 34, 0.86);
    box-shadow:
      0 18px 38px rgba(0, 0, 0, 0.4),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(18px);
  }

  .mobile-tabbar button {
    display: flex;
    min-width: 0;
    min-height: 44px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    padding: 6px 4px;
    border: 0;
    border-radius: 14px;
    background: transparent;
    color: var(--text-muted);
    font-size: 11px;
    line-height: 1;
    cursor: pointer;
  }

  .mobile-tabbar button:hover,
  .mobile-tabbar button:focus-visible,
  .mobile-tabbar button.active {
    color: var(--text-main);
    background: rgba(30, 144, 255, 0.14);
    outline: none;
  }

  .mobile-tabbar .el-icon {
    font-size: 18px;
  }
}

@media (max-width: 720px) and (max-height: 740px) {
  .screen-shell {
    padding: 8px 8px calc(72px + env(safe-area-inset-bottom));
    gap: 8px;
  }

  .screen-header {
    padding: 9px 10px;
    gap: 6px 8px;
  }

  .header-status {
    display: none;
  }

  .screen-title {
    font-size: 19px;
  }

  .clock-value {
    font-size: 15px;
  }

  .panel-kicker {
    display: none;
  }

  .panel-head h2,
  .stage-head h2 {
    font-size: 15px;
  }

  .panel-head,
  .stage-head {
    margin-bottom: 6px;
  }

  .mobile-overview-detail.is-mobile-active,
  .panel,
  .stage-panel {
    padding: 8px;
  }

  .mobile-overview-detail.is-mobile-active {
    gap: 7px;
  }

  .mobile-health-grid,
  .mobile-data-grid {
    gap: 5px;
  }

  .mobile-health-item,
  .mobile-data-item {
    padding: 6px;
  }

  .mobile-health-item strong,
  .mobile-data-item strong {
    font-size: 15px;
  }

  .mobile-chip {
    padding: 4px 7px;
  }

  .mobile-alert-summary,
  .mobile-ranking-summary {
    margin-bottom: 6px;
  }

  .mobile-alert-summary span,
  .mobile-ranking-summary span {
    min-height: 22px;
    font-size: 10px;
  }

  .alert-item {
    padding: 7px;
  }

  .alert-fact {
    padding: 5px 6px;
  }

  .ranking-item {
    padding: 7px;
  }

  .rank-badge {
    width: 30px;
    height: 30px;
  }

  .mobile-map-note {
    display: none;
  }

  .mobile-tabbar {
    left: 8px;
    right: 8px;
    bottom: max(7px, env(safe-area-inset-bottom));
    padding: 5px;
  }

  .mobile-tabbar button {
    min-height: 40px;
  }
}

@keyframes drift-a {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(50px, 20px, 0);
  }
}

@keyframes drift-b {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(-40px, -30px, 0);
  }
}

@keyframes particle-float {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-60px);
  }
}

@keyframes orbit-spin {
  from {
    transform: translate(-50%, -50%) rotate(0deg);
  }
  to {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

@keyframes pulse-dot {
  0%,
  100% {
    opacity: 0.8;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.18);
  }
}
</style>
