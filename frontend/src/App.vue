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
          <el-menu-item index="dashboard">
            <el-icon><Monitor /></el-icon>
            <span>仪表盘</span>
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
            <el-menu-item index="settings-logs">
              <span>Ping日志</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-header style="background-color: #409eff; color: #fff; display: flex; align-items: center">
          <h2 style="margin: 0">{{ menuTitle }}</h2>
        </el-header>
        <el-main style="overflow-y: auto">
          <Dashboard v-if="activeMenu === 'dashboard'" />
          <HostManage v-else-if="activeMenu === 'hosts'" />
          <AlertList v-else-if="activeMenu === 'alerts'" />
          <Settings v-else-if="activeMenu.startsWith('settings')" :active-tab="activeMenu" />
        </el-main>
      </el-container>
    </el-container>
</template>

<script setup>
import { ref } from 'vue'
import Dashboard from './components/Dashboard.vue'
import HostManage from './components/HostManage.vue'
import AlertList from './components/AlertList.vue'
import Settings from './components/Settings.vue'

const activeMenu = ref('dashboard')

const menuTitles = {
  dashboard: '监控仪表盘',
  hosts: '主机管理',
  alerts: '告警记录',
  'settings-basic': '系统设置 - 基本设置',
  'settings-logs': '系统设置 - Ping日志'
}

const menuTitle = ref(menuTitles.dashboard)

const handleMenuSelect = (key) => {
  activeMenu.value = key
  menuTitle.value = menuTitles[key]
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  overflow: hidden;
}

#app {
  width: 100%;
  height: 100vh;
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.el-menu-vertical {
  border-right: none;
}

.el-main {
  background-color: #f5f5f5;
  padding: 20px;
}

.el-header {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
