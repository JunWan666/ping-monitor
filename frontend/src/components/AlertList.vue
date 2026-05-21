<template>
  <div class="alert-list-page">
    <div v-if="isMobile" class="alert-mobile">
      <el-card shadow="never" class="alert-mobile__toolbar">
        <div class="alert-mobile__chips-row">
          <button
            v-for="item in mobileSeverityOptions"
            :key="item.key"
            type="button"
            class="alert-mobile__chip"
            :class="{ active: mobileSeverityFilter === item.key }"
            @click="mobileSeverityFilter = item.key"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="alert-mobile__filter-row">
          <button type="button" class="alert-mobile__filter-btn" @click="mobileFilterPanelVisible = !mobileFilterPanelVisible">
            <el-icon><Search /></el-icon>
            <span>{{ mobileFilterPanelVisible ? '收起筛选' : '筛选条件' }}</span>
          </button>
        </div>
        <div v-if="mobileFilterPanelVisible" class="alert-mobile__panel">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索主机名称或告警内容"
            clearable
            @clear="handleFilterChange"
            @keyup.enter="handleFilterChange"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="timeRange" placeholder="时间范围" @change="handleFilterChange">
            <el-option label="最近1小时" :value="1" />
            <el-option label="最近6小时" :value="6" />
            <el-option label="最近24小时" :value="24" />
            <el-option label="最近7天" :value="168" />
          </el-select>
          <el-select v-model="alertTypeFilter" placeholder="告警类型" clearable @change="handleFilterChange">
            <el-option label="丢包告警" value="packet_loss" />
            <el-option label="主机不可达" value="unreachable" />
          </el-select>
          <el-select v-model="sentStatusFilter" placeholder="发送状态" clearable @change="handleFilterChange">
            <el-option label="已发送" value="sent" />
            <el-option label="未发送" value="unsent" />
          </el-select>
        </div>
      </el-card>

      <div class="alert-mobile__summary-row">
        <span>共 {{ mobileAlerts.length }} 条告警</span>
        <el-select v-model="mobileSortOrder" size="small" class="alert-mobile__sort" @change="() => {}">
          <el-option label="按时间倒序" value="desc" />
          <el-option label="按时间正序" value="asc" />
        </el-select>
      </div>

      <div class="alert-mobile__scroll">
        <el-empty v-if="mobileAlertGroups.length === 0 && !loading" description="暂无告警" :image-size="72" />

        <el-collapse v-else v-model="mobileCollapseActive" class="alert-mobile__groups">
          <el-collapse-item
            v-for="group in mobileAlertGroups"
            :key="group.key"
            :name="group.key"
            class="alert-mobile__group"
          >
            <template #title>
              <div class="alert-mobile__group-title">
                <span class="alert-mobile__group-bar" :class="`is-${group.color}`"></span>
                <span>{{ group.title }} ({{ group.items.length }})</span>
              </div>
            </template>

            <div class="alert-mobile__group-list">
              <div v-for="row in group.items" :key="row.id" class="alert-mobile__card">
                <div class="alert-mobile__head">
                  <div class="alert-mobile__dot-and-text">
                    <span class="alert-mobile__dot" :class="`is-${group.color}`"></span>
                    <div class="alert-mobile__text-block">
                      <div class="alert-mobile__name">{{ row.host_name }}</div>
                      <div class="alert-mobile__message">{{ cleanMarkdown(row.message) }}</div>
                      <div class="alert-mobile__time">{{ new Date(row.created_at).toLocaleString() }}</div>
                    </div>
                  </div>
                  <el-tag :type="group.color" effect="plain" size="small">{{ group.title }}</el-tag>
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <div class="alert-mobile__pager">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="totalAlerts"
          layout="prev, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          background
        />
      </div>
    </div>

    <template v-else>
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
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useViewport } from '../lib/useViewport'

const alerts = ref([])
const loading = ref(false)
const timeRange = ref(24)
const searchKeyword = ref('')
const alertTypeFilter = ref('')
const sentStatusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalAlerts = ref(0)
const mobileSeverityFilter = ref('all')
const mobileFilterPanelVisible = ref(false)
const mobileSortOrder = ref('desc')
const mobileCollapseActive = ref(['urgent', 'important', 'warning', 'recovered'])
const { isMobile } = useViewport()

const severityOrder = ['urgent', 'important', 'warning', 'recovered']

