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
          <RouterView v-else v-slot="{ Component }">
            <KeepAlive :max="6">
              <component :is="Component" :key="route.name === 'AdminSettings' ? route.name : route.fullPath" />
            </KeepAlive>
          </RouterView>
        </main>

        <nav class="mobile-tabbar" aria-label="底部导航">
          <button
            v-for="item in mobileTabs"
            :key="item.key"
            type="button"
            class="mobile-tabbar__item"
            :class="{ active: mobileTab === item.key }"
            :aria-current="mobileTab === item.key ? 'page' : undefined"
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

    <el-container v-else class="desktop-shell" :class="{ 'is-sidebar-collapsed': sidebarCollapsed }">
      <el-aside :width="sidebarCollapsed ? '76px' : '240px'" class="desktop-aside">
        <div class="desktop-brand">
          <div class="desktop-brand__mark" aria-hidden="true"><span>⌁</span></div>
          <div v-show="!sidebarCollapsed" class="desktop-brand__copy">
            <strong>Ping Monitor</strong>
            <span>基础设施监控平台</span>
          </div>
        </div>
        <div v-show="!sidebarCollapsed" class="desktop-nav-caption">工作台</div>
        <el-menu
          :key="menuKey"
          :default-active="menuKey"
          :default-openeds="isSettingsMenu ? ['settings'] : []"
          :collapse="sidebarCollapsed"
          class="el-menu-vertical desktop-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="dashboard"><el-icon><Monitor /></el-icon><span>仪表盘</span></el-menu-item>
          <el-menu-item index="datascreen"><el-icon><DataAnalysis /></el-icon><span>可视化大屏</span></el-menu-item>
          <el-menu-item index="databoard"><el-icon><TrendCharts /></el-icon><span>数据看板</span></el-menu-item>
          <div v-show="!sidebarCollapsed" class="desktop-nav-caption desktop-nav-caption--section">监控资源</div>
          <el-menu-item index="hosts"><el-icon><Document /></el-icon><span>主机管理</span></el-menu-item>
          <el-menu-item index="domains"><el-icon><Connection /></el-icon><span>域名监控</span></el-menu-item>
          <el-menu-item index="alerts">
            <el-icon><Bell /></el-icon><span>告警记录</span>
            <span v-if="alertBadgeCount > 0 && !sidebarCollapsed" class="desktop-menu-badge">{{ alertBadgeCount }}</span>
          </el-menu-item>
          <el-sub-menu index="settings">
            <template #title><el-icon><Setting /></el-icon><span>系统设置</span></template>
            <el-menu-item index="settings-basic"><span>基本设置</span></el-menu-item>
            <el-menu-item index="settings-datascreen"><span>可视化设置</span></el-menu-item>
            <el-menu-item index="settings-logs"><span>Ping 日志</span></el-menu-item>
            <el-menu-item index="settings-system-logs"><span>系统日志</span></el-menu-item>
            <el-menu-item index="settings-backup"><span>数据备份</span></el-menu-item>
            <el-menu-item index="settings-profile"><span>修改密码</span></el-menu-item>
          </el-sub-menu>
        </el-menu>
        <div class="desktop-aside-footer">
          <div v-show="!sidebarCollapsed" class="desktop-aside-footer__hint">数据每 60 秒自动同步</div>
          <button type="button" class="sidebar-toggle" :aria-label="sidebarCollapsed ? '展开侧栏' : '收起侧栏'" @click="sidebarCollapsed = !sidebarCollapsed">
            <el-icon><Expand v-if="sidebarCollapsed" /><Fold v-else /></el-icon>
            <span v-show="!sidebarCollapsed">收起侧栏</span>
          </button>
        </div>
      </el-aside>

      <el-container class="desktop-main-container">
        <el-header class="desktop-header">
          <div class="desktop-header__left">
            <div class="desktop-breadcrumb"><span>工作台</span><el-icon><ArrowRight /></el-icon><strong>{{ menuTitle }}</strong></div>
            <p>{{ isDataScreen ? '实时了解节点分布与网络健康度' : '集中管理监控目标与运行数据' }}</p>
          </div>
          <div class="desktop-header__right">
            <el-tag v-if="menuKey !== 'datascreen'" type="success" effect="plain" round class="system-status-tag"><el-icon><SuccessFilled /></el-icon>系统运行正常</el-tag>
            <el-divider direction="vertical" />
            <el-dropdown trigger="click" @command="handleHeaderCommand">
              <button type="button" class="header-user">
                <el-avatar :size="32" class="header-user__avatar"><el-icon><User /></el-icon></el-avatar>
                <span class="header-user__meta"><strong>{{ currentUsername || '管理员' }}</strong><small>管理员</small></span>
                <el-icon class="header-user__arrow"><ArrowDown /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile"><el-icon><User /></el-icon>账号设置</el-dropdown-item>
                  <el-dropdown-item divided command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
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
          <RouterView v-else v-slot="{ Component }">
            <KeepAlive :max="6">
              <component :is="Component" :key="route.name === 'AdminSettings' ? route.name : route.fullPath" />
            </KeepAlive>
          </RouterView>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Bell,
  Connection,
  DataAnalysis,
  Document,
  Download,
  Expand,
  Fold,
  House,
  Lock,
  Monitor,
  Setting,
  SuccessFilled,
  SwitchButton,
  TrendCharts,
  User
} from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { useViewport } from '../lib/useViewport'

