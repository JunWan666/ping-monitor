<template>
  <div class="database-backup">
    <el-alert
      title="导入会覆盖当前数据库，建议先导出一份最新备份。"
      type="warning"
      show-icon
      :closable="false"
      class="backup-alert"
    />

    <el-card v-if="exporting || exportStatus || downloadingExport" shadow="never" class="import-status-card">
      <template #header>
        <div class="card-header">
          <span>导出状态</span>
          <el-tag :type="exportStatusTag" effect="plain">{{ exportStatusText }}</el-tag>
        </div>
      </template>

      <el-progress
        v-if="exporting"
        :percentage="displayExportProgress"
        :status="displayExportProgressStatus"
      />

      <el-progress
        v-else-if="downloadingExport"
        :percentage="exportDownloadProgress"
        :status="undefined"
      />

      <el-progress
        v-else-if="exportStatus === 'failed' || exportStatus === 'completed'"
        :percentage="displayExportProgress"
        :status="displayExportProgressStatus"
      />

      <div class="import-meta">
        <span>{{ exportStageText }}</span>
        <span v-if="exportCurrentTable">当前表：{{ exportCurrentTable }}</span>
        <span v-if="exportFileSize">文件大小：{{ formatBytes(exportFileSize) }}</span>
      </div>

      <div class="export-hint">{{ exportHintText }}</div>

      <div class="export-actions">
        <el-button
          v-if="exportStatus === 'completed' && exportJobId"
          type="success"
          :loading="downloadingExport"
          :disabled="downloadingExport"
          @click="downloadExportFile"
        >
          <el-icon><Download /></el-icon>
          {{ downloadingExport ? `正在下载 ${exportDownloadProgress}%` : '下载 SQL 文件' }}
        </el-button>
      </div>

      <div ref="exportLogRef" class="import-log">
        <div v-for="(line, index) in exportLogs" :key="index" class="import-log-line">
          {{ line }}
        </div>
      </div>
    </el-card>

    <el-card v-if="importing || importStatus" shadow="never" class="import-status-card">
      <template #header>
        <div class="card-header">
          <span>导入状态</span>
          <el-tag :type="importStatusTag" effect="plain">{{ importStatusText }}</el-tag>
        </div>
      </template>

      <el-progress
        :percentage="importProgress"
        :status="importStatus === 'failed' ? 'exception' : importStatus === 'completed' ? 'success' : undefined"
      />

      <div class="import-meta">
        <span>{{ importStageText }}</span>
        <span v-if="importCurrentTable">当前表：{{ importCurrentTable }}</span>
      </div>

      <div ref="importLogRef" class="import-log">
        <div v-for="(line, index) in importLogs" :key="index" class="import-log-line">
          {{ line }}
        </div>
      </div>
    </el-card>

    <el-row :gutter="20" class="backup-grid">
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="backup-card">
          <template #header>
            <div class="card-header">
              <span>导出 SQL 备份</span>
              <el-tag type="success" effect="plain">完整数据</el-tag>
            </div>
          </template>

          <div class="backup-copy">
            导出当前系统的主机、Ping 记录、告警、配置、用户和系统日志，生成一个可恢复的 SQL 文件。
          </div>

          <el-button type="primary" :loading="exporting" :disabled="downloadingExport" @click="exportBackup">
            <el-icon><Download /></el-icon>
            导出整个 SQL 文件
          </el-button>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="backup-card">
          <template #header>
            <div class="card-header">
              <span>导入 SQL 备份</span>
              <el-tag type="danger" effect="plain">覆盖恢复</el-tag>
            </div>
          </template>

          <el-upload
            class="sql-upload"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :on-exceed="handleExceed"
            :file-list="fileList"
            :limit="1"
            :disabled="importing"
            accept=".sql"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">将 SQL 文件拖到此处，或<em>点击上传</em></div>
            <template #tip>
              <div class="upload-tip">仅支持本系统导出的 .sql 备份文件</div>
            </template>
          </el-upload>

          <div v-if="selectedFile" class="selected-file">
            <span>{{ selectedFile.name }}</span>
            <span>{{ selectedFileSize }}</span>
          </div>

          <el-button
            type="danger"
            :loading="importing"
            :disabled="!selectedFile || importing"
            @click="importBackup"
          >
            <el-icon><Upload /></el-icon>
            {{ importing ? '正在导入，请稍候...' : '导入并覆盖当前数据' }}
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const router = useRouter()
const ACTIVE_EXPORT_JOB_KEY = 'ping-monitor-active-export-job-id'
const ACTIVE_IMPORT_JOB_KEY = 'ping-monitor-active-import-job-id'
const IMPORT_SUMMARY_KEY = 'ping-monitor-import-summary'

