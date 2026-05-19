<template>
  <div class="datascreen-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>可视化大屏设置</span>
          <el-button type="primary" :loading="saving" @click="saveConfig">保存设置</el-button>
        </div>
      </template>

      <el-alert
        title="关闭公开访问后，游客访问 / 会进入登录页；后台预览仍然可用。"
        type="info"
        :closable="false"
        class="page-alert"
      />

      <el-form :model="config" label-width="140px">
        <el-divider content-position="left">基础设置</el-divider>

        <el-form-item label="大屏名称">
          <el-input
            v-model="config.brand_name"
            maxlength="60"
            show-word-limit
            placeholder="例如 your-service"
            style="max-width: 360px"
          />
          <span class="form-tip">用于展示“名称 网络监控可视化大屏”</span>
        </el-form-item>

        <el-form-item label="公开访问开关">
          <el-switch v-model="config.public_enabled" />
          <span class="form-tip">
            {{ config.public_enabled ? '开启后游客可直接访问可视化大屏' : '关闭后首页默认进入登录界面' }}
          </span>
        </el-form-item>

        <el-form-item label="数据刷新间隔">
          <el-input-number
            v-model="config.refresh_interval"
            :min="1"
            :max="60"
            :step="1"
          />
          <span class="form-tip">秒，建议 5-10 秒</span>
        </el-form-item>

        <el-form-item label="主题颜色">
          <el-radio-group v-model="config.theme_color">
            <el-radio label="blue">科技蓝</el-radio>
            <el-radio label="green">翠绿</el-radio>
            <el-radio label="purple">紫色</el-radio>
            <el-radio label="red">红色</el-radio>
            <el-radio label="orange">橙色</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-divider content-position="left">3D 效果</el-divider>

        <el-form-item label="启用 3D 效果">
          <el-switch v-model="config.enable_3d" />
          <span class="form-tip">开启后地图以更立体的方式展示</span>
        </el-form-item>

        <el-form-item v-if="config.enable_3d" label="地图视角角度">
          <el-slider
            v-model="config.map_view_angle"
            :min="0"
            :max="90"
            :step="5"
            show-stops
          />
          <span class="form-tip">{{ config.map_view_angle }}°，0° 为俯视，90° 为侧视</span>
        </el-form-item>

        <el-form-item v-if="config.enable_3d" label="显示流光飞线">
          <el-switch v-model="config.show_flow_lines" />
          <span class="form-tip">模拟监控链路的数据流动效果</span>
        </el-form-item>

        <el-divider content-position="left">动画设置</el-divider>

        <el-form-item label="启用动画效果">
          <el-switch v-model="config.enable_animation" />
          <span class="form-tip">控制数字滚动、图表过渡等动画</span>
        </el-form-item>

        <el-form-item v-if="config.enable_animation" label="粒子数量">
          <el-slider
            v-model="config.particle_count"
            :min="0"
            :max="1000"
            :step="50"
            show-stops
          />
          <span class="form-tip">{{ config.particle_count }} 个背景粒子</span>
        </el-form-item>

        <el-divider content-position="left">预览</el-divider>

        <el-form-item label="后台预览">
          <el-button type="success" @click="openPreview">
            <el-icon><View /></el-icon>
            打开后台预览
          </el-button>
          <span class="form-tip">预览页不受公开访问开关影响，适合设计和调试</span>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { View } from '@element-plus/icons-vue'
import api from '../api'

const defaultConfig = {
  brand_name: '',
  refresh_interval: 5,
  enable_3d: true,
  enable_animation: true,
  map_view_angle: 45,
  particle_count: 100,
  show_flow_lines: true,
  theme_color: 'blue',
  public_enabled: true
}

const config = ref({ ...defaultConfig })
const saving = ref(false)

const normalizeConfig = (payload = {}) => ({
  brand_name: payload.brand_name ?? defaultConfig.brand_name,
  refresh_interval: payload.refresh_interval ?? defaultConfig.refresh_interval,
  enable_3d: payload.enable_3d ?? defaultConfig.enable_3d,
  enable_animation: payload.enable_animation ?? defaultConfig.enable_animation,
  map_view_angle: payload.map_view_angle ?? defaultConfig.map_view_angle,
  particle_count: payload.particle_count ?? defaultConfig.particle_count,
  show_flow_lines: payload.show_flow_lines ?? defaultConfig.show_flow_lines,
  theme_color: payload.theme_color ?? defaultConfig.theme_color,
  public_enabled: payload.public_enabled ?? defaultConfig.public_enabled
})

const loadConfig = async () => {
  try {
    const response = await api.getDataScreenConfig()
    config.value = normalizeConfig(response)
  } catch (error) {
    console.error('加载可视化配置失败:', error)
    ElMessage.error('加载可视化配置失败')
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const response = await api.updateDataScreenConfig(config.value)
    config.value = normalizeConfig(response)
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存可视化配置失败:', error)
    ElMessage.error(error.response?.data?.detail || '保存可视化配置失败')
  } finally {
    saving.value = false
  }
}

const openPreview = () => {
  window.open('/datascreen-preview', '_blank')
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.datascreen-settings {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-alert {
  margin-bottom: 20px;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.el-divider {
  margin: 30px 0 20px;
}
</style>