const route = useRoute()
const router = useRouter()
const { isMobile } = useViewport()

const sidebarCollapsed = ref(false)
const componentError = ref('')
const currentUsername = ref('')
const alertBadgeCount = ref(0)

const menuTitles = {
  dashboard: '仪表盘',
  datascreen: '可视化大屏',
  databoard: '数据看板',
  hosts: '主机管理',
  domains: '域名监控',
  alerts: '告警记录',
  'settings-basic': '基本设置',
  'settings-datascreen': '可视化设置',
  'settings-logs': 'Ping 日志',
  'settings-system-logs': '系统日志',
  'settings-backup': '数据备份',
  'settings-profile': '修改密码',
  'mobile-me': '我的'
}

const routeNames = {
  dashboard: 'AdminDashboard',
  datascreen: 'AdminDataScreen',
  databoard: 'AdminDataBoard',
  hosts: 'AdminHosts',
  domains: 'AdminDomains',
  alerts: 'AdminAlerts',
  'settings-basic': 'AdminSettings',
  'settings-datascreen': 'AdminDataScreenSettings',
  'settings-logs': 'AdminPingLogs',
  'settings-system-logs': 'AdminSystemLogs',
  'settings-backup': 'AdminBackups',
  'settings-profile': 'AdminChangePassword',
  'mobile-me': 'AdminMe'
}

const mobileTabs = [
  { key: 'home', label: '首页', icon: House },
  { key: 'hosts', label: '主机', icon: Monitor },
  { key: 'domains', label: '域名', icon: Connection },
  { key: 'alerts', label: '告警', icon: Bell },
  { key: 'me', label: '我的', icon: User }
]

const menuKey = computed(() => route.meta.menuKey || 'dashboard')
const menuTitle = computed(() => route.meta.title || menuTitles[menuKey.value] || '首页')
const isSettingsMenu = computed(() => route.meta.section === 'settings' && menuKey.value !== 'mobile-me')
const isDataScreen = computed(() => menuKey.value === 'datascreen')
const mobileTab = computed(() => {
  if (['dashboard', 'datascreen', 'databoard'].includes(menuKey.value)) return 'home'
  if (menuKey.value === 'hosts') return 'hosts'
  if (menuKey.value === 'domains') return 'domains'
  if (menuKey.value === 'alerts') return 'alerts'
  return 'me'
})
const mobileBackTarget = computed(() => {
  if (!isMobile.value) return ''
  if (isSettingsMenu) return 'mobile-me'
  if (['databoard', 'datascreen'].includes(menuKey.value)) return 'dashboard'
  return ''
})

const openMenu = (key, domainId = null) => {
  const name = routeNames[key] || 'AdminDashboard'
  const location = { name }
  if (key === 'domains' && domainId != null) location.query = { focus: String(domainId) }
  router.push(location)
}