const exporting = ref(false)
const importing = ref(false)
const exportJobId = ref('')
const exportStatus = ref('')
const exportStage = ref('')
const exportProgress = ref(0)
const exportLogs = ref([])
const exportCurrentTable = ref('')
const exportFileSize = ref(0)
const exportFilename = ref('')
const downloadingExport = ref(false)
const exportDownloadProgress = ref(0)
const exportLogRef = ref(null)
const importJobId = ref('')
const importStatus = ref('')
const importStage = ref('')
const importProgress = ref(0)
const importLogs = ref([])
const importCurrentTable = ref('')
const importLogRef = ref(null)
const exportPollTimer = ref(null)
const importPollTimer = ref(null)
const fileList = ref([])
const selectedFile = ref(null)
const resumingExport = ref(false)
const resumingImport = ref(false)
let componentUnmounted = false

const tableLabels = {
  hosts: '主机',
  ping_records: 'Ping记录',
  alerts: '告警',
  system_config: '系统配置',
  users: '用户',
  ping_statistics: '聚合统计',
  system_logs: '系统日志',
  datascreen_config: '可视化配置'
}

const stageLabels = {
  queued: '等待导入任务开始',
  preparing: '准备导入',
  validating: '校验备份文件',
  parsing: '解析 SQL 语句',
  executing: '写入数据库',
  verifying: '校验导入结果',
  post_import: '刷新运行配置',
  completed: '导入完成',
  failed: '导入失败'
}

const exportStageLabels = {
  queued: '等待导出任务开始',
  preparing: '准备导出',
  counting: '统计数据量',
  writing: '生成 SQL 文件',
  completed: '导出完成',
  failed: '导出失败'
}

const selectedFileSize = computed(() => formatBytes(selectedFile.value?.size || 0))
const exportStageText = computed(() => exportStageLabels[exportStage.value] || '准备中')
const exportStatusText = computed(() => {
  if (downloadingExport.value) return '正在下载'
  if (exportStatus.value === 'completed') return '待下载'
  if (exportStatus.value === 'failed') return '失败'
  if (exporting.value) return '进行中'
  return '待开始'
})
const exportStatusTag = computed(() => {
  if (downloadingExport.value) return 'info'
  if (exportStatus.value === 'completed') return 'success'
  if (exportStatus.value === 'failed') return 'danger'
  if (exporting.value) return 'warning'
  return 'info'
})
const displayExportProgress = computed(() => {
  if (downloadingExport.value) {
    return exportDownloadProgress.value
  }
  if (exportStatus.value === 'completed') {
    return 100
  }
  return exportProgress.value
})
const displayExportProgressStatus = computed(() => {
  if (exportStatus.value === 'failed') return 'exception'
  if (exportStatus.value === 'completed') return 'success'
  return undefined
})
const exportHintText = computed(() => {
  if (downloadingExport.value) {
    return 'SQL 文件正在下载到本地，请保持页面打开。'
  }
  if (exportStatus.value === 'completed') {
    return '文件已经生成，点击下方下载按钮保存到本地。'
  }
  if (exportStatus.value === 'failed') {
    return '导出失败，请查看日志后重新导出。'
  }
  if (exporting.value) {
    return '导出任务正在后台执行，请保持页面打开，不要刷新页面。'
  }
  return '等待导出任务开始。'
})
const importStageText = computed(() => stageLabels[importStage.value] || '准备中')
const importStatusText = computed(() => {
  if (importStatus.value === 'completed') return '完成'
  if (importStatus.value === 'failed') return '失败'
  if (importing.value) return '进行中'
  return '待开始'
})
const importStatusTag = computed(() => {
  if (importStatus.value === 'completed') return 'success'
  if (importStatus.value === 'failed') return 'danger'
  return 'warning'
})

const formatBytes = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

const buildTimestamp = () => {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate())
  ].join('') + '_' + [pad(now.getHours()), pad(now.getMinutes()), pad(now.getSeconds())].join('')
}

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

const getErrorMessage = (error) => {
  return error.response?.data?.detail || error.message || '网络错误'
}

const formatTableCounts = (counts = {}) => {
  return Object.entries(counts)
    .map(([tableName, count]) => `${tableLabels[tableName] || tableName}：${count}`)
    .join('\n')
}

