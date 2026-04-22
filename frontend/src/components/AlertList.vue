<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap">
          <span style="font-weight: bold">告警记录</span>
          <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索主机名称或告警内容"
              clearable
              style="width: 260px"
              @clear="handleFilterChange"
              @keyup.enter="handleFilterChange"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select v-model="timeRange" placeholder="时间范围" style="width: 140px" @change="handleFilterChange">
              <el-option label="最近1小时" :value="1" />
              <el-option label="最近6小时" :value="6" />
              <el-option label="最近24小时" :value="24" />
              <el-option label="最近7天" :value="168" />
            </el-select>
            <el-select v-model="alertTypeFilter" placeholder="告警类型" clearable style="width: 140px" @change="handleFilterChange">
              <el-option label="丢包告警" value="packet_loss" />
              <el-option label="主机不可达" value="unreachable" />
            </el-select>
            <el-select v-model="sentStatusFilter" placeholder="发送状态" clearable style="width: 130px" @change="handleFilterChange">
              <el-option label="已发送" value="sent" />
              <el-option label="未发送" value="unsent" />
            </el-select>
            <el-button type="primary" :loading="loading" @click="loadAlerts">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="alerts" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" align="center" header-align="center" />
        <el-table-column prop="host_name" label="主机名称" width="160" align="center" header-align="center" />
        <el-table-column label="告警类型" width="120" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag v-if="row.alert_type === 'packet_loss'" type="warning">丢包告警</el-tag>
            <el-tag v-else-if="row.alert_type === 'unreachable'" type="danger">主机不可达</el-tag>
            <el-tag v-else type="info">{{ row.alert_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="告警信息" min-width="320" align="center" header-align="center">
          <template #default="{ row }">
            <div style="word-wrap: break-word; word-break: break-all; text-align: left">{{ cleanMarkdown(row.message) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="发送状态" width="100" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_sent" type="success">已发送</el-tag>
            <el-tag v-else type="info">未发送</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="告警时间" width="180" align="center" header-align="center">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
      </el-table>

      <div v-if="alerts.length === 0 && !loading" style="text-align: center; padding: 40px; color: #909399">
        <el-icon :size="60"><CircleCheck /></el-icon>
        <div style="margin-top: 10px; font-size: 16px">当前筛选条件下暂无告警记录</div>
      </div>

      <div v-if="totalAlerts > 0" style="margin-top: 20px; text-align: right">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="totalAlerts"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const alerts = ref([])
const loading = ref(false)
const timeRange = ref(24)
const searchKeyword = ref('')
const alertTypeFilter = ref('')
const sentStatusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalAlerts = ref(0)

const loadAlerts = async () => {
  loading.value = true
  try {
    const data = await api.getAlerts(
      timeRange.value,
      currentPage.value,
      pageSize.value,
      searchKeyword.value.trim() || null,
      alertTypeFilter.value || null,
      sentStatusFilter.value || null
    )
    alerts.value = data.items || []
    totalAlerts.value = data.total || 0
  } catch (error) {
    ElMessage.error('加载告警记录失败')
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  currentPage.value = 1
  loadAlerts()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  loadAlerts()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadAlerts()
}

const cleanMarkdown = (text) => {
  if (!text) return ''

  let result = text
    .replace(/^###\s+/gm, '')
    .replace(/^>\s+/gm, '')
    .replace(/^---$/gm, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/<font\s+color=[^>]+>([^<]*)<\/font>/gi, '$1')
    .replace(/主机异常告警/g, '')
    .replace(/主机恢复正常/g, '')
    .replace(/告警级别：/g, '')
    .replace(/状态：/g, '')
    .replace(/严重/g, '')
    .replace(/警告/g, '')
    .replace(/提醒/g, '')
    .replace(/已恢复/g, '')
    .replace(/\u2705/g, '')
    .replace(/\n+/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim()

  const emojiPattern = /[\u{1F534}\u{1F7E0}\u{1F7E1}]/gu
  const emojis = result.match(emojiPattern)
  if (emojis && emojis.length > 1) {
    const firstEmoji = emojis[0]
    result = result.replace(emojiPattern, (match, offset) => {
      return offset === result.indexOf(firstEmoji) ? match : ''
    })
  }

  return result.replace(/\s{2,}/g, ' ').trim()
}

onMounted(() => {
  loadAlerts()
})
</script>
