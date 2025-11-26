<template>
  <div>
    <!-- 基本设置 -->
    <div v-if="props.activeTab === 'settings-basic'">
      <el-card shadow="hover" style="margin-bottom: 20px">
        <template #header>
          <span style="font-weight: bold">监控配置</span>
        </template>
        <el-form :model="config" label-width="150px" style="max-width: 600px">
          <el-form-item label="检测间隔">
            <el-input-number v-model="config.check_interval" :min="1" :max="1440" />
            <span style="margin-left: 10px">分钟</span>
            <div style="color: #909399; font-size: 12px; margin-top: 5px">
              建议：1-60分钟，过小会增加系统负担
            </div>
          </el-form-item>
          <el-form-item label="每次发送包数">
            <el-input-number v-model="config.packet_count" :min="1" :max="100" />
            <span style="margin-left: 10px">个</span>
            <div style="color: #909399; font-size: 12px; margin-top: 5px">
              建议：10-20个，包数越多结果越准确但耗时越长
            </div>
          </el-form-item>
          <el-form-item label="超时时间">
            <el-input-number v-model="config.packet_timeout" :min="1" :max="10" />
            <span style="margin-left: 10px">秒</span>
            <div style="color: #909399; font-size: 12px; margin-top: 5px">
              建议：2-5秒
            </div>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="hover">
        <template #header>
          <span style="font-weight: bold">通知配置</span>
        </template>
        <el-form :model="config" label-width="150px" style="max-width: 600px">
          <el-form-item label="通知平台">
            <el-select v-model="notificationPlatform" placeholder="选择通知平台" style="width: 100%">
              <el-option label="不启用" value="none" />
              <el-option label="Server酱" value="serverchan" />
              <el-option label="钉钉机器人" value="dingtalk" />
              <el-option label="企业微信机器人" value="weixin" />
            </el-select>
          </el-form-item>

          <!-- Server酱配置 -->
          <template v-if="notificationPlatform === 'serverchan'">
            <el-form-item label="Server酱密钥">
              <el-input 
                v-model="config.serverchan_key" 
                placeholder="请输入Server酱SendKey" 
                clearable
              />
              <div style="color: #909399; font-size: 12px; margin-top: 5px">
                获取地址: <a href="https://sct.ftqq.com" target="_blank">https://sct.ftqq.com</a>
              </div>
            </el-form-item>
          </template>

          <!-- 钉钉配置 -->
          <template v-if="notificationPlatform === 'dingtalk'">
            <el-form-item label="Webhook地址">
              <el-input 
                v-model="config.webhook_url" 
                placeholder="钉钉机器人 Webhook URL" 
                clearable
              />
            </el-form-item>
            <el-form-item label="加签密钥">
              <el-input 
                v-model="config.webhook_secret" 
                placeholder="加签密钥(可选)" 
                clearable
              />
              <div style="color: #909399; font-size: 12px; margin-top: 5px">
                安全设置为“加签”时填写，以SEC开头
              </div>
            </el-form-item>
          </template>

          <!-- 企业微信配置 -->
          <template v-if="notificationPlatform === 'weixin'">
            <el-form-item label="Webhook地址">
              <el-input 
                v-model="config.webhook_url" 
                placeholder="企业微信机器人 Webhook URL" 
                clearable
              />
            </el-form-item>
          </template>

          <!-- 测试按钮 -->
          <el-form-item v-if="notificationPlatform !== 'none'">
            <el-button 
              type="success" 
              @click="testNotification" 
              :loading="testingNotification"
              :disabled="!canTestNotification"
            >
              <el-icon><Bell /></el-icon> 测试通知
            </el-button>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="saveConfig" :loading="saving">
              <el-icon><Select /></el-icon> 保存配置
            </el-button>
            <el-button @click="loadConfig">
              <el-icon><Refresh /></el-icon> 重置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- Ping日志 -->
    <div v-else-if="props.activeTab === 'settings-logs'">
      <el-card shadow="hover">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: bold">主机Ping记录</span>
            <div>
              <el-select v-model="selectedHostId" placeholder="选择主机" style="width: 200px; margin-right: 10px" @change="loadPingLogs">
                <el-option label="全部主机" value="" />
                <el-option 
                  v-for="host in hosts" 
                  :key="host.id" 
                  :label="host.name" 
                  :value="host.id" 
                />
              </el-select>
              <el-button type="primary" @click="loadPingLogs">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
          </div>
        </template>

        <el-table :data="pingLogs" style="width: 100%" max-height="600">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column label="主机" width="150">
            <template #default="{ row }">
              {{ row.host_name }}
            </template>
          </el-table-column>
          <el-table-column label="地址" width="200">
            <template #default="{ row }">
              <span 
                @click="copyAddress(row.host_address)" 
                style="cursor: pointer; color: #409eff; text-decoration: underline"
                :title="'点击复制: ' + row.host_address"
              >
                {{ row.host_address }}
              </span>
              <el-icon 
                @click="copyAddress(row.host_address)" 
                style="margin-left: 5px; cursor: pointer; color: #409eff"
                :title="'复制地址'"
              >
                <CopyDocument />
              </el-icon>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === '正常' ? 'success' : 'danger'">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="packet_sent" label="发送" width="80" />
          <el-table-column prop="packet_received" label="接收" width="80" />
          <el-table-column label="丢包率" width="100">
            <template #default="{ row }">
              <el-tag :type="row.packet_loss > 20 ? 'danger' : row.packet_loss > 0 ? 'warning' : 'success'">
                {{ row.packet_loss }}%
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="延迟(ms)" width="180">
            <template #default="{ row }">
              最小: {{ row.min_rtt || '-' }} / 
              平均: {{ row.avg_rtt || '-' }} / 
              最大: {{ row.max_rtt || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="检测时间" width="180">
            <template #default="{ row }">
              {{ new Date(row.check_time).toLocaleString() }}
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 20px; text-align: right">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[20, 50, 100, 200]"
            :total="totalLogs"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadPingLogs"
            @current-change="loadPingLogs"
            background
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'settings-basic'
  }
})

