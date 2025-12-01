<template>
  <div>
    <!-- 筛选和操作栏 -->
    <el-card shadow="hover" style="margin-bottom: 20px">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div style="display: flex; gap: 10px">
          <el-select v-model="logTypeFilter" placeholder="日志类型" clearable style="width: 150px" @change="loadLogs">
            <el-option label="全部" value="" />
            <el-option label="信息" value="info" />
            <el-option label="警告" value="warning" />
            <el-option label="错误" value="error" />
            <el-option label="数据清理" value="cleanup" />
            <el-option label="数据聚合" value="aggregate" />
          </el-select>
          <el-select v-model="moduleFilter" placeholder="模块" clearable style="width: 200px" @change="loadLogs">
            <el-option label="全部" value="" />
            <el-option label="数据维护" value="data_maintenance" />
            <el-option label="监控调度" value="scheduler" />
          </el-select>
          <el-button type="primary" @click="loadLogs" :loading="loading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
        <div style="display: flex; gap: 10px">
          <!-- 数据维护操作 -->
          <el-dropdown>
            <el-button type="success">
              数据维护操作<el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleHourlyAggregation">
                  <el-icon><TrendCharts /></el-icon> 执行小时级聚合
                </el-dropdown-item>
                <el-dropdown-item @click="handleDailyAggregation">
                  <el-icon><DataAnalysis /></el-icon> 执行日级聚合
                </el-dropdown-item>
                <el-dropdown-item @click="handleDataCleanup" divided>
                  <el-icon><Delete /></el-icon> 执行数据清理
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          
          <el-popconfirm
            title="确定要清理30天前的系统日志吗？"
            confirm-button-text="确定"
            cancel-button-text="取消"
            @confirm="handleCleanupLogs"
          >
            <template #reference>
              <el-button type="danger" :loading="cleanupLoading">
                <el-icon><Delete /></el-icon> 清理旧日志
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </el-card>

    <!-- 日志列表 -->
    <el-card shadow="hover">
      <template #header>
        <span style="font-weight: bold">系统日志</span>
      </template>
      
      <el-table :data="logs" style="width: 100%" v-loading="loading">
        <el-table-column label="序号" width="70" align="center" header-align="center">
          <template #default="{ $index }">
            {{ (currentPage - 1) * pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column label="时间" width="180" align="center" header-align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag :type="getLogTypeTag(row.log_type)">{{ getLogTypeText(row.log_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="150" align="center" header-align="center" />
        <el-table-column prop="message" label="消息" min-width="300" show-overflow-tooltip />
        <el-table-column label="操作" width="100" align="center" header-align="center">
          <template #default="{ row }">
            <el-button v-if="row.details" type="primary" size="small" @click="viewDetails(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div style="margin-top: 15px; display: flex; justify-content: center">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          :small="true"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailsVisible" title="日志详情" width="60%">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="时间">{{ formatTime(selectedLog?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="类型">
          <el-tag :type="getLogTypeTag(selectedLog?.log_type)">{{ getLogTypeText(selectedLog?.log_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="模块">{{ selectedLog?.module }}</el-descriptions-item>
        <el-descriptions-item label="消息">{{ selectedLog?.message }}</el-descriptions-item>
        <el-descriptions-item label="详细信息">
          <pre style="max-height: 300px; overflow-y: auto; background: #f5f5f5; padding: 10px; border-radius: 4px">{{ formatDetails(selectedLog?.details) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const loading = ref(false)
const cleanupLoading = ref(false)
const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const logTypeFilter = ref('')
const moduleFilter = ref('')
const detailsVisible = ref(false)
const selectedLog = ref(null)

const loadLogs = async () => {
  loading.value = true
  try {
    const data = await api.getSystemLogs(
      logTypeFilter.value || null,
      moduleFilter.value || null,
      currentPage.value,
      pageSize.value
    )
    logs.value = data.items
    total.value = data.total
  } catch (error) {
    ElMessage.error('加载系统日志失败')
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  loadLogs()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadLogs()
}

const handleCleanupLogs = async () => {
  cleanupLoading.value = true
  try {
    const result = await api.cleanupSystemLogs(30)
    ElMessage.success(result.message)
    loadLogs()
  } catch (error) {
    ElMessage.error('清理日志失败')
  } finally {
    cleanupLoading.value = false
  }
}

const handleHourlyAggregation = async () => {
  loading.value = true
  try {
    const result = await api.triggerHourlyAggregation()
    ElMessage.success(result.message)
    setTimeout(() => loadLogs(), 1000)
  } catch (error) {
    ElMessage.error('执行失败：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleDailyAggregation = async () => {
  loading.value = true
  try {
    const result = await api.triggerDailyAggregation()
    ElMessage.success(result.message)
    setTimeout(() => loadLogs(), 1000)
  } catch (error) {
    ElMessage.error('执行失败：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleDataCleanup = async () => {
  loading.value = true
  try {
    const result = await api.triggerDataCleanup()
    ElMessage.success(result.message)
    setTimeout(() => loadLogs(), 1000)
  } catch (error) {
    ElMessage.error('执行失败：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const viewDetails = (log) => {
  selectedLog.value = log
  detailsVisible.value = true
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

const getLogTypeText = (type) => {
  const typeMap = {
    'info': '信息',
    'warning': '警告',
    'error': '错误',
    'cleanup': '清理',
    'aggregate': '聚合'
  }
  return typeMap[type] || type
}

const getLogTypeTag = (type) => {
  const tagMap = {
    'info': 'info',
    'warning': 'warning',
    'error': 'danger',
    'cleanup': 'success',
    'aggregate': 'success'
  }
  return tagMap[type] || 'info'
}

const formatDetails = (details) => {
  if (!details) return '无'
  try {
    const obj = JSON.parse(details)
    return JSON.stringify(obj, null, 2)
  } catch {
    return details
  }
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
</style>