const buildImportSummary = (result) => {
  const tableCounts = formatTableCounts(result.table_counts)
  return [
    `导入完成，已执行 ${result.executed_statements} 条 SQL 语句。`,
    '',
    tableCounts,
    '',
    '当前登录态可能已被备份中的用户数据替换，请重新登录。'
  ].filter(Boolean).join('\n')
}

const clearExportPollTimer = () => {
  if (exportPollTimer.value) {
    window.clearInterval(exportPollTimer.value)
    exportPollTimer.value = null
  }
}

const clearImportPollTimer = () => {
  if (importPollTimer.value) {
    window.clearInterval(importPollTimer.value)
    importPollTimer.value = null
  }
}

const rememberActiveExportJob = (jobId) => {
  if (jobId) {
    sessionStorage.setItem(ACTIVE_EXPORT_JOB_KEY, jobId)
    return
  }

  sessionStorage.removeItem(ACTIVE_EXPORT_JOB_KEY)
}

const rememberActiveImportJob = (jobId) => {
  if (jobId) {
    sessionStorage.setItem(ACTIVE_IMPORT_JOB_KEY, jobId)
    return
  }

  sessionStorage.removeItem(ACTIVE_IMPORT_JOB_KEY)
}

const scrollExportLogToBottom = async () => {
  await nextTick()
  if (exportLogRef.value) {
    exportLogRef.value.scrollTop = exportLogRef.value.scrollHeight
  }
}

const scrollImportLogToBottom = async () => {
  await nextTick()
  if (importLogRef.value) {
    importLogRef.value.scrollTop = importLogRef.value.scrollHeight
  }
}

const applyExportJob = (job) => {
  exportStatus.value = job.status || ''
  exportStage.value = job.stage || ''
  exportProgress.value = Number(job.progress || 0)
  exportLogs.value = job.logs || []
  exportCurrentTable.value = job.current_table || ''
  exportFileSize.value = Number(job.file_size || job.result?.file_size || 0)
  exportFilename.value = job.filename || job.result?.filename || exportFilename.value
}

const finishExport = async (job, notify = false) => {
  clearExportPollTimer()
  exporting.value = false
  downloadingExport.value = false
  exportDownloadProgress.value = 0

  if (job.status === 'failed') {
    rememberActiveExportJob('')
    ElMessage.error(`导出失败：${job.error || '未知错误'}`)
    return
  }

  if (job.status === 'completed') {
    exportProgress.value = 100
    exportStatus.value = 'completed'
    exportStage.value = 'completed'
    exportFilename.value = job.filename || exportFilename.value
    if (notify) {
      ElMessage.success('SQL 备份已导出完成，请点击下方下载按钮保存到本地')
    }
    return
  }
}

const pollExportStatus = async () => {
  if (!exportJobId.value) return

  try {
    const job = await api.getDatabaseExportStatus(exportJobId.value)
    const previousStatus = exportStatus.value
    applyExportJob(job)
    if (job.status === 'completed' || job.status === 'failed') {
      await finishExport(job, previousStatus !== job.status)
    }
  } catch (error) {
    clearExportPollTimer()
    exporting.value = false
    if (error.response?.status === 404) {
      rememberActiveExportJob('')
    }
    ElMessage.error(`获取导出状态失败：${getErrorMessage(error)}`)
  }
}

const startExportPolling = () => {
  clearExportPollTimer()
  exportPollTimer.value = window.setInterval(pollExportStatus, 1000)
  pollExportStatus()
}

const resumeActiveExportJob = async () => {
  if (exporting.value || downloadingExport.value || resumingExport.value) {
    return
  }

  let activeJobId = sessionStorage.getItem(ACTIVE_EXPORT_JOB_KEY)
  if (!activeJobId) {
    resumingExport.value = true
    try {
      const latestJob = await api.getLatestDatabaseExportStatus()
      activeJobId = latestJob.job_id
      rememberActiveExportJob(activeJobId)
      applyExportJob(latestJob)
    } catch (error) {
      return
    } finally {
      resumingExport.value = false
    }
  }

  if (!activeJobId || (exportJobId.value === activeJobId && exportPollTimer.value)) {
    return
  }

  try {
    const job = await api.getDatabaseExportStatus(activeJobId)
    exportJobId.value = activeJobId
    applyExportJob(job)

    if (job.status === 'queued' || job.status === 'running') {
      exporting.value = true
      exportStatus.value = job.status || 'queued'
      exportStage.value = job.stage || 'queued'
      exportLogs.value = exportLogs.value.length ? exportLogs.value : ['正在恢复后台导出任务进度...']
      startExportPolling()
      return
    }

    if (job.status === 'completed' || job.status === 'failed') {
      await finishExport(job, false)
    }
  } catch (error) {
    if (error.response?.status === 404) {
      rememberActiveExportJob('')
      exportJobId.value = ''
      return
    }

    console.error('恢复导出任务失败:', error)
  }
}

