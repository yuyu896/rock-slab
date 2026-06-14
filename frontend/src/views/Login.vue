<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/store/user'
import { handleApiError } from '@/utils/request'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const phone = ref('')
const password = ref('')
const loading = ref(false)
const showPassword = ref(false)
const errorMessage = ref('')

// Check if redirected due to token expiry
if (sessionStorage.getItem('token_expired')) {
  sessionStorage.removeItem('token_expired')
  errorMessage.value = '登录已过期，请重新登录'
}

// 清除输入时清除错误
function clearError() {
  errorMessage.value = ''
}

async function handleLogin() {
  // 清除之前的错误
  errorMessage.value = ''

  // 表单验证
  if (!phone.value && !password.value) {
    errorMessage.value = '请输入手机号和密码'
    return
  }
  if (!phone.value) {
    errorMessage.value = '请输入手机号'
    return
  }
  if (!/^\d{11}$/.test(phone.value)) {
    errorMessage.value = '手机号必须为11位数字'
    return
  }
  if (!password.value) {
    errorMessage.value = '请输入密码'
    return
  }

  loading.value = true
  try {
    await userStore.login(phone.value, password.value)
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (error) {
    // 显示登录失败的错误信息
    errorMessage.value = handleApiError(error) || '账号或密码错误，请重新输入'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          </svg>
        </div>
        <h1 class="login-title">磐盘</h1>
        <p class="login-subtitle">行政资产盘点</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <!-- 错误提示 -->
        <Transition name="error-fade">
          <div v-if="errorMessage" class="error-message">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{{ errorMessage }}</span>
          </div>
        </Transition>

        <div class="form-group">
          <label class="form-label" for="login-phone">手机号</label>
          <input
            id="login-phone"
            v-model="phone"
            type="tel"
            class="form-input"
            :class="{ 'form-input-error': errorMessage && !phone }"
            placeholder="请输入手机号"
            maxlength="11"
            autocomplete="tel"
            aria-required="true"
            @input="clearError"
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="login-password">密码</label>
          <div class="input-wrapper">
            <input
              id="login-password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              class="form-input"
              :class="{ 'form-input-error': errorMessage && !password }"
              placeholder="请输入密码"
              autocomplete="current-password"
              aria-required="true"
              @input="clearError"
            />
            <button type="button" class="toggle-password" @click="showPassword = !showPassword">
              <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
        </div>

        <button type="submit" class="login-btn" :disabled="loading">
          <span v-if="loading" class="spinner" />
          <span v-else>登 录</span>
        </button>
      </form>

    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-50) 0%, var(--color-bg-page) 50%, oklch(0.96 0.04 145) 100%);
  padding: var(--space-4);
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: var(--color-bg-card);
  border-radius: 16px;
  padding: var(--space-10) var(--space-8);
  box-shadow: 0 8px 32px oklch(0.20 0.02 145 / 0.08);
  border: 1px solid var(--color-border-light);
}

.login-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.login-logo {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--space-4);
}

.login-logo svg {
  width: 28px;
  height: 28px;
  color: white;
}

.login-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1) 0;
}

.login-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

/* 错误提示样式 */
.error-message {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: oklch(0.95 0.08 25);
  border: 1px solid oklch(0.85 0.12 25);
  border-radius: 10px;
  color: oklch(0.55 0.18 25);
  font-size: var(--text-sm);
  margin-bottom: var(--space-1);
}

.error-message svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.error-fade-enter-active,
.error-fade-leave-active {
  transition: all 0.3s ease;
}

.error-fade-enter-from,
.error-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.form-input-error {
  border-color: oklch(0.65 0.18 25) !important;
  background: oklch(0.98 0.04 25) !important;
}

.form-input-error:focus {
  box-shadow: 0 0 0 3px oklch(0.65 0.18 25 / 0.15) !important;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
}

.form-input {
  height: 44px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  background: var(--color-bg-page);
  transition: all var(--transition-fast);
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.form-input::placeholder {
  color: var(--color-text-tertiary);
}

.form-input:focus {
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 3px oklch(0.68 0.16 145 / 0.12);
}

.input-wrapper {
  position: relative;
}

.input-wrapper .form-input {
  padding-right: 44px;
}

.toggle-password {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-tertiary);
  border-radius: 8px;
  transition: color var(--transition-fast);
}

.toggle-password:hover {
  color: var(--color-text-secondary);
}

.toggle-password svg {
  width: 18px;
  height: 18px;
}

.login-btn {
  height: 44px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  color: white;
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: var(--space-2);
}

.login-btn:hover:not(:disabled) {
  box-shadow: 0 4px 16px oklch(0.58 0.18 145 / 0.3);
  transform: translateY(-1px);
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid oklch(1 0 0 / 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-footer {
  text-align: center;
  margin-top: var(--space-6);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
</style>
