<template>
  <el-dialog v-model="visible" :title="`Ping · ${host?.name || ''}`" width="min(570px, 92vw)" :fullscreen="isMobile" append-to-body @close="stop">
    <div class="quick-ping" aria-label="Ping 结果">
      <div class="quick-ping__status"><span>{{ host?.address }}</span><strong>{{ progress }} / 10</strong></div>
      <el-progress :percentage="progress * 10" :show-text="false" :status="error ? 'exception' : summary && !running ? 'success' : undefined" />
      <div class="quick-ping__packets">
        <div v-for="index in 10" :key="index" :class="packets[index]?.status">
          <span>{{ index }}</span><b>{{ packetLabel(packets[index]) }}</b>
        </div>
      </div>
      <p v-if="error" role="alert" class="quick-ping__error">{{ error }}</p>
      <p v-else-if="summary" role="status">已发送 {{ summary.packet_sent }} 次 · 收到 {{ summary.packet_received }} 次 · 丢包 {{ summary.packet_loss }}%<template v-if="summary.packet_received"> · 平均延迟 {{ summary.avg_rtt }} ms</template></p>
      <p v-else role="status">{{ running ? '正在检测…' : '检测已结束' }}</p>
    </div>
  </el-dialog>
  <HostHistoryDialog ref="history" />
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import api from '../api'
import { useViewport } from '../lib/useViewport'
import HostHistoryDialog from './HostHistoryDialog.vue'

const emit = defineEmits(['ping-complete'])
const { isMobile } = useViewport()
const history = ref(null)
const visible = ref(false)
const host = ref(null)
const packets = ref({})
const summary = ref(null)
const running = ref(false)
const error = ref('')
let source
const progress = computed(() => Object.keys(packets.value).length)
const stop = () => {
  source?.close()
  source = undefined
  running.value = false
}
const fail = (message) => {
  error.value = message
  stop()
}
const openPing = (row) => {
  stop()
  host.value = row
  packets.value = {}
  summary.value = null
  error.value = ''
  running.value = true
  visible.value = true
  try {
    source = api.pingStream(row.id, event => {
      if (event.type === 'ping') packets.value[event.sequence] = event
      if (event.type === 'summary') summary.value = event
      if (event.type === 'error') fail(event.message || 'Ping 失败')
    }, () => fail('Ping 连接中断，请重新测试'), () => {
      stop()
      emit('ping-complete')
    }, 'quick')
  } catch {
    fail('无法启动 Ping，请重新测试')
  }
}
const packetLabel = (event) => {
  if (!event) return '—'
  if (event.status === 'success') return `${event.delay} ms`
  return event.status === 'timeout' ? '超时' : '失败'
}
const openHistory = row => history.value.open(row)
onBeforeUnmount(stop)
defineExpose({ openPing, openHistory })
</script>

<style scoped>
.quick-ping { display: grid; gap: 12px; color: #475569; }
.quick-ping__status { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.quick-ping__status span { overflow-wrap: anywhere; }
.quick-ping__status strong { white-space: nowrap; }
.quick-ping__packets { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 6px; }
.quick-ping__packets div { display: grid; gap: 3px; padding: 5px; border-radius: 5px; background: #f4f6f9; text-align: center; font-size: 12px; }
.quick-ping__packets .success { color: #18784d; background: #edf8f1; }
.quick-ping__packets .error, .quick-ping__packets .timeout, .quick-ping__error { color: #ad3039; }
</style>
