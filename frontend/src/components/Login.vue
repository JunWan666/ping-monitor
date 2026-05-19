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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
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
      router.push('/init')
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
      router.push('/admin')
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
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
}

.login-import-alert {
  margin-bottom: 16px;
  white-space: pre-line;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  color: #409eff;
}
</style>
