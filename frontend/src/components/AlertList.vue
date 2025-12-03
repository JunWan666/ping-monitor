<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: bold">告警记录</span>
          <el-select v-model="timeRange" placeholder="选择时间范围" @change="loadAlerts" style="width: 150px">
            <el-option label="最近1小时" :value="1" />
            <el-option label="最近6小时" :value="6" />
            <el-option label="最近24小时" :value="24" />
            <el-option label="最近7天" :value="168" />
          </el-select>
        </div>
      </template>

      <el-table :data="alerts" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" align="center" header-align="center" />
        <el-table-column prop="host_name" label="主机名称" width="150" align="center" header-align="center" />
        <el-table-column label="告警类型" width="120" align="center" header-align="center">
          <template #default="{ row }">
            <el-tag v-if="row.alert_type === 'packet_loss'" type="warning">丢包告警</el-tag>
            <el-tag v-else-if="row.alert_type === 'unreachable'" type="danger">主机不可达</el-tag>
            <el-tag v-else type="info">{{ row.alert_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="告警信息" min-width="300" align="center" header-align="center">
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

      <div v-if="alerts.length === 0" style="text-align: center; padding: 40px; color: #909399">
        <el-icon :size="60"><CircleCheck /></el-icon>
        <div style="margin-top: 10px; font-size: 16px">暂无告警记录</div>
      </div>

      <div v-if="totalAlerts > 0" style="margin-top: 20px; text-align: right">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="totalAlerts"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadAlerts"
          @current-change="loadAlerts"
          background
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const alerts = ref([])
const timeRange = ref(24)
const currentPage = ref(1)
const pageSize = ref(10)
const totalAlerts = ref(0)

const loadAlerts = async () => {
  try {
    const data = await api.getAlerts(timeRange.value, currentPage.value, pageSize.value)
    alerts.value = data.items || []
    totalAlerts.value = data.total || 0
  } catch (error) {
    ElMessage.error('加载告警记录失败')
  }
}

// 清理Markdown标记，保留纯文本内容
const cleanMarkdown = (text) => {
  if (!text) return ''
  
  let result = text
    // 移除标题标记 (###)
    .replace(/^###\s+/gm, '')
    // 移除引用块 (>)
    .replace(/^>\s+/gm, '')
    // 移除分隔线 (---)
    .replace(/^---$/gm, '')
    // 移除链接格式 [text](url) 保留text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // 移除加粗 (**text**)
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    // 移除颜色标签 <font color=#xxx>text</font>
    .replace(/<font\s+color=[^>]+>([^<]*)<\/font>/gi, '$1')
    // 移除文字描述
    .replace(/主机异常告警/g, '')
    .replace(/主机恢复正常/g, '')
    .replace(/告警级别：/g, '')
    .replace(/状态：/g, '')
    .replace(/严重/g, '')
    .replace(/警告/g, '')
    .replace(/提醒/g, '')
    .replace(/已恢复/g, '')
    // 移除✅符号
    .replace(/\u2705/g, '')
    // 将换行符替换为空格
    .replace(/\n+/g, ' ')
    // 移除多余空格
    .replace(/\s{2,}/g, ' ')
    .trim()
  
  // 移除重复的emoji（保留第一个）
  const emojiPattern = /[\u{1F534}\u{1F7E0}\u{1F7E1}]/gu
  const emojis = result.match(emojiPattern)
  if (emojis && emojis.length > 1) {
    // 只保留第一个emoji，移除后续的
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
