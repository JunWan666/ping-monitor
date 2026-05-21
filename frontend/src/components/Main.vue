<template>
  <div class="admin-shell" :class="{ 'is-mobile': isMobile }">
    <template v-if="isMobile">
      <div class="mobile-shell">
        <header class="mobile-topbar">
          <button
            v-if="mobileBackTarget"
            type="button"
            class="mobile-back-btn"
            aria-label="返回"
            @click="goMobileBack"
          >
            <el-icon><ArrowLeft /></el-icon>
          </button>
          <div v-else class="mobile-topbar__spacer"></div>
          <div class="mobile-topbar__title">
            <div class="mobile-topbar__name">{{ menuTitle }}</div>
          </div>
          <div class="mobile-topbar__spacer"></div>
        </header>

        <main class="mobile-content">
          
          <el-alert
            v-if="componentError"
            title="页面加载失败"
            :description="componentError"
            type="error"
            show-icon
            :closable="false"
            class="mobile-error"
          />

          <iframe
            v-else-if="activeMenu === 'datascreen'"
            src="/datascreen-preview"
            class="mobile-iframe"
          />

          <section v-else-if="activeMenu === 'mobile-me'" class="mobile-me">
            <el-card shadow="never" class="mobile-profile-card">
              <button type="button" class="mobile-profile-entry" @click="openMenu('settings-profile')">
                <div class="mobile-profile">
                  <div class="mobile-avatar">
                    <el-icon :size="28"><User /></el-icon>
                  </div>
                  <div class="mobile-profile__meta">
                    <div class="mobile-profile__name">{{ currentUsername || 'admin' }}</div>
                    <div class="mobile-profile__desc">系统管理员</div>
                  </div>
                </div>
                <el-icon class="mobile-chevron"><ArrowRight /></el-icon>
              </button>
            </el-card>

            <el-card shadow="never" class="mobile-menu-card">
              <button
                v-for="item in mobileSettingsActions"
                :key="item.key"
                type="button"
                class="mobile-menu-item"
                @click="openMenu(item.key)"
              >
                <div class="mobile-menu-item__left">
                  <el-icon class="mobile-menu-item__icon">
                    <component :is="item.icon" />
                  </el-icon>
                  <span>{{ item.label }}</span>
                </div>
                <el-icon class="mobile-chevron"><ArrowRight /></el-icon>
              </button>

              <button type="button" class="mobile-menu-item is-danger" @click="handleLogout">
                <div class="mobile-menu-item__left">
                  <el-icon class="mobile-menu-item__icon"><SwitchButton /></el-icon>
                  <span>退出登录</span>
                </div>
                <el-icon class="mobile-chevron"><ArrowRight /></el-icon>
              </button>
            </el-card>
          </section>

          <KeepAlive :max="6" v-else>
            <component
              :is="currentComponent"
              :key="currentComponentKey"
              v-bind="currentComponentProps"
            />
          </KeepAlive>
        </main>

        <nav class="mobile-tabbar" aria-label="底部导航">
          <button
            v-for="item in mobileTabs"
            :key="item.key"
            type="button"
            class="mobile-tabbar__item"
            :class="{ active: mobileTab === item.key }"
            @click="selectMobileTab(item.key)"
          >
            <el-icon>
              <component :is="item.icon" />
            </el-icon>
            <span v-if="item.key === 'alerts' && alertBadgeCount > 0" class="mobile-tabbar__badge">{{ alertBadgeCount }}</span>
            <span>{{ item.label }}</span>
          </button>
        </nav>
      </div>
    </template>

    <el-container v-else class="desktop-shell">
      <el-aside width="200px" class="desktop-aside">
        <div class="desktop-brand">Ping 监控系统</div>
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical desktop-menu"
          background-color="#1f2d3d"
          text-color="#cfd3dc"
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
              <span>Ping 日志</span>
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

      <el-container class="desktop-main-container">
        <el-header class="desktop-header">
          <h2>{{ menuTitle }}</h2>
          <el-button type="danger" size="small" @click="handleLogout">退出登录</el-button>
        </el-header>
        <el-main class="desktop-main">
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
            class="desktop-iframe"
          />

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
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  Bell,
  DataAnalysis,
  Document,
  Download,
  House,
  Lock,
  Monitor,
  Setting,
  SwitchButton,
  TrendCharts,
  User
} from '@element-plus/icons-vue'
import api from '../api'
import { defineAsyncPage } from '../lib/asyncLoader'
import { useViewport } from '../lib/useViewport'

const Dashboard = defineAsyncPage(() => import('./Dashboard.vue'))
const DataBoard = defineAsyncPage(() => import('./DataBoard.vue'))
const HostManage = defineAsyncPage(() => import('./HostManage.vue'))
const AlertList = defineAsyncPage(() => import('./AlertList.vue'))
const Settings = defineAsyncPage(() => import('./Settings.vue'))
const DataScreenSettings = defineAsyncPage(() => import('./DataScreenSettings.vue'))
const UserProfile = defineAsyncPage(() => import('./UserProfile.vue'))
const SystemLogs = defineAsyncPage(() => import('./SystemLogs.vue'))
const DatabaseBackup = defineAsyncPage(() => import('./DatabaseBackup.vue'))

