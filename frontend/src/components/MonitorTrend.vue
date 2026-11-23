<template>
  <div class="monitor-trend" :data-point-count="points.length" v-loading="loading">
    <div v-show="points.length" ref="chartDom" class="monitor-trend__canvas"></div>
    <div v-if="!loading && points.length && missingSampleCount" class="monitor-trend__notice">部分时间点无样本：{{ missingSampleCount }} 个点</div>
    <span v-if="!loading && !points.length" class="monitor-trend__empty">{{ emptyText }}</span>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { echarts } from '../lib/echarts'

const props = defineProps({
  points: { type: Array, default: () => [] },
  loading: Boolean,
  emptyText: { type: String, default: '此时间范围内没有监控数据' },
  compact: Boolean,
  showOnlineRate: { type: Boolean, default: true }
})
const chartDom = ref(null)
const activeMetrics = computed(() => metrics.filter(metric => props.showOnlineRate || metric.key !== 'online_rate'))
const isTimeout = point => point?.avg_packet_loss != null && Number(point.avg_packet_loss) >= 100
const missingSampleCount = computed(() => props.points.filter(point => activeMetrics.value.some(metric =>
  point?.[metric.key] == null && !(metric.key === 'avg_rtt' && isTimeout(point))
)).length)
let chart
const metrics = [
  { name: '在线率', key: 'online_rate', color: '#27986a', rgb: '39, 152, 106', unit: '%' },
  { name: '丢包率', key: 'avg_packet_loss', color: '#e25d69', rgb: '226, 93, 105', unit: '%' },
  { name: '平均延迟', key: 'avg_rtt', color: '#367ed8', rgb: '54, 126, 216', unit: ' ms', axis: 1 }
]

const draw = () => {
  const element = chartDom.value
  if (!element?.clientWidth || !element.clientHeight || !props.points.length) return
  chart ||= echarts.init(element)
  chart.resize()
  const small = element.clientHeight < 185
  const narrow = element.clientWidth < 420
  const tight = element.clientHeight < 110
  chart.setOption({
    animation: false,
    tooltip: { trigger: 'axis', confine: true, axisPointer: { type: narrow ? 'line' : 'cross' } },
    legend: { top: 1, itemWidth: 14, itemHeight: 7, itemGap: narrow ? 9 : 18, textStyle: { fontSize: narrow ? 10 : 12, color: '#445672' } },
    grid: { left: small ? 3 : 12, right: small ? 3 : 12, top: tight ? 28 : small ? 32 : 47, bottom: small ? 1 : 11, containLabel: true },
    xAxis: {
      type: 'category', data: props.points.map(point => point.time), boundaryGap: props.points.length === 1,
      axisLabel: { hideOverlap: true, showMinLabel: !narrow, fontSize: narrow ? 9 : 11, color: '#566780' },
      axisTick: { show: false }, axisLine: { lineStyle: { color: '#ced8e5' } }
    },
    yAxis: [
      { type: 'value', name: small ? '' : '百分比 (%)', min: 0, max: 100, splitNumber: small ? 2 : 5, axisLabel: { fontSize: small ? 9 : 11, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#dce6f0', type: 'dashed' } } },
      { type: 'value', name: small ? '' : '延迟 (ms)', min: 0, splitNumber: small ? 2 : 5, alignTicks: true, axisLabel: { fontSize: small ? 9 : 11, formatter: small ? '{value} ms' : '{value}' }, splitLine: { show: false } }
    ],
    series: activeMetrics.value.map(metric => ({
      name: metric.name, type: 'line', yAxisIndex: metric.axis || 0, smooth: true, clip: false,
      data: props.points.map(point => metric.key === 'avg_rtt' && isTimeout(point) ? null : point?.[metric.key]),
      showSymbol: props.points.length <= (props.compact || narrow ? 12 : 35), symbol: 'circle', symbolSize: small ? 4 : 6,
      lineStyle: { width: small ? 1.7 : 2.5 }, itemStyle: { color: metric.color },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
        { offset: 0, color: `rgba(${metric.rgb}, ${metric.axis ? 0.22 : 0.28})` },
        { offset: 1, color: `rgba(${metric.rgb}, 0.015)` }
      ] } },
      tooltip: { valueFormatter: value => value == null ? '—' : `${value}${metric.unit}` }
    }))
  })
}
watch(() => props.points, draw, { flush: 'post' })
watch(chartDom, (element, _, onCleanup) => {
  if (!element) return
  const observer = new ResizeObserver(draw)
  observer.observe(element)
  onCleanup(() => observer.disconnect())
}, { flush: 'post' })
onBeforeUnmount(() => chart?.dispose())
</script>

<style scoped>
.monitor-trend { position: relative; display: grid; flex: 1 1 0; min-height: 0; min-width: 0; overflow: hidden; }
.monitor-trend__canvas { position: absolute; inset: 0; }
.monitor-trend__empty { align-self: center; justify-self: center; color: #64748b; font-size: 13px; }
.monitor-trend__notice { position: absolute; right: 4px; bottom: 2px; z-index: 2; color: #98a2b3; font-size: 10px; }
</style>