const downloadExportFile = async () => {
  if (!exportJobId.value || downloadingExport.value) {
    return
  }

  downloadingExport.value = true
  exportDownloadProgress.value = 0
  exportLogs.value = [...exportLogs.value, '正在下载 SQL 导出文件...']

  try {
    const blob = await api.downloadDatabaseExport(exportJobId.value, (event) => {
      if (event?.total) {
        exportDownloadProgress.value = Math.min(100, Math.round((event.loaded / event.total) * 100))
        return
      }

      if (event?.loaded) {
        exportDownloadProgress.value = Math.min(99, Math.max(exportDownloadProgress.value, 1))
      }
    })

    downloadBlob(blob, exportFilename.value || `ping_monitor_backup_${buildTimestamp()}.sql`)
    exportDownloadProgress.value = 100
    exportLogs.value = [...exportLogs.value, 'SQL 文件下载完成']
    ElMessage.success('SQL 备份下载完成')
  } catch (error) {
    exportDownloadProgress.value = 0
    ElMessage.error(`下载导出文件失败：${getErrorMessage(error)}`)
  } finally {
    downloadingExport.value = false
  }
}

const applyImportJob = (job) => {
  importStatus.value = job.status || ''
  importStage.value = job.stage || ''
  importProgress.value = Number(job.progress || 0)
  importLogs.value = job.logs || []
  importCurrentTable.value = job.current_table || ''
}

const finishImport = async (job) => {
  clearImportPollTimer()
  importing.value = false
  rememberActiveImportJob('')

  if (job.status === 'failed') {
    ElMessage.error(`导入失败：${job.error || '未知错误'}`)
    return
  }

  const importSummary = buildImportSummary(job.result || {})
  sessionStorage.setItem(IMPORT_SUMMARY_KEY, importSummary)
  try {
    await ElMessageBox.alert(importSummary, '导入完成', {
      confirmButtonText: '重新登录',
      type: 'success',
      customStyle: { width: '520px', whiteSpace: 'pre-line' }
    })
  } finally {
    localStorage.removeItem('token')
    router.replace('/login')
  }
}

const pollImportStatus = async () => {
  if (!importJobId.value) return

  try {
    const job = await api.getDatabaseImportStatus(importJobId.value)
    applyImportJob(job)
    if (job.status === 'completed' || job.status === 'failed') {
      await finishImport(job)
    }
  } catch (error) {
    clearImportPollTimer()
    importing.value = false
    if (error.response?.status === 404) {
      rememberActiveImportJob('')
    }
    ElMessage.error(`获取导入状态失败：${getErrorMessage(error)}`)
  }
}

const startImportPolling = () => {
  clearImportPollTimer()
  importPollTimer.value = window.setInterval(pollImportStatus, 1000)
  pollImportStatus()
}

const resumeActiveImportJob = async () => {
  if (importing.value || resumingImport.value) {
    return
  }

  let activeJobId = sessionStorage.getItem(ACTIVE_IMPORT_JOB_KEY)
  if (!activeJobId) {
    resumingImport.value = true
    try {
      const latestJob = await api.getLatestDatabaseImportStatus()
      activeJobId = latestJob.job_id
      rememberActiveImportJob(activeJobId)
      applyImportJob(latestJob)
    } catch (error) {
      return
    } finally {
      resumingImport.value = false
    }
  }

  if (!activeJobId || (importJobId.value === activeJobId && importPollTimer.value)) {
    return
  }

  importJobId.value = activeJobId
  importing.value = true
  importStatus.value = importStatus.value || 'queued'
  importStage.value = importStage.value || 'queued'
  importLogs.value = importLogs.value.length ? importLogs.value : ['正在恢复后台导入任务进度...']
  startImportPolling()
}

