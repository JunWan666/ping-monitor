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
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="host_name" label="主机名称" width="150" />
        <el-table-column label="告警类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.alert_type === 'packet_loss'" type="warning">丢包告警</el-tag>
            <el-tag v-else-if="row.alert_type === 'unreachable'" type="danger">主机不可达</el-tag>
            <el-tag v-else type="info">{{ row.alert_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="告警信息" min-width="300" />
        <el-table-column label="发送状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_sent" type="success">已发送</el-tag>
            <el-tag v-else type="info">未发送</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="告警时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
      </el-table>

      <div v-if="alerts.length === 0" style="text-align: center; padding: 40px; color: #909399">
        <el-icon :size="60"><CircleCheck /></el-icon>
        <div style="margin-top: 10px; font-size: 16px">暂无告警记录</div>
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

const loadAlerts = async () => {
  try {
    alerts.value = await api.getAlerts(timeRange.value)
  } catch (error) {
    ElMessage.error('加载告警记录失败')
  }
}

onMounted(() => {
  loadAlerts()
})
</script>
