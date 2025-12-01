<template>
  <div>
    <!-- 时间范围选择器 -->
    <el-card shadow="hover" style="margin-bottom: 20px">
      <el-radio-group v-model="selectedTimeRange" size="large" @change="handleTimeRangeChange">
        <el-radio-button label="1h">过去1小时</el-radio-button>
        <el-radio-button label="1d">过去1天</el-radio-button>
        <el-radio-button label="3d">过去3天</el-radio-button>
        <el-radio-button label="7d">过去7天</el-radio-button>
        <el-radio-button label="15d">过去15天</el-radio-button>
        <el-radio-button label="30d">过去30天</el-radio-button>
      </el-radio-group>
      <el-button type="primary" style="margin-left: 20px" :loading="loading" @click="loadData">
        <el-icon><Refresh /></el-icon> 刷新数据
      </el-button>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">监控主机数</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px">{{ stats.total_hosts }}</div>
            </div>
            <el-icon :size="40" color="#409eff"><Monitor /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">平均在线率</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px; color: #67c23a">{{ stats.avg_online_rate }}%</div>
            </div>
            <el-icon :size="40" color="#67c23a"><SuccessFilled /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">平均延迟</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px; color: #409eff">{{ stats.avg_rtt }}ms</div>
            </div>
            <el-icon :size="40" color="#409eff"><Timer /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="display: flex; justify-content: space-between; align-items: center">
            <div>
              <div style="font-size: 14px; color: #909399">平均丢包率</div>
              <div style="font-size: 28px; font-weight: bold; margin-top: 10px; color: #f56c6c">{{ stats.avg_packet_loss }}%</div>
            </div>
            <el-icon :size="40" color="#f56c6c"><WarningFilled /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 整体趋势图 -->
    <el-card shadow="hover" style="margin-bottom: 20px">
      <template #header>
        <span style="font-weight: bold">整体趋势（{{ timeRangeText }}）</span>
      </template>
      <div ref="trendChartDom" style="width: 100%; height: 400px"></div>
    </el-card>

    <!-- 主机列表 -->
    <el-card shadow="hover" style="margin-bottom: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: bold">主机统计数据（{{ timeRangeText }}）</span>
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
        </div>
      </template>
      
      <el-table :data="filteredHostData" style="width: 100%" v-loading="loading">
        <el-table-column label="序号" width="70" align="center" header-align="center">
          <template #default="{ $index }">
            {{ (currentPage - 1) * pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="name" label="主机名称" min-width="120" align="center" header-align="center" />
        <el-table-column prop="address" label="地址" min-width="150" align="center" header-align="center" />
        <el-table-column label="监控次数" min-width="90" align="center" header-align="center">
          <template #default="{ row }">
            {{ row.check_count }}
          </template>
        </el-table-column>
        <el-table-column label="在线率" min-width="90" align="center" header-align="center" sortable :sort-method="(a, b) => a.online_rate - b.online_rate">
          <template #default="{ row }">
            <el-tag :type="getOnlineRateType(row.online_rate)">{{ row.online_rate }}%</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="平均丢包率" min-width="100" align="center" header-align="center" sortable :sort-method="(a, b) => a.avg_packet_loss - b.avg_packet_loss">
          <template #default="{ row }">
            <span :style="{ color: row.avg_packet_loss > 10 ? '#f56c6c' : '#67c23a' }">{{ row.avg_packet_loss }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="平均延迟" min-width="90" align="center" header-align="center" sortable :sort-method="(a, b) => a.avg_rtt - b.avg_rtt">
          <template #default="{ row }">
            <span :style="{ color: row.avg_rtt > 100 ? '#e6a23c' : '#67c23a' }">{{ row.avg_rtt }}ms</span>
          </template>
        </el-table-column>
        <el-table-column label="最小延迟" min-width="90" align="center" header-align="center">
          <template #default="{ row }">
            {{ row.min_rtt }}ms
          </template>
        </el-table-column>
        <el-table-column label="最大延迟" min-width="90" align="center" header-align="center">
          <template #default="{ row }">
            {{ row.max_rtt }}ms
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" header-align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewHostChart(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div style="margin-top: 15px; display: flex; justify-content: center">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredAllHostData.length"
          layout="total, sizes, prev, pager, next, jumper"
          :small="true"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 主机详情对话框 -->
    <el-dialog v-model="chartVisible" :title="`${selectedHost?.name} 详细数据（${timeRangeText}）`" width="80%">
      <div ref="hostChartDom" style="width: 100%; height: 400px"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import * as echarts from 'echarts'

const loading = ref(false)
const selectedTimeRange = ref('1d')
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const stats = reactive({
  total_hosts: 0,
  avg_online_rate: 0,
  avg_rtt: 0,
  avg_packet_loss: 0
})

const hostData = ref([])
const chartVisible = ref(false)
const selectedHost = ref(null)
const trendChartDom = ref(null)
const hostChartDom = ref(null)
let trendChartInstance = null
let hostChartInstance = null

const timeRangeText = computed(() => {
  const rangeMap = {
    '1h': '过去1小时',
    '1d': '过去1天',
    '3d': '过去3天',
    '7d': '过去7天',
    '15d': '过去15天',
    '30d': '过去30天'
  }
  return rangeMap[selectedTimeRange.value] || ''
})

// 搜索过滤后的所有数据
const filteredAllHostData = computed(() => {
  if (!searchKeyword.value) return hostData.value
  
  const keyword = searchKeyword.value.toLowerCase()
  return hostData.value.filter(host => 
    host.name.toLowerCase().includes(keyword) || 
    host.address.toLowerCase().includes(keyword)
  )
})

// 当前页显示的数据
const filteredHostData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredAllHostData.value.slice(start, end)
})

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

const getOnlineRateType = (rate) => {
  if (rate >= 95) return 'success'
  if (rate >= 80) return 'warning'
  return 'danger'
}

const handleTimeRangeChange = () => {
  currentPage.value = 1
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await api.getDataBoardStats(selectedTimeRange.value)
    
    // 更新统计数据
    stats.total_hosts = data.total_hosts
    stats.avg_online_rate = data.avg_online_rate
    stats.avg_rtt = data.avg_rtt
    stats.avg_packet_loss = data.avg_packet_loss
    
    // 更新主机数据
    hostData.value = data.host_stats
    
    // 加载整体趋势图
    await nextTick()
    renderTrendChart(data.trend_data)
  } catch (error) {
    ElMessage.error('加载数据失败')
    console.error('加载数据看板失败:', error)
  } finally {
    loading.value = false
  }
}

