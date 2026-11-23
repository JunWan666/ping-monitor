<template>
  <div class="mobile-me-page">
    <el-card shadow="never" class="mobile-profile-card">
      <button type="button" class="mobile-profile-entry" @click="router.push({ name: 'AdminChangePassword' })">
        <div class="mobile-profile">
          <div class="mobile-avatar"><el-icon :size="28"><User /></el-icon></div>
          <div class="mobile-profile__meta">
            <div class="mobile-profile__name">{{ username || '管理员' }}</div>
            <div class="mobile-profile__desc">系统管理员</div>
          </div>
        </div>
        <el-icon class="mobile-chevron"><ArrowRight /></el-icon>
      </button>
    </el-card>
    <el-card shadow="never" class="mobile-menu-card">
      <button v-for="item in actions" :key="item.name" type="button" class="mobile-menu-item" @click="router.push({ name: item.name })">
        <div class="mobile-menu-item__left"><el-icon class="mobile-menu-item__icon"><component :is="item.icon" /></el-icon><span>{{ item.label }}</span></div>
        <el-icon class="mobile-chevron"><ArrowRight /></el-icon>
      </button>
      <button type="button" class="mobile-menu-item is-danger" @click="logout">
        <div class="mobile-menu-item__left"><el-icon class="mobile-menu-item__icon"><SwitchButton /></el-icon><span>退出登录</span></div>
        <el-icon class="mobile-chevron"><ArrowRight /></el-icon>
      </button>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { ArrowRight, DataAnalysis, Document, Download, Lock, Monitor, Setting, SwitchButton, User } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const username = ref('')
const actions = [
  { name: 'AdminSettings', label: '基础设置', icon: Setting },
  { name: 'AdminDataScreenSettings', label: '大屏设置', icon: DataAnalysis },
  { name: 'AdminPingLogs', label: 'Ping 日志', icon: Document },
  { name: 'AdminSystemLogs', label: '系统日志', icon: Monitor },
  { name: 'AdminBackups', label: '数据备份', icon: Download },
  { name: 'AdminChangePassword', label: '修改密码', icon: Lock }
]

const logout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning', center: true })
    localStorage.removeItem('token')
    router.replace('/login')
  } catch {}
}

onMounted(async () => {
  try { username.value = (await api.getCurrentUser())?.username || '' } catch {}
})
</script>

<style scoped>
.mobile-me-page { display: flex; flex-direction: column; gap: 12px; min-height: 100%; }
.mobile-profile-card, .mobile-menu-card { border-radius: 14px; overflow: hidden; }
.mobile-profile-entry, .mobile-menu-item { display: flex; align-items: center; justify-content: space-between; width: 100%; border: 0; background: transparent; color: #111827; }
.mobile-profile-entry { padding: 12px 6px 12px 4px; }
.mobile-menu-item { min-height: 50px; padding: 12px 4px 12px 0; border-bottom: 1px solid #eef0f4; }
.mobile-menu-item:last-child { border-bottom: 0; }
.mobile-profile { display: flex; align-items: center; gap: 12px; }
.mobile-avatar { display: flex; align-items: center; justify-content: center; width: 48px; height: 48px; border-radius: 14px; background: #eef4ff; color: #3b82f6; }
.mobile-profile__name { color: #111827; font-size: 16px; font-weight: 700; }
.mobile-profile__desc { margin-top: 2px; color: #6b7280; font-size: 12px; }
.mobile-menu-item__left { display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 500; }
.mobile-menu-item__icon { color: #3b82f6; font-size: 18px; }
.mobile-menu-item.is-danger { color: #f56c6c; }
.mobile-menu-item.is-danger .mobile-menu-item__icon { color: #f56c6c; }
.mobile-chevron { color: #c0c4cc; font-size: 16px; }
</style>