const handleMenuSelect = (key) => {
  if (routeNames[key]) openMenu(key)
}

const selectMobileTab = (key) => {
  if (key === 'home') return openMenu('dashboard')
  if (key === 'hosts') return openMenu('hosts')
  if (key === 'domains') return openMenu('domains')
  if (key === 'alerts') return openMenu('alerts')
  return openMenu('mobile-me')
}

const goMobileBack = () => {
  if (mobileBackTarget.value) openMenu(mobileBackTarget.value)
}

const handleHeaderCommand = (command) => {
  if (command === 'profile') openMenu('settings-profile')
  if (command === 'logout') handleLogout()
}

const handleNavigateEvent = (event) => {
  const targetMenu = event?.detail?.menu
  if (targetMenu && routeNames[targetMenu]) openMenu(targetMenu, event.detail.domainId)
}

const reloadPage = () => window.location.reload()

const validateSession = async () => {
  try { await api.getCurrentUser() } catch {}
}

const loadCurrentUser = async () => {
  try { currentUsername.value = (await api.getCurrentUser())?.username || '' } catch { currentUsername.value = '' }
}

const loadHeaderStats = async () => {
  try { alertBadgeCount.value = (await api.getDashboard())?.recent_alerts || 0 } catch { alertBadgeCount.value = 0 }
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning', center: true })
    localStorage.removeItem('token')
    router.replace('/login')
  } catch {}
}

watch(() => route.fullPath, () => { componentError.value = '' })

onMounted(() => {
  validateSession()
  loadCurrentUser()
  loadHeaderStats()
  window.addEventListener('ping-monitor:navigate', handleNavigateEvent)
})

onBeforeUnmount(() => window.removeEventListener('ping-monitor:navigate', handleNavigateEvent))

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
  background: var(--app-bg);
  color: var(--ink);
}

.admin-shell.is-map-immersive .desktop-aside,
.admin-shell.is-map-immersive .desktop-header,
.admin-shell.is-map-immersive .mobile-topbar,
.admin-shell.is-map-immersive .mobile-tabbar {
  display: none;
}

.admin-shell.is-map-immersive .desktop-main,
.admin-shell.is-map-immersive .mobile-content {
  padding: 0;
}

.admin-shell.is-map-immersive :deep(.ds-frame) {
  border-radius: 0;
}

.desktop-shell {
  width: 100%;
  height: 100%;
  background: var(--app-bg);
}

.desktop-aside {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
  background: #fff;
  border-right: 1px solid var(--line);
  transition: width 0.2s ease;
}

.desktop-brand {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 74px;
  padding: 16px 18px;
  border-bottom: 1px solid #f0f2f5;
}

.desktop-brand__mark {
  display: grid;
  flex: 0 0 38px;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: linear-gradient(145deg, #2563eb, #4f8df7);
  color: #fff;
  font-size: 27px;
  font-weight: 700;
  line-height: 1;
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.2);
}

.desktop-brand__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.desktop-brand__copy strong {
  overflow: hidden;
  color: #1d2939;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.desktop-brand__copy span {
  color: var(--ink-muted);
  font-size: 11px;
  white-space: nowrap;
}

.desktop-nav-caption {
  padding: 19px 20px 8px;
  color: #98a2b3;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.desktop-nav-caption--section {
  padding-top: 22px;
}

.desktop-menu {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  border-right: 0;
  background: #fff;
}

.desktop-menu :deep(.el-menu-item),
.desktop-menu :deep(.el-sub-menu__title) {
  position: relative;
  height: 44px;
  margin: 3px 10px;
  border-radius: 8px;
  color: #667085;
  font-size: 14px;
  line-height: 44px;
  transition: color 0.2s ease, background 0.2s ease;
}

.desktop-menu :deep(.el-menu-item .el-icon),
.desktop-menu :deep(.el-sub-menu__title .el-icon) {
  color: #98a2b3;
  font-size: 17px;
}

