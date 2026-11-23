<template>
  <el-dialog v-model="visible" :title="title" :fullscreen="isMobile" width="min(760px, 92vw)" append-to-body>
    <div class="history-panel" v-loading="loading">
      <MonitorTrend :points="chartPoints" :loading="loading" :show-online-rate="false" :empty-text="error || '这段时间没有监控记录'" />
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import api from '../api'
import MonitorTrend from './MonitorTrend.vue'
import { useViewport } from '../lib/useViewport'

const { isMobile } = useViewport()
const visible = ref(false)
const title = ref('')
const loading = ref(false)
const error = ref('')
const points = ref([])
let request = 0
const chartPoints = computed(() => points.value.map(point => ({ ...point, avg_packet_loss: point.packet_loss })))

const open = async (host, range = '1d', period = '近 24 小时') => {
  const id = ++request
  title.value = `${host.name} · ${period}`
  points.value = []
  error.value = ''
  loading.value = true
  visible.value = true
  try {
    const data = await api.getHostDetailStats(host.id, range)
    if (id === request) points.value = data
  } catch {
    if (id === request) error.value = '主机详情加载失败，请重新打开'
  } finally {
    if (id === request) {
      loading.value = false
    }
  }
}

defineExpose({ open })
</script>

<style scoped>
.history-panel { min-height: min(260px, 60dvh); }
:deep(.monitor-trend) { width: 100%; height: clamp(178px, 55dvh, 410px); }
</style>
