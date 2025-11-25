<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
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
      <el-col :span="6">
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
      <el-col :span="6">
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
      <el-col :span="6">
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
          <el-button type="primary" size="small" @click="loadData" :loading="loading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      <el-table :data="dashboard.host_status" style="width: 100%">
        <el-table-column prop="name" label="主机名称" width="150" />
        <el-table-column label="地址" width="200">
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
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === '正常'" type="success">{{ row.status }}</el-tag>
            <el-tag v-else-if="row.status === '异常'" type="danger">{{ row.status }}</el-tag>
            <el-tag v-else type="info">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="丢包率" width="120">
          <template #default="{ row }">
            <span v-if="row.packet_loss !== null">{{ row.packet_loss }}%</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="平均延迟" width="120">
          <template #default="{ row }">
            <span v-if="row.avg_rtt !== null">{{ row.avg_rtt }}ms</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="最后检查" min-width="180">
          <template #default="{ row }">
            <span v-if="row.last_check">{{ formatTime(row.last_check) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewChart(row)">查看图表</el-button>
            <el-button type="success" size="small" @click="pingHost(row)">立即Ping</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 监控图表对话框 -->
    <el-dialog v-model="chartVisible" :title="`${selectedHost?.name} 监控数据`" width="80%">
      <div ref="chartDom" style="width: 100%; height: 400px"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import * as echarts from 'echarts'

const loading = ref(false)
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

const onlineRate = computed(() => {
  if (dashboard.total_hosts === 0) return 0
  const online = dashboard.host_status.filter(h => h.status === '正常').length
  return Math.round((online / dashboard.total_hosts) * 100)
})

const loadData = async () => {
  loading.value = true
  try {
    const data = await api.getDashboard()
    Object.assign(dashboard, data)
    // 加载整体监控数据
    await loadOverallChart()
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const loadOverallChart = async () => {
  try {
    // 获取最近的ping日志，不分组，直接按时间显示
    const response = await api.getPingLogs(null, 1, 50) // 获取最近50条记录
    const logs = response.items || []
    
    if (logs.length === 0) {
      renderOverallChart([], [], [])
      return
    }
    
    // 按时间分组，每次检测的数据汇总（同一时间点的所有主机）
    const timeMap = new Map()
    
    logs.forEach(log => {
      const time = new Date(log.check_time)
      const timeKey = `${time.getMonth()+1}/${time.getDate()} ${String(time.getHours()).padStart(2, '0')}:${String(time.getMinutes()).padStart(2, '0')}`
      
      if (!timeMap.has(timeKey)) {
        timeMap.set(timeKey, {
          packet_loss_sum: 0,
          avg_rtt_sum: 0,
          count: 0,
          timestamp: time.getTime()
        })
      }
      
      const data = timeMap.get(timeKey)
      data.packet_loss_sum += log.packet_loss
      data.avg_rtt_sum += log.avg_rtt || 0
      data.count += 1
    })
    
    // 计算平均值并按时间排序
    const sortedEntries = Array.from(timeMap.entries())
      .sort((a, b) => a[1].timestamp - b[1].timestamp)
      .slice(-30) // 只显示最近30个数据点
    
    const times = []
    const avgPacketLoss = []
    const avgRtt = []
    
    sortedEntries.forEach(([time, data]) => {
      times.push(time)
      avgPacketLoss.push((data.packet_loss_sum / data.count).toFixed(2))
      avgRtt.push((data.avg_rtt_sum / data.count).toFixed(2))
    })
    
    renderOverallChart(times, avgPacketLoss, avgRtt)
  } catch (error) {
    console.error('加载整体监控数据失败:', error)
  }
}

const renderOverallChart = (times, packetLoss, avgRtt) => {
  if (!overallChartDom.value) return
  
  if (overallChartInstance) {
    overallChartInstance.dispose()
  }
  
  overallChartInstance = echarts.init(overallChartDom.value)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['平均丢包率(%)', '平均延迟(ms)'],
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
        interval: 0
      },
      boundaryGap: false
    },
    yAxis: [
      {
        type: 'value',
        name: '丢包率(%)',
        position: 'left',
        axisLine: {
          lineStyle: {
            color: '#f56c6c'
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
  }
  
  overallChartInstance.setOption(option)
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
  if (!chartDom.value) return
  
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  chartInstance = echarts.init(chartDom.value)
  
  const times = records.map(r => new Date(r.created_at).toLocaleString()).reverse()
  const packetLoss = records.map(r => r.packet_loss).reverse()
  const avgRtt = records.map(r => r.avg_rtt || 0).reverse()
  
  const option = {
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
  }
  
  chartInstance.setOption(option)
}

const formatTime = (time) => {
  return new Date(time).toLocaleString()
}

watch(chartVisible, (val) => {
  if (!val && chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

onMounted(() => {
  loadData()
  // 每30秒自动刷新
  setInterval(loadData, 30000)
  
  // 监听窗口大小变化，重绘图表
  window.addEventListener('resize', () => {
    if (overallChartInstance) {
      overallChartInstance.resize()
    }
  })
})
</script>
