<template>
  <div class="login-container">
    <el-card class="login-card">
      <el-alert
        v-if="importSummary"
        :title="importSummary"
        type="success"
        show-icon
        :closable="true"
        class="login-import-alert"
      />
      <template #header>
        <div class="card-header">
          <h2>Ping监控系统</h2>
          <p style="color: #909399; font-size: 14px; margin-top: 8px;">请登录您的账户</p>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="username">
          <el-input 
            v-model="form.username" 
            placeholder="请输入用户名"
            size="large"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="请输入密码"
            show-password
            size="large"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" size="large" style="width: 100%; margin-top: 10px;">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const route = useRoute()
const isSafeRedirect = (redirect) => typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')
const redirectTarget = () => {
  const redirect = typeof route.query?.redirect === 'string' ? route.query.redirect : ''
  return isSafeRedirect(redirect) ? redirect : '/admin/dashboard'
}
const formRef = ref(null)
const loading = ref(false)
const importSummary = ref('')

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// 检查是否需要初始化
const checkInit = async () => {
  try {
    const result = await api.checkAdminExists()
    if (!result.has_admin) {
      // 没有管理员，跳转到初始化页面
      router.push({ path: '/init', query: route.query.redirect ? { redirect: route.query.redirect } : undefined })
    }
  } catch (error) {
    console.error('检查初始化状态失败:', error)
  }
}

const handleLogin = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const result = await api.login({
        username: form.username,
        password: form.password
      })
      
      localStorage.setItem('token', result.access_token)
      ElMessage.success('登录成功')
      router.push(redirectTarget())
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '登录失败')
    } finally {
      loading.value = false
    }
  })
}

onMounted(() => {
  importSummary.value = sessionStorage.getItem('ping-monitor-import-summary') || ''
  if (importSummary.value) {
    sessionStorage.removeItem('ping-monitor-import-summary')
  }
  checkInit()
})
</script>

<style scoped>
.login-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 100vh;
  padding: 32px 20px;
  overflow: hidden;
  background: #f5f8ff;
}

.login-container::before,
.login-container::after {
  position: absolute;
  width: 420px;
  height: 420px;
  border-radius: 50%;
  background: rgba(37, 99, 235, 0.1);
  filter: blur(2px);
  content: '';
}

.login-container::before { top: -210px; left: -110px; }
.login-container::after { right: -130px; bottom: -240px; background: rgba(96, 165, 250, 0.12); }

.login-card {
  position: relative;
  z-index: 1;
  width: min(432px, 100%);
  overflow: hidden;
  border: 1px solid rgba(216, 222, 232, 0.9);
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(30, 64, 175, 0.1);
}

.login-card :deep(.el-card__header) { padding: 28px 32px 0; border-bottom: 0; }
.login-card :deep(.el-card__body) { padding: 22px 32px 30px; }

.login-import-alert { margin-bottom: 16px; white-space: pre-line; }
.card-header { text-align: center; }
.card-header h2 { margin: 0; color: #1d2939; font-size: 24px; letter-spacing: -0.03em; }
.card-header p { margin-top: 8px; color: #98a2b3 !important; font-size: 13px !important; }
.login-card :deep(.el-input__wrapper) { min-height: 44px; }
.login-card :deep(.el-button) { height: 44px; border-radius: 8px; font-size: 15px; }

@media (max-width: 520px) {
  .login-container { padding: 18px 14px; }
  .login-card :deep(.el-card__header) { padding-inline: 22px; }
  .login-card :deep(.el-card__body) { padding: 18px 22px 24px; }
}
</style>
