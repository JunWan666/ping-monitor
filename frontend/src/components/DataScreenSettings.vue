<template>
  <div class="datascreen-settings admin-settings" v-loading="loading">
    <nav v-if="!isMobile" class="admin-settings__nav" aria-label="可视化设置分类">
      <button v-for="item in sections" :key="item.key" type="button" class="admin-settings__tab" :class="{ active: section === item.key }" :aria-current="section === item.key ? 'page' : undefined" @click="section = item.key">{{ item.label }}</button>
    </nav>
    <el-select v-else v-model="section" class="admin-settings__select" aria-label="可视化设置分类">
      <el-option v-for="item in sections" :key="item.key" :value="item.key" :label="item.label" />
    </el-select>
    <el-card shadow="never" class="admin-settings__card datascreen-settings__card">
      <template #header>
        <h3>{{ activeSection.label }}</h3>
        <p>{{ activeSection.description }}</p>
      </template>
      <el-form :model="config" label-position="top" class="datascreen-form">
        <template v-if="section === 'basic'">
          <el-form-item label="大屏名称">
            <el-input v-model="config.brand_name" maxlength="60" show-word-limit placeholder="输入大屏名称" />
          </el-form-item>
          <el-form-item label="主题颜色">
            <el-select v-model="config.theme_color"><el-option v-for="theme in themes" :key="theme.value" v-bind="theme" /></el-select>
          </el-form-item>
          <el-form-item label="数据刷新间隔">
            <div class="datascreen-control"><el-input-number v-model="config.refresh_interval" :min="1" :max="60" :precision="0" /><span>秒</span></div>
          </el-form-item>
          <el-form-item label="公开访问大屏">
            <div class="datascreen-control"><el-switch v-model="config.public_enabled" /><span>{{ config.public_enabled ? '游客可访问首页' : '仅后台预览可用' }}</span></div>
          </el-form-item>
        </template>
        <el-form-item v-else-if="section === 'map'" label="高德地图 Key" class="datascreen-form__wide">
          <el-input v-model="config.amap_key" placeholder="选填" clearable />
          <p>使用高德底图时，请申请 Web 端 JS API Key，并在高德后台设置访问域名白名单。</p>
          <el-link type="primary" :underline="false" @click="openAmapConsole">打开高德控制台</el-link>
        </el-form-item>
        <template v-else-if="section === '3d'">
          <el-form-item label="启用 3D 效果"><el-switch v-model="config.enable_3d" /></el-form-item>
          <el-form-item label="地图视角" class="datascreen-form__wide">
            <div class="datascreen-control"><el-slider v-model="config.map_view_angle" :min="0" :max="90" :step="5" :disabled="!config.enable_3d" /><span>{{ config.map_view_angle }}°</span></div>
          </el-form-item>
        </template>
        <template v-else-if="section === 'animation'">
          <el-form-item label="启用动画效果"><el-switch v-model="config.enable_animation" /></el-form-item>
          <el-form-item label="背景粒子数量">
            <div class="datascreen-control"><el-slider v-model="config.particle_count" :min="0" :max="1000" :step="50" :disabled="!config.enable_animation" /><span>{{ config.particle_count }}</span></div>
          </el-form-item>
        </template>
      </el-form>
      <div class="admin-settings__actions datascreen-settings__actions">
        <el-button v-if="section !== 'preview'" type="primary" :loading="saving" @click="saveConfig">保存设置</el-button>
        <el-button :type="section === 'preview' ? 'primary' : undefined" :icon="View" @click="openPreview">打开后台预览</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { View } from '@element-plus/icons-vue'
import api from '../api'
import { useViewport } from '../lib/useViewport'

const AMAP_CONSOLE_URL = 'https://console.amap.com/dev/key/app'
const openAmapConsole = () => window.open(AMAP_CONSOLE_URL, '_blank', 'noopener')

const defaultConfig = {
  brand_name: '',
  refresh_interval: 5,
  enable_3d: true,
  enable_animation: true,
  map_view_angle: 45,
  particle_count: 100,
  show_flow_lines: true,
  theme_color: 'blue',
  public_enabled: true,
  amap_key: ''
}