const activeMenu = ref('dashboard')
const componentError = ref('')
const currentUsername = ref('')
const alertBadgeCount = ref(0)
const { isMobile } = useViewport()

const menuTitles = {
  datascreen: '可视化大屏',
  dashboard: '首页',
  databoard: '数据看板',
  hosts: '主机管理',
  alerts: '告警记录',
  'settings-basic': '系统设置 - 基本设置',
  'settings-datascreen': '系统设置 - 可视化设置',
  'settings-logs': '系统设置 - Ping 日志',
  'settings-system-logs': '系统设置 - 系统日志',
  'settings-backup': '系统设置 - 数据备份',
  'settings-profile': '系统设置 - 修改密码',
  'mobile-me': '我的'
}

const mobileTabs = [
  { key: 'home', label: '首页', icon: House },
  { key: 'hosts', label: '主机', icon: Monitor },
  { key: 'alerts', label: '告警', icon: Bell },
  { key: 'me', label: '我的', icon: User }
]

const mobileSettingsActions = [
  { key: 'settings-basic', label: '基础设置', icon: Setting },
  { key: 'settings-datascreen', label: '大屏设置', icon: DataAnalysis },
  { key: 'settings-logs', label: 'Ping 日志', icon: Document },
  { key: 'settings-system-logs', label: '系统日志', icon: Monitor },
  { key: 'settings-backup', label: '数据备份', icon: Download },
  { key: 'settings-profile', label: '修改密码', icon: Lock }
]

const menuTitle = computed(() => menuTitles[activeMenu.value] || '首页')

const mobileTab = computed(() => {
  if (activeMenu.value === 'dashboard' || activeMenu.value === 'datascreen') {
    return 'home'
  }

  if (activeMenu.value === 'hosts') return 'hosts'
  if (activeMenu.value === 'alerts') return 'alerts'
  return 'me'
})

const mobileBackTarget = computed(() => {
  if (!isMobile.value) {
    return ''
  }

  if (activeMenu.value.startsWith('settings')) {
    return 'mobile-me'
  }

  if (activeMenu.value === 'databoard' || activeMenu.value === 'datascreen') {
    return 'dashboard'
  }

  return ''
})

const currentComponent = computed(() => {
  if (activeMenu.value === 'datascreen' || activeMenu.value === 'mobile-me') {
    return null
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
  if (activeMenu.value === 'settings-basic' || activeMenu.value === 'settings-logs') {
    return {
      activeTab: activeMenu.value
    }
  }

  return {}
})

const openMenu = (key) => {
  componentError.value = ''
  activeMenu.value = key
}

const handleMenuSelect = (key) => {
  openMenu(key)
}

const selectMobileTab = (key) => {
  if (key === 'home') {
    openMenu('dashboard')
  } else if (key === 'hosts') {
    openMenu('hosts')
  } else if (key === 'alerts') {
    openMenu('alerts')
  } else {
    openMenu('mobile-me')
  }
}

const goMobileBack = () => {
  if (mobileBackTarget.value) {
    openMenu(mobileBackTarget.value)
  }
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
    // 统一由 api.js 处理登录失效跳转
  }
}

const loadCurrentUser = async () => {
  try {
    const user = await api.getCurrentUser()
    currentUsername.value = user?.username || ''
  } catch (error) {
    currentUsername.value = ''
  }
}

const loadHeaderStats = async () => {
  try {
    const dashboard = await api.getDashboard()
    alertBadgeCount.value = dashboard?.recent_alerts || 0
  } catch (error) {
    alertBadgeCount.value = 0
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
    window.location.href = '/login'
  } catch (error) {
    // 用户取消
  }
}

onMounted(() => {
  validateSession()
  loadCurrentUser()
  loadHeaderStats()
  window.addEventListener('ping-monitor:navigate', handleNavigateEvent)
})

onBeforeUnmount(() => {
  window.removeEventListener('ping-monitor:navigate', handleNavigateEvent)
})

onErrorCaptured((error) => {
  console.error('菜单页面渲染失败:', error)
  componentError.value = error?.message || '当前页面渲染异常，请刷新后重试。'
  return false
})
</script>

<style scoped>
.admin-shell {
  --mobile-topbar-height: 56px;
  --mobile-tabbar-height: 72px;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: #f5f7fb;
}

.desktop-shell {
  width: 100%;
  height: 100%;
}

.desktop-aside {
  background: #1f2d3d;
}

.desktop-brand {
  color: #fff;
  padding: 20px 18px 14px;
  font-size: 18px;
  font-weight: 700;
}

.desktop-menu {
  border-right: none;
}

.desktop-main-container {
  min-width: 0;
}

.desktop-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 64px;
  background: #fff;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.06);
}

