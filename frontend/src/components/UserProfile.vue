<template>
  <div class="user-profile-page">
    <el-card shadow="hover" class="profile-card">
      <template #header>
        <div class="profile-card__header">
          <span>修改用户信息</span>
          <small>账号与密码</small>
        </div>
      </template>

      <el-form
        :model="form"
        :rules="rules"
        ref="formRef"
        :label-position="isMobile ? 'top' : 'right'"
        :label-width="isMobile ? 'auto' : '120px'"
        class="profile-form"
      >
        <section class="profile-section">
          <div class="profile-section__title">账号信息</div>
          <el-form-item label="当前用户名">
            <el-input v-model="currentUsername" disabled />
          </el-form-item>

          <el-form-item label="新用户名" prop="new_username">
            <el-input v-model="form.new_username" placeholder="至少3个字符，留空则不修改" clearable />
          </el-form-item>
        </section>

        <section class="profile-section">
          <div class="profile-section__title">密码验证</div>
          <el-form-item label="原密码" prop="old_password">
            <el-input v-model="form.old_password" type="password" placeholder="请输入原密码" show-password clearable />
          </el-form-item>
        </section>

        <section class="profile-section">
          <div class="profile-section__title">新密码</div>
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="form.new_password" type="password" placeholder="至少5个字符，留空则不修改" show-password clearable />
          </el-form-item>

          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input v-model="form.confirm_password" type="password" placeholder="请再次输入新密码" show-password clearable />
          </el-form-item>
        </section>

        <el-form-item class="profile-actions">
          <el-button type="primary" @click="submitForm" :loading="submitting">
            <el-icon><Select /></el-icon> 提交修改
          </el-button>
          <el-button @click="resetForm">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>

      <el-alert
        title="温馨提示"
        type="warning"
        :closable="false"
        class="profile-alert"
      >
        <p>1. 修改成功后将自动退出登录，需要使用新信息重新登录</p>
        <p>2. 用户名和密码至少需要修改其中一项</p>
        <p>3. 必须输入原密码才能进行修改</p>
      </el-alert>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '../api'
import { useViewport } from '../lib/useViewport'

const router = useRouter()
const formRef = ref(null)
const submitting = ref(false)
const currentUsername = ref('')
const { isMobile } = useViewport()

const form = reactive({
  old_password: '',
  new_username: '',
  new_password: '',
  confirm_password: ''
})

// 自定义验证规则
const validateConfirmPassword = (rule, value, callback) => {
  if (form.new_password && value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  new_username: [
    { min: 3, message: '用户名至少需要3个字符', trigger: 'blur' }
  ],
  new_password: [
    { min: 5, message: '密码至少需要5个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const loadCurrentUser = async () => {
  try {
    const user = await api.getCurrentUser()
    currentUsername.value = user.username
  } catch (error) {
    ElMessage.error('获取用户信息失败')
  }
}

const submitForm = async () => {
  // 验证是否至少修改了一项
  if (!form.new_username && !form.new_password) {
    ElMessage.warning('请至少修改用户名或密码其中一项')
    return
  }

  // 如果修改了密码，必须确认密码
  if (form.new_password && !form.confirm_password) {
    ElMessage.warning('请确认新密码')
    return
  }

  // 表单验证
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }

  try {
    await ElMessageBox.confirm(
      '修改成功后将自动退出登录，确定要继续吗？',
      '确认修改',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        center: true
      }
    )

    submitting.value = true

    const data = {
      old_password: form.old_password
    }
    if (form.new_username) {
      data.new_username = form.new_username
    }
    if (form.new_password) {
      data.new_password = form.new_password
    }

    await api.updatePassword(data)
    
    ElMessage.success('修改成功，即将跳转到登录页面')
    
    // 清除token
    localStorage.removeItem('token')
    
    // 延迟跳转到登录页
    setTimeout(() => {
      window.location.href = '/login'
    }, 1500)
  } catch (error) {
    if (error !== 'cancel') {
      submitting.value = false
      ElMessage.error(error.response?.data?.detail || '修改失败')
    } else {
      submitting.value = false
    }
  }
}

const resetForm = () => {
  formRef.value.resetFields()
}

onMounted(() => {
  loadCurrentUser()
})
</script>

<style scoped>
.user-profile-page {
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow-x: hidden;
  box-sizing: border-box;
}

.profile-form {
  max-width: 560px;
  min-width: 0;
}

.profile-card__header {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-weight: 700;
}

.profile-card__header small {
  font-size: 12px;
  font-weight: 400;
  color: #909399;
}

.profile-section {
  margin-bottom: 18px;
}

.profile-section__title {
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.profile-alert {
  margin-top: 20px;
}

@media (max-width: 767px) {
  .user-profile-page {
    overflow-y: auto;
    overflow-x: hidden;
    padding-bottom: 4px;
  }

  .user-profile-page :deep(.el-card) {
    border-radius: 14px;
    box-shadow: none;
  }

  .user-profile-page :deep(.el-card__header) {
    padding: 14px 14px 0;
    border-bottom: none;
  }

  .user-profile-page :deep(.el-card__body) {
    padding: 14px;
  }

  .profile-form {
    max-width: 100% !important;
    width: 100%;
  }

  .profile-section {
    margin-bottom: 12px;
    padding: 12px;
    border: 1px solid #edf2f7;
    border-radius: 12px;
    background: #f8fafc;
    min-width: 0;
    box-sizing: border-box;
  }

  .profile-form :deep(.el-form-item) {
    display: block;
    width: 100%;
    min-width: 0;
  }

  .profile-section__title {
    margin-bottom: 10px;
    font-size: 13px;
  }

  .user-profile-page :deep(.el-form-item__label) {
    display: block;
    width: auto !important;
    height: auto;
    line-height: 1.4;
    margin-bottom: 6px;
    padding: 0;
    text-align: left;
  }

  .user-profile-page :deep(.el-form-item__content) {
    margin-left: 0 !important;
    width: 100%;
    min-width: 0;
  }

  .user-profile-page :deep(.el-input),
  .user-profile-page :deep(.el-input__wrapper) {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }

  .profile-actions :deep(.el-form-item__content) {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .profile-actions :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }

  .profile-alert {
    margin-top: 12px;
    overflow-wrap: anywhere;
  }
}
</style>