const renderTrendChart = (trendData) => {
  if (!trendChartDom.value) return
  
  if (trendChartInstance) {
    trendChartInstance.dispose()
  }
  
  trendChartInstance = echarts.init(trendChartDom.value)
  
  const times = trendData.map(d => d.time)
  const avgPacketLoss = trendData.map(d => d.avg_packet_loss)
  const avgRtt = trendData.map(d => d.avg_rtt)
  const onlineRate = trendData.map(d => d.online_rate)
  
  const option = {
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
        data: onlineRate,
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
        data: avgPacketLoss,
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
  
  trendChartInstance.setOption(option)
}

const viewHostChart = async (host) => {
  selectedHost.value = host
  chartVisible.value = true
  
  await nextTick()
  
  try {
    const data = await api.getHostDetailStats(host.id, selectedTimeRange.value)
    renderHostChart(data)
  } catch (error) {
    ElMessage.error('加载主机详细数据失败')
  }
}

const renderHostChart = (data) => {
  if (!hostChartDom.value) return
  
  if (hostChartInstance) {
    hostChartInstance.dispose()
  }
  
  hostChartInstance = echarts.init(hostChartDom.value)
  
  const times = data.map(d => d.time)
  const packetLoss = data.map(d => d.packet_loss)
  const avgRtt = data.map(d => d.avg_rtt)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['丢包率(%)', '平均延迟(ms)']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '12%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: {
        rotate: 45,
        interval: 'auto'
      }
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
        }
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
  
  hostChartInstance.setOption(option)
}

watch(chartVisible, (val) => {
  if (!val && hostChartInstance) {
    hostChartInstance.dispose()
    hostChartInstance = null
  }
})

onMounted(() => {
  loadData()
  
  // 监听窗口大小变化
  window.addEventListener('resize', () => {
    if (trendChartInstance) {
      trendChartInstance.resize()
    }
  })
})

onBeforeUnmount(() => {
  if (trendChartInstance) {
    trendChartInstance.dispose()
    trendChartInstance = null
  }
  if (hostChartInstance) {
    hostChartInstance.dispose()
    hostChartInstance = null
  }
})
</script>

<style scoped>
</style>
