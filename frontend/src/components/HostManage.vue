<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: bold">主机列表</span>
          <div style="display: flex; align-items: center; gap: 10px">
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
            <el-select 
              v-model="statusFilter" 
              placeholder="状态筛选" 
              clearable
              style="width: 130px"
            >
              <el-option label="正常" value="正常" />
              <el-option label="异常" value="异常" />
            </el-select>
            <el-button type="danger" @click="batchDelete" :disabled="selectedHosts.length === 0" v-if="selectedHosts.length > 0">
              <el-icon><Delete /></el-icon> 批量删除 ({{ selectedHosts.length }})
            </el-button>
            <el-button type="success" @click="showBatchImportDialog">
              <el-icon><Upload /></el-icon> 批量导入
            </el-button>
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon> 添加主机
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredHosts" style="width: 100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
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
        <el-table-column prop="description" label="描述" min-width="150" />
        <el-table-column label="告警阈值" width="120">
          <template #default="{ row }">
            {{ row.alert_threshold }}%
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="updateHostStatus(row)" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="pingHost(row)">Ping</el-button>
            <el-button type="warning" size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="deleteHost(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div style="margin-top: 15px; display: flex; justify-content: center">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredAllHosts.length"
          layout="total, sizes, prev, pager, next, jumper"
          :small="true"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 添加/编辑主机对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogMode === 'add' ? '添加主机' : '编辑主机'"
      width="500px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="主机名称">
          <el-input v-model="form.name" placeholder="例如: 百度服务器" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" placeholder="例如: www.baidu.com 或 114.114.114.114" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item label="告警阈值">
          <el-input-number v-model="form.alert_threshold" :min="0" :max="100" />
          <span style="margin-left: 10px">%</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
    <!-- 批量导入对话框 -->
    <el-dialog 
      v-model="batchDialogVisible" 
      title="批量导入主机"
      width="700px"
    >
      <el-tabs v-model="importTabActive">
        <!-- 文本导入 -->
        <el-tab-pane label="文本导入" name="text">
          <el-alert
            title="导入说明"
            type="info"
            :closable="false"
            style="margin-bottom: 15px"
          >
            <p>每行一个主机，格式：主机名称,地址,描述,告警阈值</p>
            <p>示例：百度,www.baidu.com,百度搜索,20</p>
            <p>注意：描述和告警阈值可以省略，省略时默认阈值为20%</p>
          </el-alert>
          
          <el-input
            v-model="batchImportText"
            type="textarea"
            :rows="10"
            placeholder="请输入主机信息，每行一个主机"
          />
        </el-tab-pane>
        
        <!-- Excel导入 -->
        <el-tab-pane label="Excel导入" name="excel">
          <el-alert
            title="导入说明"
            type="info"
            :closable="false"
            style="margin-bottom: 15px"
          >
            <p>1. 下载示例Excel文件模板</p>
            <p>2. 按照模板格式填写主机信息</p>
            <p>3. 上传填写好的Excel文件</p>
            <p>注意：支持 .xlsx 和 .xls 格式</p>
          </el-alert>
          
          <div style="margin-bottom: 15px">
            <el-button type="primary" @click="downloadTemplate">
              <el-icon><Download /></el-icon> 下载示例模板
            </el-button>
          </div>
          
          <el-upload
            ref="uploadRef"
            class="upload-demo"
            :auto-upload="false"
            :on-change="handleFileChange"
            :file-list="fileList"
            :limit="1"
            :on-exceed="handleExceed"
            accept=".xlsx,.xls"
            drag
            :disabled="false"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将Excel文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip" style="color: #909399; font-size: 12px; margin-top: 5px">
                支持 .xlsx 和 .xls 格式，每次只能上传一个文件
              </div>
            </template>
          </el-upload>
        </el-tab-pane>
      </el-tabs>
      
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBatchImport" :loading="importing">导入</el-button>
      </template>
    </el-dialog>

    <!-- Ping结果对话框 -->
    <el-dialog
      v-model="pingDialogVisible"
      title="Ping结果"
      width="500px"
      :close-on-click-modal="false"
    >
      <div v-loading="pinging" element-loading-text="正在Ping，请稍候..." style="min-height: 200px">
        <div v-if="pingResult" style="padding: 20px">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="主机">
              {{ pingResult.host }}
            </el-descriptions-item>
            <el-descriptions-item label="地址">
              {{ pingResult.address }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="pingResult.packet_loss >= 20 ? 'danger' : 'success'">
                {{ pingResult.status === 'success' ? '正常' : pingResult.status === 'unreachable' ? '无法访问' : '超时' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="发送包数">
              {{ pingResult.packet_sent }}
            </el-descriptions-item>
            <el-descriptions-item label="接收包数">
              {{ pingResult.packet_received }}
            </el-descriptions-item>
            <el-descriptions-item label="丢包率">
              <span :style="{ color: pingResult.packet_loss >= 20 ? '#f56c6c' : '#67c23a', fontWeight: 'bold' }">
                {{ pingResult.packet_loss }}%
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="最小延迟">
              {{ pingResult.min_rtt ? pingResult.min_rtt + 'ms' : '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="最大延迟">
              {{ pingResult.max_rtt ? pingResult.max_rtt + 'ms' : '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="平均延迟">
              {{ pingResult.avg_rtt ? pingResult.avg_rtt + 'ms' : '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="closePingDialog" :disabled="pinging">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Download, Upload } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import api from '../api'

const hosts = ref([])
const hostsWithStatus = ref([])
const selectedHosts = ref([])
const dialogVisible = ref(false)
const batchDialogVisible = ref(false)
const pingDialogVisible = ref(false)
const dialogMode = ref('add')
const importing = ref(false)
const pinging = ref(false)
const batchImportText = ref('')
const importTabActive = ref('text')
const uploadRef = ref(null)
const excelData = ref([])
const fileList = ref([])
const pingResult = ref(null)
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const form = reactive({
  id: null,
  name: '',
  address: '',
  description: '',
  alert_threshold: 20.0
})

// 搜索和筛选后的所有主机
const filteredAllHosts = computed(() => {
  let result = [...hostsWithStatus.value]
  
  // 关键字搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(host => 
      host.name.toLowerCase().includes(keyword) || 
      host.address.toLowerCase().includes(keyword)
    )
  }
  
  // 状态筛选
  if (statusFilter.value) {
    result = result.filter(host => host.status === statusFilter.value)
  }
  
  return result
})

// 当前页显示的主机
const filteredHosts = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredAllHosts.value.slice(start, end)
})

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

const loadHosts = async () => {
  try {
    hosts.value = await api.getHosts()
    // 获取每个主机的最新状态
    const dashboardData = await api.getDashboard()
    const statusMap = new Map()
    dashboardData.host_status.forEach(hs => {
      statusMap.set(hs.id, hs.status)
    })
    
    // 合并主机信息和状态
    hostsWithStatus.value = hosts.value.map(host => ({
      ...host,
      status: statusMap.get(host.id) || '未知'
    }))
  } catch (error) {
    ElMessage.error('加载主机列表失败')
  }
}

const showAddDialog = () => {
  dialogMode.value = 'add'
  resetForm()
  dialogVisible.value = true
}

const showBatchImportDialog = () => {
  batchImportText.value = ''
  excelData.value = []
  fileList.value = []
  importTabActive.value = 'text'
  batchDialogVisible.value = true
}

const showEditDialog = (host) => {
  dialogMode.value = 'edit'
  Object.assign(form, host)
  dialogVisible.value = true
}

const resetForm = () => {
  form.id = null
  form.name = ''
  form.address = ''
  form.description = ''
  form.alert_threshold = 20.0
}

const submitForm = async () => {
  if (!form.name || !form.address) {
    ElMessage.warning('请填写主机名称和地址')
    return
  }

  try {
    if (dialogMode.value === 'add') {
      await api.createHost({
        name: form.name,
        address: form.address,
        description: form.description,
        alert_threshold: form.alert_threshold
      })
      ElMessage.success('添加成功')
    } else {
      await api.updateHost(form.id, {
        name: form.name,
        address: form.address,
        description: form.description,
        alert_threshold: form.alert_threshold
      })
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    loadHosts()
  } catch (error) {
    ElMessage.error(dialogMode.value === 'add' ? '添加失败' : '更新失败')
  }
}

const updateHostStatus = async (host) => {
  try {
    await api.updateHost(host.id, { enabled: host.enabled })
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error('状态更新失败')
    host.enabled = !host.enabled
  }
}

const pingHost = async (host) => {
  pingResult.value = null
  pinging.value = true
  pingDialogVisible.value = true
  
  try {
    const result = await api.pingNow(host.id)
    pingResult.value = result
    pinging.value = false
    
    // 刷新主机列表
    loadHosts()
  } catch (error) {
    pinging.value = false
    pingDialogVisible.value = false
    ElMessage.error(`Ping失败: ${error.response?.data?.detail || error.message || '网络错误'}`)
  }
}

const closePingDialog = () => {
  pingDialogVisible.value = false
  pingResult.value = null
}

const deleteHost = async (host) => {
  try {
    await ElMessageBox.confirm(`确定要删除主机 "${host.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.deleteHost(host.id)
    ElMessage.success('删除成功')
    loadHosts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSelectionChange = (selection) => {
  selectedHosts.value = selection
}

const batchDelete = async () => {
  if (selectedHosts.value.length === 0) {
    ElMessage.warning('请选择要删除的主机')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedHosts.value.length} 台主机吗？`,
      '批量删除提示',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    let successCount = 0
    let failCount = 0

    for (const host of selectedHosts.value) {
      try {
        await api.deleteHost(host.id)
        successCount++
      } catch (error) {
        failCount++
      }
    }

    if (successCount > 0) {
      ElMessage.success(`成功删除 ${successCount} 台主机${failCount > 0 ? `，${failCount} 台失败` : ''}`)
    } else {
      ElMessage.error('批量删除失败')
    }

    loadHosts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
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

const submitBatchImport = async () => {
  let hostsToImport = []
  
  // 根据当前标签页决定数据来源
  if (importTabActive.value === 'text') {
    if (!batchImportText.value.trim()) {
      ElMessage.warning('请输入主机信息')
      return
    }
    
    const lines = batchImportText.value.split('\n').filter(line => line.trim())
    hostsToImport = lines.map((line, index) => {
      const parts = line.split(',').map(p => p.trim())
      if (parts.length < 2) {
        return { error: `第${index + 1}行：格式错误，至少需要主机名称和地址`, index: index + 1 }
      }
      const [name, address, description = '', alert_threshold = '20'] = parts
      return { name, address, description, alert_threshold: parseFloat(alert_threshold) || 20.0, index: index + 1 }
    })
  } else {
    if (!excelData.value || excelData.value.length === 0) {
      ElMessage.warning('请上传Excel文件')
      return
    }
    hostsToImport = excelData.value
  }

  importing.value = true
  let successCount = 0
  let failCount = 0
  const errors = []

  for (const item of hostsToImport) {
    if (item.error) {
      failCount++
      errors.push(item.error)
      continue
    }

    try {
      await api.createHost({
        name: item.name,
        address: item.address,
        description: item.description || '',
        alert_threshold: item.alert_threshold || 20.0
      })
      successCount++
    } catch (error) {
      failCount++
      errors.push(`${item.name || '第' + item.index + '行'}：${error.response?.data?.detail || '导入失败'}`)
    }
  }

  importing.value = false
  
  if (successCount > 0) {
    ElMessage.success(`成功导入 ${successCount} 个主机`)
    loadHosts()
  }
  
  if (failCount > 0) {
    const errorMsg = errors.slice(0, 5).join('\n') + (errors.length > 5 ? '\n...' : '')
    ElMessageBox.alert(
      `失败 ${failCount} 个，错误信息：\n${errorMsg}`,
      '导入结果',
      { confirmButtonText: '确定', type: 'warning' }
    )
  } else {
    batchDialogVisible.value = false
  }
}

const downloadTemplate = () => {
  // 创建示例数据
  const data = [
    ['主机名称', '地址', '描述', '告警阈值(%)'],
    ['百度', 'www.baidu.com', '百度搜索引擎', 20],
    ['腾讯', 'www.qq.com', '腾讯官网', 20],
    ['阿里', 'www.aliyun.com', '阿里云', 15]
  ]
  
  // 创建工作簿
  const ws = XLSX.utils.aoa_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '主机列表')
  
  // 下载文件
  XLSX.writeFile(wb, '主机导入模板.xlsx')
  ElMessage.success('模板下载成功')
}

// 监听标签切换，当切换到 Excel 标签时确保 input 可用
watch(importTabActive, (newVal) => {
  if (newVal === 'excel') {
    nextTick(() => {
      const uploadEl = uploadRef.value
      if (uploadEl) {
        const inputEl = uploadEl.$el.querySelector('input[type="file"]')
        if (inputEl) {
          // 确保 input 可用
          inputEl.disabled = false
          inputEl.style.pointerEvents = 'auto'
        }
      }
    })
  }
})

const handleExceed = () => {
  ElMessage.warning('每次只能上传一个文件，请删除后再上传')
}

const handleFileChange = (file) => {
  fileList.value = [file]
  const reader = new FileReader()
  
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const sheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[sheetName]
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })
      
      // 跳过表头，解析数据
      const hosts = []
      for (let i = 1; i < jsonData.length; i++) {
        const row = jsonData[i]
        if (!row || row.length === 0) continue
        
        const [name, address, description = '', alert_threshold = 20] = row
        
        if (!name || !address) {
          hosts.push({ error: `第${i + 1}行：缺少主机名称或地址`, index: i + 1 })
          continue
        }
        
        hosts.push({
          name: String(name).trim(),
          address: String(address).trim(),
          description: String(description || '').trim(),
          alert_threshold: parseFloat(alert_threshold) || 20.0,
          index: i + 1
        })
      }
      
      excelData.value = hosts
      ElMessage.success(`成功读取 ${hosts.length} 条数据`)
    } catch (error) {
      ElMessage.error('Excel文件解析失败')
    }
  }
  
  reader.onerror = () => {
    ElMessage.error('文件读取失败')
  }
  
  if (file.raw) {
    reader.readAsArrayBuffer(file.raw)
  } else {
    ElMessage.error('文件对象异常')
  }
}

onMounted(() => {
  loadHosts()
})
</script>

<style scoped>
.upload-demo {
  width: 100%;
}

/* 确保上传区域可点击 */
.upload-demo :deep(.el-upload-dragger) {
  cursor: pointer;
  pointer-events: auto;
}

.upload-demo :deep(.el-upload) {
  width: 100%;
}
</style>
