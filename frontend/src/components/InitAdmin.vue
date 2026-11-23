<template>
  <div class="init-container">
    <el-card class="init-card">
      <template #header>
        <div class="card-header">
          <h2>初始化管理员</h2>
          <p>欢迎使用Ping监控系统，请设置管理员账户</p>
        </div>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="username">
          <el-input 
            v-model="form.username" 
            placeholder="用户名（至少3个字符）"
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
            placeholder="密码（至少5个字符）"
            show-password
            size="large"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input 
            v-model="form.confirmPassword" 
            type="password" 
            placeholder="确认密码"
            show-password
            size="large"
            @keyup.enter="handleInit"
          >
            <template #prefix>
              <el-icon><Check /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleInit" :loading="loading" size="large" style="width: 100%; margin-top: 10px;">
            创建管理员
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const route = useRoute()
const isSafeRedirect = (redirect) => typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')
const redirectTarget = () => {
  const redirect = typeof route.query?.redirect === 'string' ? route.query.redirect : ''
  return isSafeRedirect(redirect) ? redirect : '/'
}
const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少需要3个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 5, message: '密码至少需要5个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleInit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const result = await api.initAdmin({
        username: form.username,
        password: form.password
      })
      
      localStorage.setItem('token', result.access_token)
      ElMessage.success('管理员创建成功，正在跳转...')
      // 初始化后回到原始目标地址；没有深链接时回公开入口
      setTimeout(() => {
        router.replace(redirectTarget())
      }, 500)
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '创建失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.init-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 32px 20px;
  overflow: hidden;
  background: #f5f8ff;
}

.init-container::before {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 16% 14%, rgba(37, 99, 235, 0.12), transparent 34%), radial-gradient(circle at 86% 90%, rgba(96, 165, 250, 0.12), transparent 30%);
  content: '';
}

.init-card {
  position: relative;
  z-index: 1;
  width: min(460px, 100%);
  border: 1px solid #e6eaf0;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(30, 64, 175, 0.1);
}

.init-card :deep(.el-card__header) { padding: 28px 32px 0; border-bottom: 0; }
.init-card :deep(.el-card__body) { padding: 20px 32px 30px; }
.card-header { text-align: center; }
.card-header h2 { margin: 0 0 10px; color: #1d2939; font-size: 24px; }
.card-header p { margin: 0; color: #98a2b3; font-size: 13px; }
.init-card :deep(.el-input__wrapper) { min-height: 44px; }
.init-card :deep(.el-button) { height: 44px; border-radius: 8px; }

@media (max-width: 520px) {
  .init-container { padding: 18px 14px; }
  .init-card :deep(.el-card__header) { padding-inline: 22px; }
  .init-card :deep(.el-card__body) { padding: 18px 22px 24px; }
}
</style>