const exportBackup = async () => {
  if (exporting.value || downloadingExport.value) {
    return
  }

  exporting.value = true
  exportJobId.value = ''
  exportStatus.value = 'queued'
  exportStage.value = 'queued'
  exportProgress.value = 0
  exportCurrentTable.value = ''
  exportFileSize.value = 0
  exportFilename.value = ''
  exportDownloadProgress.value = 0
  exportLogs.value = ['正在创建 SQL 导出任务...']

  try {
    const result = await api.exportDatabaseBackup()
    exportJobId.value = result.job_id
    rememberActiveExportJob(result.job_id)
    if (!componentUnmounted) {
      startExportPolling()
    }
  } catch (error) {
    exporting.value = false
    ElMessage.error(`导出失败：${getErrorMessage(error)}`)
  }
}

const handleFileChange = (uploadFile) => {
  const rawFile = uploadFile.raw
  if (!rawFile || !rawFile.name.toLowerCase().endsWith('.sql')) {
    selectedFile.value = null
    fileList.value = []
    ElMessage.warning('请选择 .sql 备份文件')
    return false
  }

  selectedFile.value = rawFile
  fileList.value = [uploadFile]
  return true
}

const handleFileRemove = () => {
  selectedFile.value = null
  fileList.value = []
}

const handleExceed = () => {
  ElMessage.warning('每次只能上传一个 SQL 文件，请先移除当前文件')
}

const importBackup = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择 SQL 备份文件')
    return
  }

  try {
    await ElMessageBox.confirm(
      '导入后会先清空当前数据库，再恢复备份文件中的数据。这个操作不可撤销，确定继续吗？',
      '确认导入 SQL 备份',
      {
        confirmButtonText: '确认导入',
        cancelButtonText: '取消',
        type: 'warning',
        center: true
      }
    )
  } catch (error) {
    return
  }

  importing.value = true
  importJobId.value = ''
  importStatus.value = 'queued'
  importStage.value = 'queued'
  importProgress.value = 0
  importCurrentTable.value = ''
  importLogs.value = ['正在上传 SQL 备份文件...']

  try {
    const result = await api.importDatabaseBackup(selectedFile.value)
    importJobId.value = result.job_id
    rememberActiveImportJob(result.job_id)
    fileList.value = []
    selectedFile.value = null
    if (!componentUnmounted) {
      startImportPolling()
    }
  } catch (error) {
    importing.value = false
    ElMessage.error(`导入失败：${getErrorMessage(error)}`)
  }
}

onBeforeUnmount(() => {
  componentUnmounted = true
  clearExportPollTimer()
  clearImportPollTimer()
})

onMounted(() => {
  componentUnmounted = false
  resumeActiveExportJob()
  resumeActiveImportJob()
})

onActivated(() => {
  resumeActiveExportJob()
  resumeActiveImportJob()
})

watch(exportLogs, scrollExportLogToBottom)
watch(importLogs, scrollImportLogToBottom)
</script>

<style scoped>
.database-backup {
  width: 100%;
  min-height: 0;
}

.backup-alert {
  margin-bottom: 20px;
}

.backup-grid {
  align-items: stretch;
}

.backup-card {
  height: 100%;
}

.import-status-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 700;
}

.backup-copy {
  min-height: 56px;
  margin-bottom: 18px;
  color: #606266;
  font-size: 14px;
  line-height: 1.7;
}

.import-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 0;
  color: #606266;
  font-size: 13px;
}

.export-hint {
  margin-bottom: 12px;
  color: #409eff;
  font-size: 13px;
  line-height: 1.5;
}

.export-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.import-log {
  max-height: 180px;
  overflow-y: auto;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafafa;
}

.import-log-line {
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
}

.sql-upload {
  margin-bottom: 14px;
}

.sql-upload :deep(.el-upload) {
  width: 100%;
}

.sql-upload :deep(.el-upload-dragger) {
  width: 100%;
}

.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}

.selected-file {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  color: #606266;
  font-size: 13px;
}

@media (max-width: 1199px) {
  .backup-card {
    margin-bottom: 16px;
  }
}

@media (max-width: 767px) {
  .database-backup {
    height: 100%;
    overflow-y: auto;
    padding-bottom: 4px;
  }

  .database-backup :deep(.el-card) {
    border-radius: 14px;
    box-shadow: none;
  }

  .backup-alert,
  .import-status-card {
    margin-bottom: 12px;
  }

  .backup-grid :deep(.el-col) {
    margin-bottom: 12px;
  }

  .import-meta,
  .selected-file {
    flex-direction: column;
  }
}
</style>
