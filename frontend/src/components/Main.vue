<template>
  <el-container style="height: 100vh">
      <!-- 侧边栏 -->
      <el-aside width="200px" style="background-color: #545c64">
        <div style="color: #fff; padding: 20px; font-size: 20px; font-weight: bold">
          Ping监控系统
        </div>
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical"
          background-color="#545c64"
          text-color="#fff"
          active-text-color="#ffd04b"
          @select="handleMenuSelect"
        >
          <el-menu-item index="datascreen">
            <el-icon><DataAnalysis /></el-icon>
            <span>可视化大屏</span>
          </el-menu-item>
          <el-menu-item index="dashboard">
            <el-icon><Monitor /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="databoard">
            <el-icon><TrendCharts /></el-icon>
            <span>数据看板</span>
          </el-menu-item>
          <el-menu-item index="hosts">
            <el-icon><Document /></el-icon>
            <span>主机管理</span>
          </el-menu-item>
          <el-menu-item index="alerts">
            <el-icon><Bell /></el-icon>
            <span>告警记录</span>
          </el-menu-item>
          <el-sub-menu index="settings">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </template>
            <el-menu-item index="settings-basic">
              <span>基本设置</span>
            </el-menu-item>
            <el-menu-item index="settings-datascreen">
              <span>可视化设置</span>
            </el-menu-item>
            <el-menu-item index="settings-logs">
              <span>Ping日志</span>
            </el-menu-item>
            <el-menu-item index="settings-system-logs">
              <span>系统日志</span>
            </el-menu-item>
            <el-menu-item index="settings-backup">
              <span>数据备份</span>
            </el-menu-item>
            <el-menu-item index="settings-profile">
              <span>修改密码</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-header style="background-color: #409eff; color: #fff; display: flex; align-items: center; justify-content: space-between">
          <h2 style="margin: 0">{{ menuTitle }}</h2>
          <el-button type="danger" size="small" @click="handleLogout">退出登录</el-button>
        </el-header>
        <el-main style="overflow-y: auto">
          <el-card v-if="componentError" shadow="never" class="page-error-card">
            <el-alert
              title="页面加载失败"
              :description="componentError"
              type="error"
              show-icon
              :closable="false"
            />
            <div class="page-error-actions">
              <el-button type="primary" @click="reloadPage">刷新页面</el-button>
              <el-button @click="openMenu('dashboard')">回到仪表盘</el-button>
            </div>
          </el-card>
          <iframe
            v-else-if="activeMenu === 'datascreen'"
            src="/datascreen-preview"
            style="width: 100%; height: 100%; border: none;"
          ></iframe>
          <KeepAlive :max="6" v-else>
            <component
              :is="currentComponent"
              :key="currentComponentKey"
              v-bind="currentComponentProps"
            />
          </KeepAlive>
        </el-main>
      </el-container>
    </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import api from '../api'
import { defineAsyncPage } from '../lib/asyncLoader'

const Dashboard = defineAsyncPage(() => import('./Dashboard.vue'))
const DataBoard = defineAsyncPage(() => import('./DataBoard.vue'))
const HostManage = defineAsyncPage(() => import('./HostManage.vue'))
const AlertList = defineAsyncPage(() => import('./AlertList.vue'))
const Settings = defineAsyncPage(() => import('./Settings.vue'))
const DataScreenSettings = defineAsyncPage(() => import('./DataScreenSettings.vue'))
const UserProfile = defineAsyncPage(() => import('./UserProfile.vue'))
const SystemLogs = defineAsyncPage(() => import('./SystemLogs.vue'))
const DatabaseBackup = defineAsyncPage(() => import('./DatabaseBackup.vue'))

const router = useRouter()
const activeMenu = ref('dashboard')
const componentError = ref('')

const menuTitles = {
  datascreen: '可视化大屏',
  dashboard: '监控仪表盘',
  databoard: '数据看板',
  hosts: '主机管理',
  alerts: '告警记录',
  'settings-basic': '系统设置 - 基本设置',
  'settings-datascreen': '系统设置 - 可视化设置',
  'settings-logs': '系统设置 - Ping日志',
  'settings-system-logs': '系统设置 - 系统日志',
  'settings-backup': '系统设置 - 数据备份',
  'settings-profile': '系统设置 - 修改密码'
}

const menuTitle = ref(menuTitles.dashboard)

const currentComponent = computed(() => {
  if (activeMenu.value === 'datascreen') {
    return null // 使用iframe显示
  }

  if (activeMenu.value === 'settings-profile') {
    return UserProfile
  }

  if (activeMenu.value === 'settings-datascreen') {
    return DataScreenSettings
  }

  if (activeMenu.value === 'settings-system-logs') {
    return SystemLogs
  }

  if (activeMenu.value === 'settings-backup') {
    return DatabaseBackup
  }

  if (activeMenu.value.startsWith('settings')) {
    return Settings
  }

  const menuComponentMap = {
    dashboard: Dashboard,
    databoard: DataBoard,
    hosts: HostManage,
    alerts: AlertList
  }

  return menuComponentMap[activeMenu.value] || Dashboard
})

const currentComponentKey = computed(() => {
  if (activeMenu.value === 'settings-basic' || activeMenu.value === 'settings-logs') {
    return 'settings'
  }

  return activeMenu.value
})

const currentComponentProps = computed(() => {
  if (currentComponentKey.value === 'settings') {
    return {
      activeTab: activeMenu.value
    }
  }

  return {}
})

const openMenu = (key) => {
  componentError.value = ''
  activeMenu.value = key
  menuTitle.value = menuTitles[key]
}

const handleMenuSelect = (key) => {
  openMenu(key)
}

const handleNavigateEvent = (event) => {
  const targetMenu = event?.detail?.menu
  if (targetMenu && menuTitles[targetMenu]) {
    openMenu(targetMenu)
  }
}

const reloadPage = () => {
  window.location.reload()
}

const validateSession = async () => {
  try {
    await api.getCurrentUser()
  } catch (error) {
    // api.js 会统一处理登录失效跳转
  }
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
      center: true
    })

    localStorage.removeItem('token')
    // 使用 replace 并刷新页面，确保清除所有组件状态
    window.location.href = '/login'
  } catch (error) {
    // 用户取消
  }
}

onMounted(() => {
  validateSession()
  window.addEventListener('ping-monitor:navigate', handleNavigateEvent)
})

onBeforeUnmount(() => {
  window.removeEventListener('ping-monitor:navigate', handleNavigateEvent)
})

onErrorCaptured((error) => {
  console.error('菜单页面渲染失败:', error)
  componentError.value = error?.message || '当前菜单页面渲染异常，请刷新页面后重试。'
  return false
})
</script>

<style scoped>
.el-menu-vertical {
  border-right: none;
}

.page-error-card {
  max-width: 720px;
  margin: 40px auto;
}

.page-error-actions {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}
</style>