const getAlertSeverity = (row) => {
  const message = `${row?.message || ''} ${row?.alert_type || ''}`.toLowerCase()
  if (row?.alert_type === 'unreachable' || message.includes('离线') || message.includes('不可达')) {
    return 'urgent'
  }
  if (message.includes('丢包')) {
    return 'important'
  }
  if (message.includes('恢复') || message.includes('恢复正常')) {
    return 'recovered'
  }
  return 'warning'
}

const mobileSeverityOptions = [
  { key: 'all', label: '全部' },
  { key: 'urgent', label: '紧急' },
  { key: 'important', label: '重要' },
  { key: 'warning', label: '警告' },
  { key: 'recovered', label: '恢复' }
]

const mobileAlerts = computed(() => {
  let items = [...alerts.value]
  if (mobileSeverityFilter.value !== 'all') {
    items = items.filter((item) => getAlertSeverity(item) === mobileSeverityFilter.value)
  }
  return items.sort((a, b) => {
    const aTime = new Date(a.created_at).getTime()
    const bTime = new Date(b.created_at).getTime()
    return mobileSortOrder.value === 'asc' ? aTime - bTime : bTime - aTime
  })
})

const mobileAlertGroups = computed(() => {
  const groups = new Map()
  for (const row of mobileAlerts.value) {
    const key = getAlertSeverity(row)
    if (!groups.has(key)) {
      groups.set(key, [])
    }
    groups.get(key).push(row)
  }

  return severityOrder
    .map((key) => ({
      key,
      title: {
        urgent: '紧急',
        important: '重要',
        warning: '警告',
        recovered: '恢复'
      }[key],
      color: {
        urgent: 'danger',
        important: 'warning',
        warning: 'warning',
        recovered: 'success'
      }[key],
      items: groups.get(key) || []
    }))
    .filter((group) => group.items.length > 0)
})

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

<style scoped>
.alert-list-page {
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
}

.alert-mobile {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  overflow-x: clip;
}

.alert-mobile :deep(.el-card__body) {
  min-width: 0;
}

.alert-mobile__toolbar {
  border-radius: 14px;
  flex: 0 0 auto;
}

.alert-mobile__chips-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
}

.alert-mobile__chip {
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #fff;
  color: #4b5563;
  height: 34px;
  padding: 0 8px;
  font-size: 12px;
  white-space: nowrap;
}

.alert-mobile__chip.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 700;
}

.alert-mobile__filter-row {
  margin-top: 10px;
}

.alert-mobile__filter-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 36px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 13px;
  font-weight: 700;
}

.alert-mobile__panel {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin-top: 12px;
}

.alert-mobile__summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex: 0 0 auto;
  font-size: 12px;
  color: #6b7280;
  min-width: 0;
}

.alert-mobile__sort {
  width: min(126px, 48%);
  flex: 0 0 auto;
}

.alert-mobile__scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.alert-mobile__groups {
  border: none;
}

.alert-mobile__group {
  margin-bottom: 10px;
  overflow: hidden;
  border: 1px solid #edf2f7;
  border-radius: 14px;
  background: #fff;
}

.alert-mobile__group :deep(.el-collapse-item__header) {
  padding: 0 12px;
  border-bottom: none;
  font-weight: 700;
}

.alert-mobile__group :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.alert-mobile__group :deep(.el-collapse-item__content) {
  padding: 0 12px 12px;
}

.alert-mobile__group-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-mobile__group-bar,
.alert-mobile__dot {
  display: inline-block;
  border-radius: 999px;
  flex: 0 0 auto;
}

.alert-mobile__group-bar {
  width: 4px;
  height: 16px;
}

.alert-mobile__dot {
  width: 9px;
  height: 9px;
  margin-top: 5px;
}

.alert-mobile__group-bar.is-danger,
.alert-mobile__dot.is-danger {
  background: #f56c6c;
}

.alert-mobile__group-bar.is-warning,
.alert-mobile__dot.is-warning {
  background: #e6a23c;
}

.alert-mobile__group-bar.is-success,
.alert-mobile__dot.is-success {
  background: #67c23a;
}

.alert-mobile__group-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-mobile__card {
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
}

.alert-mobile__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.alert-mobile__dot-and-text {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  flex: 1 1 auto;
}

.alert-mobile__text-block {
  min-width: 0;
}

.alert-mobile__name {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  overflow-wrap: anywhere;
}

.alert-mobile__time {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.alert-mobile__message {
  margin-top: 5px;
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.alert-mobile__pager {
  display: flex;
  justify-content: center;
  padding-top: 4px;
  flex: 0 0 auto;
  min-width: 0;
  overflow: hidden;
}

.alert-mobile__pager :deep(.el-pagination) {
  max-width: 100%;
  justify-content: center;
}
</style>