.desktop-header h2 {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.desktop-main {
  padding: 20px;
  overflow-y: auto;
}

.desktop-iframe {
  width: 100%;
  height: calc(100vh - 84px);
  border: none;
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

.mobile-shell {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-width: 0;
  overflow: hidden;
  background: #f5f7fb;
}

.mobile-topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  height: var(--mobile-topbar-height);
  padding: 0 14px;
  background: #fff;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.06);
  flex: 0 0 auto;
}

.mobile-topbar__spacer {
  min-width: 1px;
}

.mobile-back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 999px;
  background: #f3f6fb;
  color: #111827;
  font-size: 18px;
}

.mobile-topbar__title {
  min-width: 0;
  text-align: center;
}

.mobile-topbar__name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.mobile-content {
  display: flex;
  flex-direction: column;
  flex: 0 0 calc(100vh - var(--mobile-topbar-height));
  width: 100%;
  height: calc(100vh - var(--mobile-topbar-height));
  flex-basis: calc(100dvh - var(--mobile-topbar-height));
  height: calc(100dvh - var(--mobile-topbar-height));
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: 12px 12px calc(var(--mobile-tabbar-height) + 10px);
  box-sizing: border-box;
}

.mobile-error {
  margin-bottom: 12px;
}

.mobile-iframe {
  width: 100%;
  height: calc(100vh - 140px);
  border: none;
  border-radius: 12px;
  background: #fff;
}

.mobile-me {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: 4px;
}

.mobile-profile-card {
  border-radius: 14px;
  padding: 0;
}

.mobile-profile-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 12px 6px 12px 4px;
  border: none;
  background: transparent;
  color: inherit;
}

.mobile-profile {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mobile-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: #eef4ff;
  color: #3b82f6;
  flex: 0 0 auto;
}

.mobile-profile__meta {
  min-width: 0;
}

.mobile-profile__name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.mobile-profile__desc {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}

.mobile-chevron {
  color: #c0c4cc;
  font-size: 16px;
}

.mobile-menu-card {
  border-radius: 14px;
  overflow: hidden;
}

.mobile-menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 15px 4px 15px 0;
  border: none;
  border-bottom: 1px solid #eef0f4;
  background: transparent;
  color: #111827;
}

.mobile-menu-item:last-child {
  border-bottom: none;
}

.mobile-menu-item.is-danger {
  color: #f56c6c;
}

.mobile-menu-item__left {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  font-weight: 500;
}

.mobile-menu-item__icon {
  font-size: 18px;
  color: #3b82f6;
}

.mobile-menu-item.is-danger .mobile-menu-item__icon {
  color: #f56c6c;
}

.mobile-tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  height: var(--mobile-tabbar-height);
  padding: 8px 10px calc(8px + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.98);
  border-top: 1px solid #e5e7eb;
  box-shadow: 0 -6px 24px rgba(15, 23, 42, 0.06);
  box-sizing: border-box;
}

.mobile-tabbar__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  border: none;
  background: transparent;
  color: #6b7280;
  padding: 0;
}

.mobile-tabbar__item .el-icon {
  font-size: 18px;
  position: relative;
}

.mobile-tabbar__item span {
  font-size: 11px;
  line-height: 1;
}

.mobile-tabbar__badge {
  position: absolute;
  top: 4px;
  right: calc(50% - 18px);
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #f56c6c;
  color: #fff;
  font-size: 10px;
  line-height: 16px;
}

.mobile-tabbar__item.active {
  color: #2563eb;
}

.mobile-tabbar__item:focus-visible {
  outline: none;
}

:deep(.el-menu-vertical) {
  border-right: none;
}

@media (max-width: 768px) {
  .admin-shell {
    height: 100dvh;
  }

  .mobile-shell {
    height: 100dvh;
  }

  .mobile-content :deep(.dashboard-page),
  .mobile-content :deep(.host-manage-page),
  .mobile-content :deep(.alert-list-page),
  .mobile-content :deep(.databoard-page),
  .mobile-content :deep(.settings-root),
  .mobile-content :deep(.settings-page),
  .mobile-content :deep(.settings-logs-page),
  .mobile-content :deep(.system-logs-page),
  .mobile-content :deep(.user-profile-page),
  .mobile-content :deep(.datascreen-settings),
  .mobile-content :deep(.database-backup),
  .mobile-content :deep(.database-backup-page) {
    height: 100%;
    min-height: 0;
    min-width: 0;
    max-width: 100%;
    box-sizing: border-box;
  }
}

@media (max-width: 768px) and (max-height: 680px) {
  .admin-shell {
    --mobile-topbar-height: 48px;
    --mobile-tabbar-height: 62px;
  }

  .mobile-topbar {
    padding: 0 10px;
  }

  .mobile-topbar__name {
    font-size: 15px;
  }

  .mobile-content {
    padding: 8px 10px calc(var(--mobile-tabbar-height) + 8px);
  }

  .mobile-tabbar {
    padding: 6px 10px calc(6px + env(safe-area-inset-bottom));
  }

  .mobile-tabbar__item {
    gap: 2px;
  }

  .mobile-tabbar__item .el-icon {
    font-size: 17px;
  }
}

@media (max-width: 420px) {
  .mobile-shortcut-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