const config = ref({ ...defaultConfig })
const saving = ref(false)
const section = ref('basic')
const { isMobile } = useViewport()
const loading = ref(false)
const sections = [
  { key: 'basic', label: '基础设置', description: '设置大屏名称、主题和访问范围。' },
  { key: 'map', label: '地图底图', description: '默认使用中国矢量地图。配置 Key 后，大屏可手动切换高德。' },
  { key: '3d', label: '3D 效果', description: '设置地图视角。' },
  { key: 'animation', label: '动画效果', description: '调整数字滚动、图表过渡和背景粒子。' },
  { key: 'preview', label: '后台预览', description: '在新标签页查看当前已保存的效果。' }
]
const activeSection = computed(() => sections.find(item => item.key === section.value))
const themes = [
  { value: 'blue', label: '科技蓝' }, { value: 'green', label: '翠绿' }, { value: 'purple', label: '紫色' },
  { value: 'red', label: '红色' }, { value: 'orange', label: '橙色' }
]

const normalizeConfig = (payload = {}) => ({
  brand_name: payload.brand_name ?? defaultConfig.brand_name,
  refresh_interval: payload.refresh_interval ?? defaultConfig.refresh_interval,
  enable_3d: payload.enable_3d ?? defaultConfig.enable_3d,
  enable_animation: payload.enable_animation ?? defaultConfig.enable_animation,
  map_view_angle: payload.map_view_angle ?? defaultConfig.map_view_angle,
  particle_count: payload.particle_count ?? defaultConfig.particle_count,
  show_flow_lines: payload.show_flow_lines ?? defaultConfig.show_flow_lines,
  theme_color: payload.theme_color ?? defaultConfig.theme_color,
  public_enabled: payload.public_enabled ?? defaultConfig.public_enabled,
  amap_key: payload.amap_key ?? defaultConfig.amap_key
})

const loadConfig = async () => {
  loading.value = true
  try {
    const response = await api.getDataScreenConfig()
    config.value = normalizeConfig(response)
  } catch (error) {
    console.error('加载可视化配置失败:', error)
    ElMessage.error('加载可视化配置失败')
  } finally {
    loading.value = false
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
.datascreen-settings__card :deep(.el-card__header) { padding: 14px 20px; }
.datascreen-settings__card :deep(.el-card__body) { padding: 20px; }
.datascreen-settings__card { display: flex; flex: 1 1 0; flex-direction: column; min-height: 0; }
.datascreen-settings__card :deep(.el-card__body) { display: flex; flex: 1 1 0; flex-direction: column; min-height: 0; }
.datascreen-settings__card :deep(.el-card__body) > .el-form { flex: 1 1 0; min-height: 0; }
.datascreen-settings h3 { font-size: 17px; line-height: 1.3; }
.datascreen-settings p { margin: 5px 0 0; color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.5; }
.datascreen-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 26px; }
.datascreen-form :deep(.el-form-item) { min-width: 0; margin: 0; }
.datascreen-form :deep(.el-form-item__label) { margin-bottom: 4px; font-weight: 600; line-height: 1.4; }
.datascreen-form__wide { grid-column: 1 / -1; }
.datascreen-form__wide :deep(.el-form-item__content) { display: block; }
.datascreen-control { display: flex; align-items: center; width: 100%; gap: 10px; font-size: 12px; }
.datascreen-control > span { flex-shrink: 0; }
.datascreen-control :deep(.el-input-number) { width: min(112px, 80%); }
.datascreen-control :deep(.el-slider) { flex: 1; margin-inline: 8px; }
.datascreen-settings__actions { margin-top: 18px; padding-top: 14px; }
@media (max-width: 768px) { .datascreen-settings__card { flex: 1 1 0; }
  .datascreen-settings__card :deep(.el-card__header), .datascreen-settings__card :deep(.el-card__body) { padding: 10px 12px; }
  .datascreen-form { gap: 10px; }
  .datascreen-settings__actions { margin-top: 12px; padding-top: 8px; }
}
@media (max-width: 768px) and (max-height: 430px) and (orientation: landscape) {
  .datascreen-settings__card :deep(.el-card__header), .datascreen-settings__card :deep(.el-card__body) { padding-block: 6px; }
  .datascreen-settings__card h3 { font-size: 14px; }
  .datascreen-settings p { margin-top: 2px; }
  .datascreen-form { gap: 6px 12px; }
  .datascreen-settings__actions { margin-top: 6px; padding-top: 5px; }
  .datascreen-settings .admin-settings__nav { grid-template-columns: repeat(3, minmax(0, 1fr)); grid-auto-flow: row; }
  .datascreen-settings .admin-settings__tab { min-height: 32px; font-size: 12px; }
  .datascreen-settings__actions :deep(.el-button) { min-height: 26px; height: 26px; }
}
</style>
