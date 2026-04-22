<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap">
          <span style="font-weight: bold">主机列表</span>
          <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap">
            <el-input 
              v-model="searchKeyword" 
              placeholder="搜索名称、地址、IP、描述、地区或运营商" 
              clearable
              style="width: 320px"
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
              <el-option label="未知" value="未知" />
            </el-select>
            <el-select
              v-model="enabledFilter"
              placeholder="启用状态"
              clearable
              style="width: 120px"
            >
              <el-option label="已启用" value="enabled" />
              <el-option label="已停用" value="disabled" />
            </el-select>
            <el-select
              v-model="locationFilter"
              placeholder="定位状态"
              clearable
              style="width: 120px"
            >
              <el-option label="已定位" value="success" />
              <el-option label="获取失败" value="failed" />
              <el-option label="获取中" value="pending" />
            </el-select>
            <el-button type="primary" @click="loadHosts">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
            <el-button type="danger" @click="batchDelete" :disabled="selectedHosts.length === 0" v-if="selectedHosts.length > 0">
              <el-icon><Delete /></el-icon> 批量删除 ({{ selectedHosts.length }})
            </el-button>
            <el-button type="info" @click="batchRefreshLocation" :disabled="selectedHosts.length === 0" v-if="selectedHosts.length > 0">
              <el-icon><Refresh /></el-icon> 批量刷新位置 ({{ selectedHosts.length }})
            </el-button>
            <el-button type="warning" @click="exportHosts">
              <el-icon><Download /></el-icon> 导出
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
        <el-table-column prop="id" label="ID" width="80" align="center" header-align="center" />
        <el-table-column prop="name" label="主机名称" width="150" align="center" header-align="center" />
        <el-table-column label="地址" width="200" align="center" header-align="center">
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
        <el-table-column label="IP地址" width="180" align="center" header-align="center">
          <template #default="{ row }">
            <span
              v-if="row.resolved_ip"
              @click="copyAddress(row.resolved_ip)"
              style="cursor: pointer; color: #409eff; text-decoration: underline"
              :title="'点击复制: ' + row.resolved_ip"
            >
              {{ row.resolved_ip }}
            </span>
            <span v-else style="color: #909399">未解析</span>
            <el-icon
              @click="refreshIp(row.id, row.name)"
              style="margin-left: 5px; cursor: pointer; color: #67c23a"
              :title="'刷新IP地址'"
            >
              <Refresh />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === '正常'" type="success">{{ row.status }}</el-tag>
            <el-tag v-else-if="row.status === '异常'" type="danger">{{ row.status }}</el-tag>
            <el-tag v-else type="info">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="丢包率" width="100" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag v-if="row.packet_loss !== null && row.packet_loss !== undefined" :type="getPacketLossTagType(row.packet_loss)">
              {{ row.packet_loss }}%
            </el-tag>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>
        <el-table-column label="平均延迟" width="110" align="center" header-align="center">
          <template #default="{ row }">
            <span v-if="row.avg_rtt !== null && row.avg_rtt !== undefined" :style="{ color: getRttColor(row.avg_rtt), fontWeight: '600' }">
              {{ row.avg_rtt }}ms
            </span>
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>
        <el-table-column label="最后检查" width="180" align="center" header-align="center">
          <template #default="{ row }">
            <span v-if="row.last_check">{{ new Date(row.last_check).toLocaleString() }}</span>
            <span v-else style="color: #909399">暂无</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150" align="center" header-align="center" />
        <el-table-column label="地理位置" width="200" align="center" header-align="center">
          <template #default="{ row }">
            <div v-if="row.location_status === 'success'" style="display: flex; align-items: center; justify-content: center; gap: 5px">
              <el-icon style="color: #67c23a"><Location /></el-icon>
              <span>{{ formatLocation(row) }}</span>
              <el-icon
                @click="refreshLocation(row.id, row.name)"
                style="cursor: pointer; color: #409eff"
                :title="'刷新地理位置'"
              >
                <Refresh />
              </el-icon>
            </div>
            <div v-else-if="row.location_status === 'failed'" style="display: flex; align-items: center; justify-content: center; gap: 5px">
              <el-icon style="color: #f56c6c"><WarningFilled /></el-icon>
              <span style="color: #909399">获取失败</span>
              <el-icon
                @click="refreshLocation(row.id, row.name)"
                style="cursor: pointer; color: #409eff"
                :title="'重新获取'"
              >
                <Refresh />
              </el-icon>
            </div>
            <div v-else style="display: flex; align-items: center; justify-content: center; gap: 5px">
              <el-icon style="color: #909399"><Loading /></el-icon>
              <span style="color: #909399">获取中...</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="告警阈值" width="120" align="center" header-align="center">
          <template #default="{ row }">
            {{ row.alert_threshold }}%
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100" align="center" header-align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="updateHostStatus(row)" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180" align="center" header-align="center">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" align="center" header-align="center">
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
      width="720px"
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
        <el-divider content-position="left">地理位置（可选）</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="国家">
              <el-input v-model="form.country" placeholder="例如：中国 / 美国" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="省份/州">
              <el-input v-model="form.province" placeholder="例如：广东 / California" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="城市">
              <el-input v-model="form.city" placeholder="例如：深圳 / Mountain View" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="运营商">
              <el-input v-model="form.isp" placeholder="例如：中国电信 / Google" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="纬度">
              <el-input-number v-model="form.latitude" :min="-90" :max="90" :step="0.0001" :precision="6" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="经度">
              <el-input-number v-model="form.longitude" :min="-180" :max="180" :step="0.0001" :precision="6" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <div style="margin-top: -6px; color: #909399; font-size: 12px; line-height: 1.7">
          不填写时，系统会根据 IP 自动补全；已手动填写的地区信息会优先保留，只补全空白字段。
        </div>
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
            <p>每行一个主机，格式：主机名称,地址,描述,告警阈值,国家,省份/州,城市,运营商,纬度,经度</p>
            <p>示例：百度,www.baidu.com,百度搜索,20,中国,北京,北京,中国电信,,</p>
            <p>注意：从第 5 列开始均可省略，系统会自动补全缺失的地理位置</p>
          </el-alert>
          
          <el-input
            v-model="batchImportText"
            type="textarea"
            :rows="10"
            placeholder="请输入主机信息，每行一个主机，可选追加地理位置字段"
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

      <!-- 导入进度条 -->
      <div v-if="importing" style="margin-top: 20px">
        <el-progress
          :percentage="importProgress"
          :status="importProgress === 100 ? 'success' : undefined"
        >
          <span>{{ importProgressText }}</span>
        </el-progress>
      </div>

      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBatchImport" :loading="importing">导入</el-button>
      </template>
    </el-dialog>

    <!-- Ping结果对话框 -->
    <el-dialog
      v-model="pingDialogVisible"
      title="Ping测试"
      width="900px"
      :close-on-click-modal="false"
    >
      <div style="display: flex; gap: 20px;">
        <!-- 左侧: Ping日志区域 -->
        <div style="flex: 1; minWidth: 0;">
          <div style="marginBottom: 10px; fontWeight: bold; color: #409eff;">实时日志</div>
          <div 
            ref="pingLogContainer" 
            class="ping-log-container"
            :style="{ height: '400px', overflowY: 'auto', backgroundColor: '#1e1e1e', color: '#d4d4d4', padding: '15px', borderRadius: '4px', fontFamily: 'Consolas, Monaco, monospace', fontSize: '13px', lineHeight: '1.6' }"
          >
            <div v-if="pingLogs.length === 0" style="color: #888; text-align: center; padding: 20px;">
              准备开始 Ping 测试...
            </div>
            <div 
              v-for="(log, index) in pingLogs" 
              :key="index" 
              :style="{ 
                marginBottom: '8px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all'
              }"
            >
              <span v-if="log.type === 'start'" style="color: #4ec9b0; fontWeight: bold">▶ {{ log.message }}</span>
              <span v-else-if="log.type === 'ping'">
                <span style="color: #d4d4d4">[{{ log.sequence }}/{{ log.total }}]</span>
                <span :style="{ color: log.status === 'success' ? '#6a9955' : '#f48771' }">●</span>
                <span :style="{ color: getDelayColor(log.delay) }">{{ log.message }}</span>
              </span>
              <span v-else-if="log.type === 'complete'" style="color: #4ec9b0; fontWeight: bold">✓ {{ log.message }}</span>
              <span v-else-if="log.type === 'error'" style="color: #f48771; fontWeight: bold">✗ {{ log.message }}</span>
            </div>
          </div>
        </div>

        <!-- 右侧: 汇总结果区域 -->
        <div style="flex: 1; minWidth: 280px;">
          <div style="marginBottom: 10px; fontWeight: bold; color: #409eff;">测试结果汇总</div>
          <div v-if="pingSummary" style="backgroundColor: #f5f7fa; padding: 20px; borderRadius: 4px; height: 400px; display: flex; flexDirection: column; justifyContent: center;">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="状态" label-align="center" align="center">
                <el-tag :type="pingSummary.packet_loss >= 20 ? 'danger' : 'success'">
                  {{ pingSummary.status === 'success' ? '正常' : pingSummary.status === 'unreachable' ? '无法访问' : '超时' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="丢包率" label-align="center" align="center">
                <span :style="{ color: pingSummary.packet_loss >= 20 ? '#f56c6c' : '#67c23a', fontWeight: 'bold', fontSize: '16px' }">
                  {{ pingSummary.packet_loss }}%
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="发送包数" label-align="center" align="center">
                <span style="fontSize: 14px">{{ pingSummary.packet_sent }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="接收包数" label-align="center" align="center">
                <span style="fontSize: 14px">{{ pingSummary.packet_received }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="最小延迟" label-align="center" align="center">
                <span :style="{ color: getDelayColor(pingSummary.min_rtt), fontSize: '14px', fontWeight: 'bold' }">
                  {{ pingSummary.min_rtt ? pingSummary.min_rtt + 'ms' : '-' }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="最大延迟" label-align="center" align="center">
                <span :style="{ color: getDelayColor(pingSummary.max_rtt), fontSize: '14px', fontWeight: 'bold' }">
                  {{ pingSummary.max_rtt ? pingSummary.max_rtt + 'ms' : '-' }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="平均延迟" label-align="center" align="center">
                <span :style="{ color: getDelayColor(pingSummary.avg_rtt), fontSize: '18px', fontWeight: 'bold' }">
                  {{ pingSummary.avg_rtt ? pingSummary.avg_rtt + 'ms' : '-' }}
                </span>
              </el-descriptions-item>
            </el-descriptions>
          </div>
          <div v-else style="color: #909399; textAlign: center; padding: 60px 20px; backgroundColor: #f5f7fa; borderRadius: 4px; height: 400px; display: flex; flexDirection: column; alignItems: center; justifyContent: center;">
            <i class="el-icon-loading" style="fontSize: 32px; marginBottom: 15px;"></i>
            <div style="fontSize: 16px;">等待测试结果...</div>
          </div>
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
import { UploadFilled, Download, Upload, Location, Refresh, WarningFilled, Loading } from '@element-plus/icons-vue'
import api from '../api'

const hosts = ref([])
const hostsWithStatus = ref([])
const selectedHosts = ref([])
const dialogVisible = ref(false)
const batchDialogVisible = ref(false)
const pingDialogVisible = ref(false)
const dialogMode = ref('add')
const importing = ref(false)
const importProgress = ref(0)
const importProgressText = ref('')
const pinging = ref(false)
const batchImportText = ref('')
const importTabActive = ref('text')
const uploadRef = ref(null)
const excelData = ref([])
const fileList = ref([])
const pingResult = ref(null)
const pingLogs = ref([])
const pingSummary = ref(null)
const pingLogContainer = ref(null)
const pingEventSource = ref(null)
const searchKeyword = ref('')
const statusFilter = ref('')
const enabledFilter = ref('')
const locationFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
let xlsxModulePromise = null

const getXLSX = async () => {
  if (!xlsxModulePromise) {
    xlsxModulePromise = import('xlsx')
  }
  return xlsxModulePromise
}

const form = reactive({
  id: null,
  name: '',
  address: '',
  description: '',
  alert_threshold: 20.0,
  country: '',
  province: '',
  city: '',
  isp: '',
  latitude: null,
  longitude: null
})

// 搜索和筛选后的所有主机
const filteredAllHosts = computed(() => {
  let result = [...hostsWithStatus.value]
  
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter((host) => {
      const searchFields = [
        host.name,
        host.address,
        host.description,
        host.resolved_ip,
        host.country,
        host.province,
        host.city,
        host.isp,
        host.status
      ]
      return searchFields
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(keyword))
    })
  }
  
  if (statusFilter.value) {
    result = result.filter((host) => host.status === statusFilter.value)
  }

  if (enabledFilter.value) {
    const enabledValue = enabledFilter.value === 'enabled'
    result = result.filter((host) => Boolean(host.enabled) === enabledValue)
  }

  if (locationFilter.value) {
    result = result.filter((host) => normalizeLocationStatus(host.location_status) === locationFilter.value)
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
    const [hostList, dashboardData] = await Promise.all([
      api.getHosts(),
      api.getDashboard()
    ])

    hosts.value = hostList
    const statusMap = new Map()
    ;(dashboardData.host_status || []).forEach((hs) => {
      statusMap.set(hs.id, hs)
    })
    
    hostsWithStatus.value = hosts.value.map((host) => {
      const statusInfo = statusMap.get(host.id) || {}
      return {
        ...host,
        status: statusInfo.status || host.last_status || '未知',
        packet_loss: statusInfo.packet_loss ?? null,
        avg_rtt: statusInfo.avg_rtt ?? null,
        last_check: statusInfo.last_check ?? null,
        resolved_ip: statusInfo.resolved_ip || host.resolved_ip,
        location_status: statusInfo.location_status || host.location_status,
        country: statusInfo.country || host.country,
        province: statusInfo.province || host.province,
        city: statusInfo.city || host.city,
        isp: statusInfo.isp || host.isp
      }
    })
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
  form.country = ''
  form.province = ''
  form.city = ''
  form.isp = ''
  form.latitude = null
  form.longitude = null
}

const submitForm = async () => {
  if (!form.name || !form.address) {
    ElMessage.warning('请填写主机名称和地址')
    return
  }

  try {
    const payload = {
      name: form.name,
      address: form.address,
      description: form.description,
      alert_threshold: form.alert_threshold,
      country: form.country || null,
      province: form.province || null,
      city: form.city || null,
      isp: form.isp || null,
      latitude: form.latitude ?? null,
      longitude: form.longitude ?? null
    }

    if (dialogMode.value === 'add') {
      await api.createHost(payload)
      ElMessage.success('添加成功')
    } else {
      await api.updateHost(form.id, payload)
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
  // 重置状态
  pingResult.value = null
  pingLogs.value = []
  pingSummary.value = null
  pinging.value = true
  pingDialogVisible.value = true
  
  try {
    // 关闭之前的连接
    if (pingEventSource.value) {
      pingEventSource.value.close()
    }
    
    // 启动SSE流
    pingEventSource.value = api.pingStream(
      host.id,
      // onMessage: 处理每条消息
      (data) => {
        pingLogs.value.push(data)
        
        // 如果是汇总数据,保存到summary
        if (data.type === 'summary') {
          pingSummary.value = data
        }
        
        // 自动滚动到底部
        nextTick(() => {
          if (pingLogContainer.value) {
            pingLogContainer.value.scrollTop = pingLogContainer.value.scrollHeight
          }
        })
      },
      // onError: 错误处理
      (error) => {
        pinging.value = false
        ElMessage.error(`Ping失败: 连接错误`)
      },
      // onComplete: 完成回调
      () => {
        pinging.value = false
        // 刷新主机列表
        loadHosts()
      }
    )
  } catch (error) {
    pinging.value = false
    pingDialogVisible.value = false
    ElMessage.error(`Ping失败: ${error.message || '网络错误'}`)
  }
}

const closePingDialog = () => {
  // 关闭SSE连接
  if (pingEventSource.value) {
    pingEventSource.value.close()
    pingEventSource.value = null
  }
  
  pingDialogVisible.value = false
  pingLogs.value = []
  pingSummary.value = null
  pingResult.value = null
}

// 根据延迟时间返回颜色
const getDelayColor = (delay) => {
  if (!delay) return '#d4d4d4'
  if (delay < 50) return '#6a9955'  // 绿色: 优秀
  if (delay < 100) return '#dcdcaa' // 黄色: 一般
  return '#f48771'                   // 红色: 较慢
}

const deleteHost = async (host) => {
  try {
    await ElMessageBox.confirm(`确定要删除主机 "${host.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
      center: true
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
        type: 'warning',
        center: true
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

// 刷新单个主机地理位置
const refreshLocation = async (hostId, hostName) => {
  try {
    const response = await api.refreshHostLocation(hostId)
    if (response.location && response.location.status === 'success') {
      ElMessage.success(`${hostName} 地理位置刷新成功`)
      await loadHosts()
    } else {
      ElMessage.warning(`${hostName} 地理位置刷新失败: ${response.location?.error || '未知错误'}`)
    }
  } catch (error) {
    console.error('刷新地理位置失败:', error)
    ElMessage.error(`${hostName} 地理位置刷新失败`)
  }
}

const refreshIp = async (hostId, hostName) => {
  try {
    const response = await api.refreshHostIp(hostId)
    if (response.resolved_ip) {
      ElMessage.success(`${hostName} IP地址刷新成功: ${response.resolved_ip}`)
    } else {
      ElMessage.warning(`${hostName} IP地址解析失败`)
    }
    await loadHosts()
  } catch (error) {
    console.error('刷新IP地址失败:', error)
    ElMessage.error(`刷新IP地址失败: ${error.response?.data?.detail || error.message}`)
  }
}

// 批量刷新地理位置
const batchRefreshLocation = async () => {
  if (selectedHosts.value.length === 0) {
    ElMessage.warning('请先选择要刷新地理位置的主机')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要刷新选中的 ${selectedHosts.value.length} 个主机的地理位置吗？`,
      '批量刷新地理位置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    let successCount = 0
    let failCount = 0

    for (const host of selectedHosts.value) {
      try {
        const response = await api.refreshHostLocation(host.id)
        if (response.location && response.location.status === 'success') {
          successCount++
        } else {
          failCount++
        }
      } catch (error) {
        failCount++
      }
    }

    await loadHosts()

    if (failCount === 0) {
      ElMessage.success(`成功刷新 ${successCount} 个主机的地理位置`)
    } else {
      ElMessage.warning(`刷新完成: 成功 ${successCount} 个，失败 ${failCount} 个`)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量刷新地理位置失败:', error)
    }
  }
}

// 格式化地理位置显示
const formatLocation = (host) => {
  const parts = []
  if (host.country) parts.push(host.country)
  if (host.province) parts.push(host.province)
  if (host.city) parts.push(host.city)
  return parts.length > 0 ? parts.join(' ') : '未知'
}

const normalizeLocationStatus = (status) => {
  if (status === 'success' || status === 'failed') {
    return status
  }
  return 'pending'
}

const getPacketLossTagType = (packetLoss) => {
  if (Number(packetLoss) >= 20) {
    return 'danger'
  }
  if (Number(packetLoss) > 0) {
    return 'warning'
  }
  return 'success'
}

const getRttColor = (avgRtt) => {
  if (Number(avgRtt) >= 150) {
    return '#f56c6c'
  }
  if (Number(avgRtt) >= 80) {
    return '#e6a23c'
  }
  return '#67c23a'
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
      const [
        name,
        address,
        description = '',
        alert_threshold = '20',
        country = '',
        province = '',
        city = '',
        isp = '',
        latitude = '',
        longitude = ''
      ] = parts
      return {
        name,
        address,
        description,
        alert_threshold: parseFloat(alert_threshold) || 20.0,
        country,
        province,
        city,
        isp,
        latitude: latitude === '' ? null : Number(latitude),
        longitude: longitude === '' ? null : Number(longitude),
        index: index + 1
      }
    })
  } else {
    if (!excelData.value || excelData.value.length === 0) {
      ElMessage.warning('请上传Excel文件')
      return
    }
    hostsToImport = excelData.value
  }

  importing.value = true
  importProgress.value = 0
  let successCount = 0
  let duplicateCount = 0
  let failCount = 0
  const duplicateHosts = []
  const errors = []

  const totalCount = hostsToImport.length
  for (let i = 0; i < hostsToImport.length; i++) {
    const item = hostsToImport[i]

    // 更新进度
    importProgress.value = Math.round(((i + 1) / totalCount) * 100)
    importProgressText.value = `正在导入 ${i + 1}/${totalCount}`

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
        alert_threshold: item.alert_threshold || 20.0,
        country: item.country || null,
        province: item.province || null,
        city: item.city || null,
        isp: item.isp || null,
        latitude: item.latitude ?? null,
        longitude: item.longitude ?? null
      })
      successCount++
    } catch (error) {
      const errorDetail = error.response?.data?.detail || '导入失败'

      // 判断是否为重复主机
      if (errorDetail.includes('已存在') || errorDetail.includes('duplicate')) {
        duplicateCount++
        duplicateHosts.push(item.name)
      } else {
        failCount++
        errors.push(`${item.name || '第' + item.index + '行'}：${errorDetail}`)
      }
    }
  }

  importing.value = false
  importProgress.value = 0
  importProgressText.value = ''

  // 构建结果消息
  let resultMessage = `导入完成！\n\n`
  resultMessage += `总计：${totalCount} 个主机\n`
  resultMessage += `成功导入：${successCount} 个\n`

  if (duplicateCount > 0) {
    resultMessage += `重复跳过：${duplicateCount} 个\n`
  }

  if (failCount > 0) {
    resultMessage += `导入失败：${failCount} 个\n`
  }

  // 显示详细信息
  if (duplicateCount > 0 || failCount > 0) {
    resultMessage += `\n详细信息：\n`

    if (duplicateCount > 0) {
      const showDuplicates = duplicateHosts.slice(0, 3).join('、')
      resultMessage += `• 重复主机：${showDuplicates}${duplicateCount > 3 ? ` 等${duplicateCount}个` : ''}\n`
    }

    if (failCount > 0) {
      const showErrors = errors.slice(0, 3).join('\n  ')
      resultMessage += `• 失败原因：\n  ${showErrors}${errors.length > 3 ? `\n  ...还有${errors.length - 3}个错误` : ''}`
    }
  }

  // 刷新主机列表
  if (successCount > 0) {
    loadHosts()
  }

  // 显示结果弹窗
  const messageType = failCount > 0 ? 'warning' : (successCount > 0 ? 'success' : 'info')

  await ElMessageBox.alert(resultMessage, '导入结果', {
    confirmButtonText: '确定',
    type: messageType,
    center: true,
    customStyle: {
      width: '500px'
    }
  })

  // 如果全部成功或只有重复，关闭对话框
  if (failCount === 0) {
    batchDialogVisible.value = false
  }
}

const downloadTemplate = async () => {
  const XLSX = await getXLSX()

  // 创建示例数据
  const data = [
    ['主机名称', '地址', '描述', '告警阈值(%)'],
    ['百度', 'www.baidu.com', '百度搜索引擎', 20],
    ['腾讯', 'www.qq.com', '腾讯官网', 20],
    ['阿里', 'www.aliyun.com', '阿里云', 15]
  ]
  
  // 创建工作簿
  data[0].push('国家', '省份/州', '城市', '运营商', '纬度', '经度')
  data[1].push('中国', '北京', '北京', '中国电信', '', '')
  data[2].push('中国', '广东', '深圳', '腾讯云', '', '')
  data[3].push('中国', '浙江', '杭州', '阿里云', '', '')

  const ws = XLSX.utils.aoa_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '主机列表')
  
  // 下载文件
  XLSX.writeFile(wb, '主机导入模板.xlsx')
  ElMessage.success('模板下载成功')
}

const exportHosts = async () => {
  if (hostsWithStatus.value.length === 0) {
    ElMessage.warning('没有可导出的主机数据')
    return
  }

  const XLSX = await getXLSX()
  
  // 准备导出数据，格式与导入模板一致
  const data = [
    ['主机名称', '地址', '描述', '告警阈值(%)']
  ]
  
  // 添加主机数据
  data[0].push('国家', '省份/州', '城市', '运营商', '纬度', '经度')

  hostsWithStatus.value.forEach(host => {
    data.push([
      host.name,
      host.address,
      host.description || '',
      host.alert_threshold,
      host.country || '',
      host.province || '',
      host.city || '',
      host.isp || '',
      host.latitude ?? '',
      host.longitude ?? ''
    ])
  })
  
  // 创建工作簿
  const ws = XLSX.utils.aoa_to_sheet(data)
  
  // 自动设置列宽
  const colWidths = []
  // 遍历每一列
  for (let col = 0; col < data[0].length; col++) {
    let maxWidth = 0
    // 遍历该列的所有行，找出最大宽度
    for (let row = 0; row < data.length; row++) {
      const cellValue = data[row][col]
      if (cellValue != null) {
        const cellLength = String(cellValue).length
        // 中文字符按2个字符宽度计算
        const chineseCount = (String(cellValue).match(/[\u4e00-\u9fa5]/g) || []).length
        const actualWidth = cellLength + chineseCount
        maxWidth = Math.max(maxWidth, actualWidth)
      }
    }
    // 设置列宽，最小10，最大50
    colWidths.push({ wch: Math.min(Math.max(maxWidth + 2, 10), 50) })
  }
  ws['!cols'] = colWidths
  
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '主机列表')
  
  // 生成文件名（带时间戳）
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  const timestamp = `${year}${month}${day}_${hours}${minutes}${seconds}`
  const filename = `主机列表_${timestamp}.xlsx`
  
  // 下载文件
  XLSX.writeFile(wb, filename)
  ElMessage.success(`导出成功，共 ${hostsWithStatus.value.length} 条数据`)
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

watch([searchKeyword, statusFilter, enabledFilter, locationFilter], () => {
  currentPage.value = 1
})

const handleExceed = () => {
  ElMessage.warning('每次只能上传一个文件，请删除后再上传')
}

const handleFileChange = (file) => {
  fileList.value = [file]
  const reader = new FileReader()
  
  reader.onload = async (e) => {
    try {
      const XLSX = await getXLSX()
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
        
        const [
          name,
          address,
          description = '',
          alert_threshold = 20,
          country = '',
          province = '',
          city = '',
          isp = '',
          latitude = '',
          longitude = ''
        ] = row
        
        if (!name || !address) {
          hosts.push({ error: `第${i + 1}行：缺少主机名称或地址`, index: i + 1 })
          continue
        }
        
        hosts.push({
          name: String(name).trim(),
          address: String(address).trim(),
          description: String(description || '').trim(),
          alert_threshold: parseFloat(alert_threshold) || 20.0,
          country: String(country || '').trim(),
          province: String(province || '').trim(),
          city: String(city || '').trim(),
          isp: String(isp || '').trim(),
          latitude: latitude === '' || latitude == null ? null : Number(latitude),
          longitude: longitude === '' || longitude == null ? null : Number(longitude),
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