.desktop-menu :deep(.el-menu-item:hover),
.desktop-menu :deep(.el-sub-menu__title:hover) {
  background: #f5f8ff;
  color: var(--brand);
}

.desktop-menu :deep(.el-menu-item:hover .el-icon),
.desktop-menu :deep(.el-sub-menu__title:hover .el-icon) {
  color: var(--brand);
}

.desktop-menu :deep(.el-menu-item.is-active) {
  background: #eff6ff;
  color: var(--brand);
  font-weight: 600;
}

.desktop-menu :deep(.el-menu-item.is-active)::before {
  position: absolute;
  top: 9px;
  bottom: 9px;
  left: -10px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--brand);
  content: '';
}

.desktop-menu :deep(.el-menu-item.is-active .el-icon) {
  color: var(--brand);
}

.desktop-menu :deep(.el-sub-menu .el-menu) {
  background: transparent;
}

.desktop-menu :deep(.el-sub-menu .el-menu-item) {
  min-width: 0;
  height: 34px;
  margin: 1px 10px 1px 18px;
  padding-inline: 46px 10px !important;
  line-height: 34px;
  font-size: 13px;
}

.desktop-menu :deep(.el-menu--collapse) {
  width: 76px;
}

.desktop-menu :deep(.el-menu--collapse .el-menu-item),
.desktop-menu :deep(.el-menu--collapse .el-sub-menu__title) {
  margin-inline: 10px;
  padding-inline: 0 !important;
  justify-content: center;
}

.desktop-menu :deep(.el-menu--collapse .el-menu-item.is-active)::before {
  left: -10px;
}

.desktop-menu-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  margin-left: auto;
  padding: 0 6px;
  border-radius: 999px;
  background: #fff0f0;
  color: #dc2626;
  font-size: 11px;
  line-height: 20px;
}

.desktop-aside-footer {
  flex: 0 0 auto;
  padding: 12px 10px 14px;
  border-top: 1px solid #f0f2f5;
}

.desktop-aside-footer__hint {
  padding: 0 10px 9px;
  color: #98a2b3;
  font-size: 11px;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  min-height: 36px;
  padding: 0 11px;
  border: 0;
  border-radius: 8px;
  background: #f8fafc;
  color: #667085;
  font-size: 12px;
  text-align: left;
}

.sidebar-toggle:hover {
  background: #eff6ff;
  color: var(--brand);
}

.desktop-shell.is-sidebar-collapsed .desktop-aside-footer {
  padding-inline: 10px;
}

.desktop-shell.is-sidebar-collapsed .sidebar-toggle {
  justify-content: center;
  padding: 0;
}

.desktop-main-container {
  min-width: 0;
  min-height: 0;
}

.desktop-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  height: 74px;
  padding: 0 28px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}

.desktop-header__left {
  min-width: 0;
}

.desktop-breadcrumb {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #98a2b3;
  font-size: 13px;
}

.desktop-breadcrumb .el-icon {
  color: #b4bdc9;
  font-size: 13px;
}

.desktop-breadcrumb strong {
  color: #1d2939;
  font-weight: 600;
}

.desktop-header__left p {
  margin: 4px 0 0;
  color: #98a2b3;
  font-size: 12px;
}

.desktop-header__right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}

.system-status-tag {
  gap: 4px;
  border-color: #b7e3c0;
  background: #f0fdf4;
  color: #15803d;
}

.header-user {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
}

.header-user__avatar {
  background: #eff6ff;
  color: var(--brand);
}

.header-user__meta {
  display: grid;
  gap: 1px;
  min-width: 74px;
}

.header-user__meta strong {
  overflow: hidden;
  color: #344054;
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-user__meta small {
  color: #98a2b3;
  font-size: 11px;
}

.header-user__arrow {
  color: #98a2b3;
  font-size: 13px;
}

.desktop-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: 20px 24px 24px;
  overflow: hidden;
  background: var(--app-bg);
}