const saving = ref(false)
const testingNotification = ref(false)
const notificationPlatform = ref('none')
const hosts = ref([])
const pingLogs = ref([])
const selectedHostId = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalLogs = ref(0)

const config = reactive({
  check_interval: 5,
  packet_count: 10,
  packet_timeout: 2,
  serverchan_key: '',
  webhook_url: '',
  webhook_secret: ''
})

// 计算属性：是否可以测试通知
const canTestNotification = computed(() => {
  if (notificationPlatform.value === 'serverchan') {
    return !!config.serverchan_key
  } else if (notificationPlatform.value === 'dingtalk' || notificationPlatform.value === 'weixin') {
    return !!config.webhook_url
  }
  return false
})

const loadConfig = async () => {
  try {
    const data = await api.getConfig()
    Object.assign(config, data)
    
    // 根据配置自动选择平台
    if (data.serverchan_key) {
      notificationPlatform.value = 'serverchan'
    } else if (data.webhook_url) {
      // 根据URL判断是钉钉还是企业微信
      if (data.webhook_url.includes('oapi.dingtalk.com')) {
        notificationPlatform.value = 'dingtalk'
      } else if (data.webhook_url.includes('qyapi.weixin.qq.com')) {
        notificationPlatform.value = 'weixin'
      } else {
        notificationPlatform.value = 'dingtalk' // 默认钉钉
      }
    } else {
      notificationPlatform.value = 'none'
    }
  } catch (error) {
    ElMessage.error('加载配置失败')
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await api.updateConfig({
      check_interval: config.check_interval,
      packet_count: config.packet_count,
      packet_timeout: config.packet_timeout,
      serverchan_key: config.serverchan_key || null,
      webhook_url: config.webhook_url || null,
      webhook_secret: config.webhook_secret || null
    })
    ElMessage.success('配置保存成功，监控间隔将在下次检测时生效')
    loadConfig()
  } catch (error) {
    ElMessage.error('配置保存失败')
  } finally {
    saving.value = false
  }
}

const loadHosts = async () => {
  try {
    hosts.value = await api.getHosts()
  } catch (error) {
    ElMessage.error('加载主机列表失败')
  }
}

const loadPingLogs = async () => {
  try {
    const hostId = selectedHostId.value || null
    const data = await api.getPingLogs(hostId, currentPage.value, pageSize.value)
    pingLogs.value = data.items || []
    totalLogs.value = data.total || 0
  } catch (error) {
    ElMessage.error('加载Ping日志失败')
  }
}

const testNotification = async () => {
  if (notificationPlatform.value === 'none') {
    ElMessage.warning('请先选择通知平台')
    return
  }

  let type = 'webhook'
  if (notificationPlatform.value === 'serverchan') {
    if (!config.serverchan_key) {
      ElMessage.warning('请先输入Server酱密钥')
      return
    }
    type = 'serverchan'
  } else {
    if (!config.webhook_url) {
      ElMessage.warning('请先输入Webhook地址')
      return
    }
    type = 'webhook'
  }

  testingNotification.value = true
  try {
    await api.testNotification(type)
    ElMessage.success('测试通知已发送，请检查是否收到')
  } catch (error) {
    ElMessage.error(`测试通知失败: ${error.response?.data?.detail || error.message || '网络错误'}`)
  } finally {
    testingNotification.value = false
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

// 监听 activeTab 变化，自动加载对应数据
watch(() => props.activeTab, (newTab) => {
  if (newTab === 'settings-logs') {
    loadPingLogs()
  }
})

onMounted(() => {
  loadConfig()
  loadHosts()
  // 首次进入如果是 Ping 日志标签，立即加载数据
  if (props.activeTab === 'settings-logs') {
    loadPingLogs()
  }
})
</script>
