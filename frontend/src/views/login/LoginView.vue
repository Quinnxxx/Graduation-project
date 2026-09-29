<script setup lang="ts">
/**
 * 登录 / 注册页
 *
 * 居中卡片，使用 Tabs 切换“登录”与“注册”：
 * - 登录：用户名 + 密码，成功后回跳 redirect 或进入工作台；
 * - 注册：完整字段校验，成功后切回登录 Tab 并预填用户名。
 * 业务错误由 request 拦截器统一 message 提示，页面 catch 仅负责结束 loading。
 */

import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import type { FormInstance } from 'ant-design-vue'
import type { Rule } from 'ant-design-vue/es/form'

import { registerApi } from '@/api/auth'
import { useUserStore } from '@/store/modules/user'
import type { LoginParams, RegisterParams } from '@/types/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

/** 当前激活的 Tab：login 登录 / register 注册 */
const activeTab = ref<'login' | 'register'>('login')

/** 登录表单引用 */
const loginFormRef = ref<FormInstance>()
/** 注册表单引用 */
const registerFormRef = ref<FormInstance>()

/** 登录提交中标志 */
const loginLoading = ref(false)
/** 注册提交中标志 */
const registerLoading = ref(false)

/** 登录表单数据 */
const loginForm = reactive<LoginParams>({
  username: '',
  password: '',
})

/** 注册表单数据 */
const registerForm = reactive<RegisterParams>({
  username: '',
  password: '',
  confirmPassword: '',
  nickname: '',
  email: '',
  phone: '',
})

/** 登录表单校验规则 */
const loginRules: Record<string, Rule[]> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

/** 用户名规则：4-32 位字母、数字、下划线 */
const usernamePattern = /^[a-zA-Z0-9_]{4,32}$/
/** 邮箱规则 */
const emailPattern = /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/
/** 手机号规则 */
const phonePattern = /^1[3-9]\d{9}$/

/** 注册表单校验规则 */
const registerRules: Record<string, Rule[]> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    {
      pattern: usernamePattern,
      message: '用户名为 4-32 位字母、数字或下划线',
      trigger: 'blur',
    },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度需在 6-32 位之间', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value: string) => {
        if (value !== registerForm.password) {
          return Promise.reject(new Error('两次输入的密码不一致'))
        }
        return Promise.resolve()
      },
      trigger: 'blur',
    },
  ],
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { pattern: emailPattern, message: '请输入正确的邮箱地址', trigger: 'blur' },
  ],
  phone: [
    {
      validator: (_rule, value: string) => {
        // 手机号选填，为空时不校验
        if (!value) {
          return Promise.resolve()
        }
        if (!phonePattern.test(value)) {
          return Promise.reject(new Error('请输入正确的手机号'))
        }
        return Promise.resolve()
      },
      trigger: 'blur',
    },
  ],
}

/**
 * 提交登录
 */
async function handleLogin(): Promise<void> {
  try {
    await loginFormRef.value?.validate()
  } catch {
    return
  }

  loginLoading.value = true
  try {
    await userStore.login({ ...loginForm })
    message.success('登录成功')
    // 回跳原目标页面，无则进入工作台
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch {
    // 错误已由请求层统一提示，此处仅结束 loading
  } finally {
    loginLoading.value = false
  }
}

/**
 * 提交注册
 */
async function handleRegister(): Promise<void> {
  try {
    await registerFormRef.value?.validate()
  } catch {
    return
  }

  registerLoading.value = true
  try {
    await registerApi({ ...registerForm })
    message.success('注册成功，请登录')
    // 预填用户名到登录表单，切回登录 Tab
    loginForm.username = registerForm.username
    registerFormRef.value?.resetFields()
    activeTab.value = 'login'
  } catch {
    // 错误已由请求层统一提示，此处仅结束 loading
  } finally {
    registerLoading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <a-card class="login-card">
      <div class="login-title">校招求职智能辅助平台</div>
      <div class="login-subtitle">融合多 Agent 协作与三级记忆机制</div>

      <a-tabs v-model:active-key="activeTab" centered>
        <!-- 登录 -->
        <a-tab-pane key="login" tab="登录">
          <a-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            layout="vertical"
            @finish="handleLogin"
          >
            <a-form-item label="用户名" name="username">
              <a-input
                v-model:value="loginForm.username"
                placeholder="请输入用户名"
                allow-clear
              />
            </a-form-item>

            <a-form-item label="密码" name="password">
              <a-input-password
                v-model:value="loginForm.password"
                placeholder="请输入密码"
                allow-clear
                @press-enter="handleLogin"
              />
            </a-form-item>

            <a-button
              type="primary"
              html-type="submit"
              block
              :loading="loginLoading"
              class="login-button"
            >
              登 录
            </a-button>
          </a-form>
        </a-tab-pane>

        <!-- 注册 -->
        <a-tab-pane key="register" tab="注册">
          <a-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            layout="vertical"
            @finish="handleRegister"
          >
            <a-form-item label="用户名" name="username">
              <a-input
                v-model:value="registerForm.username"
                placeholder="4-32 位字母、数字或下划线"
                allow-clear
              />
            </a-form-item>

            <a-form-item label="密码" name="password">
              <a-input-password
                v-model:value="registerForm.password"
                placeholder="6-32 位密码"
                allow-clear
              />
            </a-form-item>

            <a-form-item label="确认密码" name="confirmPassword">
              <a-input-password
                v-model:value="registerForm.confirmPassword"
                placeholder="请再次输入密码"
                allow-clear
              />
            </a-form-item>

            <a-form-item label="昵称" name="nickname">
              <a-input
                v-model:value="registerForm.nickname"
                placeholder="请输入昵称"
                allow-clear
              />
            </a-form-item>

            <a-form-item label="邮箱" name="email">
              <a-input
                v-model:value="registerForm.email"
                placeholder="请输入邮箱"
                allow-clear
              />
            </a-form-item>

            <a-form-item label="手机号（选填）" name="phone">
              <a-input
                v-model:value="registerForm.phone"
                placeholder="请输入手机号"
                allow-clear
              />
            </a-form-item>

            <a-button
              type="primary"
              html-type="submit"
              block
              :loading="registerLoading"
              class="login-button"
            >
              注 册
            </a-button>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px 0;
  background: linear-gradient(135deg, #1677ff 0%, #69b1ff 100%);
}

.login-card {
  width: 420px;
  max-width: calc(100vw - 32px);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.login-title {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a1a;
  text-align: center;
}

.login-subtitle {
  margin: 8px 0 16px;
  font-size: 13px;
  color: #8c8c8c;
  text-align: center;
}

.login-button {
  margin-top: 8px;
}
</style>