.desktop-iframe {
  width: 100%;
  height: 100%;
  min-height: 0;
  flex: 1;
  border: none;
  border-radius: var(--radius-md);
  background: #02050b;
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
  padding-bottom: env(safe-area-inset-bottom, 0px);
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-content {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  width: 100%;
  height: 0;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: 10px 12px;
  box-sizing: border-box;
}

.mobile-error {
  margin-bottom: 12px;
}

.mobile-iframe {
  width: 100%;
  height: 100%;
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
  overflow: hidden;
  padding-bottom: 4px;
}

.mobile-profile-card {
  border-radius: 14px;
  padding: 0;
  flex: 0 0 auto;
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
  flex: 0 0 auto;
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
  position: relative;
  flex: 0 0 var(--mobile-tabbar-height);
  z-index: 20;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  grid-template-rows: 1fr;
  gap: 0;
  height: var(--mobile-tabbar-height);
  padding: 8px 6px;
  background: rgba(255, 255, 255, 0.98);
  border-top: 1px solid #e5e7eb;
  box-shadow: 0 -6px 24px rgba(15, 23, 42, 0.06);
  box-sizing: border-box;
}

.mobile-tabbar__item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  min-height: 44px;
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

.mobile-tabbar__item > span:last-child {
  white-space: nowrap;
  font-size: clamp(10px, 3vw, 11px);
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
  .mobile-content :deep(.domain-monitor-page),
  .mobile-content :deep(.settings-root),
  .mobile-content :deep(.settings-page),
  .mobile-content :deep(.settings-logs-page),
  .mobile-content :deep(.system-logs-page),
  .mobile-content :deep(.user-profile-page),
  .mobile-content :deep(.datascreen-settings),
  .mobile-content :deep(.database-backup),
  .mobile-content :deep(.database-backup-page),
  .mobile-content :deep(.admin-settings) {
    height: 100%;
    min-height: 0;
    min-width: 0;
    max-width: 100%;
    box-sizing: border-box;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .desktop-aside { width: 164px; }
}

@media (min-width: 769px) and (max-height: 760px) {
  .desktop-header { height: 50px; }
  .desktop-main { padding: 10px; }
  .desktop-brand { padding: 12px 16px; }
  .desktop-menu :deep(.el-menu-item),
  .desktop-menu :deep(.el-sub-menu__title) { height: 37px; line-height: 37px; }
  .desktop-menu :deep(.el-sub-menu .el-menu-item) { height: 32px; line-height: 32px; }
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
    padding: 8px 10px;
  }

  .mobile-tabbar {
    padding: 6px;
  }

  .mobile-tabbar__item {
    gap: 2px;
  }

  .mobile-tabbar__item .el-icon {
    font-size: 17px;
  }

  .mobile-profile-entry { padding-block: 2px; }
  .mobile-menu-card :deep(.el-card__body) { padding: 8px 12px; }
  .mobile-menu-item { padding-block: 5px; min-height: 38px; }
  .mobile-me { gap: 6px; padding-bottom: 0; }
  .mobile-profile-entry { padding: 5px 4px; }
  .mobile-avatar { width: 36px; height: 36px; border-radius: 10px; }
  .mobile-menu-item { min-height: 34px; padding-block: 4px; }
  .mobile-menu-item__left { gap: 6px; font-size: 12px; }
  .mobile-menu-item__icon { font-size: 15px; }
  .mobile-menu-card :deep(.el-card__body) { padding: 2px 8px; }
}

@media (max-width: 768px) and (max-height: 430px) {
  .mobile-me { gap: 4px; }
  .mobile-profile-entry { padding-block: 3px; }
  .mobile-avatar { width: 30px; height: 30px; }
  .mobile-profile__name { font-size: 13px; }
  .mobile-profile__desc { display: none; }
  .mobile-menu-card :deep(.el-card__body) { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 2px 6px; column-gap: 8px; }
  .mobile-menu-item { min-width: 0; min-height: 30px; height: 30px; padding: 2px; border-bottom: 1px solid #eef0f4; }
  .mobile-menu-item__left { gap: 4px; min-width: 0; font-size: 11px; }
  .mobile-menu-item__left span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mobile-menu-item__icon { font-size: 13px; }
  .mobile-chevron { font-size: 12px; }
}

@media (max-width: 420px) {
  .mobile-shortcut-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
