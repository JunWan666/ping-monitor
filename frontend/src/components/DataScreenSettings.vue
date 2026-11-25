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
          <el-form-item label="品牌名称">
            <el-input v-model="config.brand_name" maxlength="60" show-word-limit placeholder="如 Acme" />
            <p>显示在大屏左上角，也用于浏览器标题；留空时显示 ping。</p>
          </el-form-item>
          <el-form-item label="数据刷新间隔">
            <div class="datascreen-control"><el-input-number v-model="config.refresh_interval" :min="1" :max="60" :precision="0" /><span>秒</span></div>
            <p>节点状态的轮询频率；告警流固定每 30 秒刷新。</p>
          </el-form-item>
          <el-form-item label="公开访问大屏">
            <div class="datascreen-control"><el-switch v-model="config.public_enabled" /><span>{{ config.public_enabled ? '游客可访问首页' : '仅后台预览可用' }}</span></div>
          </el-form-item>
        </template>
        <template v-else-if="section === 'map'">
          <el-form-item label="立体视角">
            <div class="datascreen-control"><el-switch v-model="config.enable_3d" /><span>{{ config.enable_3d ? '倾斜地图 + 城市光柱（柱高 = 节点数）' : '平面地图，只显示节点光环' }}</span></div>
          </el-form-item>
          <el-form-item label="倾斜角度">
            <div class="datascreen-control"><el-slider v-model="config.map_view_angle" :min="0" :max="MAX_TILT" :step="5" :disabled="!config.enable_3d" /><span>{{ config.map_view_angle }}°</span></div>
            <p>0° 为正俯视，默认 40°。</p>
          </el-form-item>
          <el-form-item label="探测连线">
            <div class="datascreen-control"><el-switch v-model="config.show_flow_lines" /><span>控制中心到各城市的连线与往返光点</span></div>
          </el-form-item>
          <el-form-item label="光点速度">
            <div class="datascreen-control">
              <el-slider v-model="config.flow_speed" :min="FLOW_SPEED.min" :max="FLOW_SPEED.max" :step="10" :format-tooltip="speedLabel" :disabled="!config.show_flow_lines || !config.enable_animation" />
              <span>{{ speedLabel(config.flow_speed) }}</span>
            </div>
            <p>往左越慢，往右越快；1.0× 为标准（城市平均 RTT × 80 倍慢放），0.5× 慢一倍。</p>
          </el-form-item>
          <el-form-item label="动画效果">
            <div class="datascreen-control"><el-switch v-model="config.enable_animation" /><span>{{ config.enable_animation ? '光柱扫描、彗星、告警脉冲等动效' : '静态显示，适合低性能设备' }}</span></div>
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

// The screen clamps the tilt to 60°; steeper angles flatten the map into a sliver.
const MAX_TILT = 60
// Comet speed in percent of the standard pace; the API accepts 20–200.
const FLOW_SPEED = { min: 20, max: 200 }
const speedLabel = (value) => `${(Number(value) / 100).toFixed(1)}×${Number(value) === 100 ? ' 标准' : ''}`

// theme_color, particle_count and amap_key belonged to the previous screen. They are not shown,
// but are loaded and sent back unchanged so saving here never resets stored values.
const defaultConfig = {
  brand_name: '',
  refresh_interval: 5,
  enable_3d: true,
  enable_animation: true,
  map_view_angle: 40,
  particle_count: 100,
  show_flow_lines: true,
  flow_speed: 100,
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
  { key: 'basic', label: '基础设置', description: '设置品牌名称、刷新频率和访问范围。' },
  { key: 'map', label: '地图与动效', description: '调整节点地图的视角、连线和动画。' },
  { key: 'preview', label: '后台预览', description: '在新标签页查看当前已保存的效果。' }
]
const activeSection = computed(() => sections.find(item => item.key === section.value))

const normalizeConfig = (payload = {}) => {
  const next = {}
  for (const key of Object.keys(defaultConfig)) next[key] = payload[key] ?? defaultConfig[key]
  next.map_view_angle = Math.min(MAX_TILT, Math.max(0, Number(next.map_view_angle) || 0))
  next.flow_speed = Math.min(FLOW_SPEED.max, Math.max(FLOW_SPEED.min, Number(next.flow_speed) || defaultConfig.flow_speed))
  return next
}

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
.datascreen-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 26px; align-content: start; }
.datascreen-form :deep(.el-form-item) { min-width: 0; margin: 0; }
.datascreen-form :deep(.el-form-item__label) { margin-bottom: 4px; font-weight: 600; line-height: 1.4; }
.datascreen-form :deep(.el-form-item__content) { display: block; }
.datascreen-control { display: flex; align-items: center; width: 100%; gap: 10px; font-size: 12px; }
.datascreen-control > span { flex-shrink: 0; color: var(--el-text-color-regular); }
.datascreen-control :deep(.el-input-number) { width: min(112px, 80%); }
.datascreen-control :deep(.el-slider) { flex: 1; margin-inline: 8px; }
.datascreen-settings__actions { margin-top: 18px; padding-top: 14px; }
@media (max-width: 768px) { .datascreen-settings__card { flex: 1 1 0; }
  .datascreen-settings__card :deep(.el-card__header), .datascreen-settings__card :deep(.el-card__body) { padding: 10px 12px; }
  .datascreen-form { grid-template-columns: minmax(0, 1fr); gap: 10px; }
  .datascreen-control > span { flex-shrink: 1; }
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
