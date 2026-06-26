<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { useNotificationStore } from '@/store/notification'
import { updatePassword } from '@/api/auth'
import { TOKEN_KEY, handleApiError } from '@/utils/request'
import { ElMessageBox, ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

const userName = computed(() => userStore.profile?.name || '用户')
const userPhone = computed(() => userStore.profile?.phone || '')
const userRole = computed(() => userStore.profile?.role || '')

const roleLabels: Record<string, string> = {
  admin: '超级管理员',
  manager: '行政经理',
  supervisor: '行政主管',
  leader: '行政组长',
  staff: '行政专员',
}

const menuItems = [
  { key: 'my-assets', label: '我的资产', icon: 'box', path: '/mobile/my-assets' },
  { key: 'my-transfers', label: '我的申请', icon: 'transfer', path: '/mobile/my-transfers' },
  { key: 'notifications', label: '消息通知', icon: 'bell', badge: true, path: '/mobile/notifications' },
  { key: 'settings', label: '系统设置', icon: 'settings', path: '/mobile/settings' },
  { key: 'help', label: '帮助与反馈', icon: 'help', path: '/mobile/help' },
  { key: 'about', label: '关于我们', icon: 'info', path: '/mobile/about' },
]

// 修改密码
const passwordDialogVisible = ref(false)
const passwordLoading = ref(false)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

function openPasswordDialog() {
  passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  passwordDialogVisible.value = true
}

function validatePasswordForm(): string | null {
  const { oldPassword, newPassword, confirmPassword } = passwordForm.value
  if (!oldPassword || !newPassword || !confirmPassword) {
    return '请填写所有密码字段'
  }
  if (newPassword.length < 6) {
    return '新密码长度不能少于6位'
  }
  if (newPassword !== confirmPassword) {
    return '两次输入的新密码不一致'
  }
  if (oldPassword === newPassword) {
    return '新密码不能与旧密码相同'
  }
  return null
}

async function handleChangePassword() {
  const error = validatePasswordForm()
  if (error) {
    ElMessage.warning(error)
    return
  }
  passwordLoading.value = true
  try {
    const { data } = await updatePassword({
      oldPassword: passwordForm.value.oldPassword,
      newPassword: passwordForm.value.newPassword,
    })
    if (data?.token) {
      localStorage.setItem(TOKEN_KEY, data.token)
      userStore.token = data.token
    }
    ElMessage.success(data?.detail || '密码修改成功')
    passwordDialogVisible.value = false
  } catch (e) {
    ElMessage.error(handleApiError(e))
  } finally {
    passwordLoading.value = false
  }
}

function navigateTo(path: string) {
  router.push(path)
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await userStore.logout()
    router.replace('/login')
    ElMessage.success('已退出登录')
  } catch (e) {
    // 用户取消
  }
}

// 获取未读通知数量
onMounted(() => {
  notificationStore.fetchUnreadCount()
})

function getIcon(name: string): string {
  const icons: Record<string, string> = {
    box: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0-1 1.73v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>`,
    transfer: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/></svg>`,
    bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/></svg>`,
    settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-.33-1.82l.06-.06a2 2 0 1 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33z"/></svg>`,
    help: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01"/></svg>`,
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
  }
  return icons[name] || icons.info
}
</script>

<template>
  <div class="profile-page">
    <!-- 用户卡片 -->
    <div class="user-card">
      <div class="user-avatar">{{ userName.charAt(0) }}</div>
      <div class="user-info">
        <div class="user-name">{{ userName }}</div>
        <div class="user-phone">{{ userPhone }}</div>
        <div class="user-role">{{ roleLabels[userRole] || userRole }}</div>
      </div>
      <button class="edit-btn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
      </button>
    </div>

    <!-- 菜单列表 -->
    <div class="menu-section">
      <button
        v-for="item in menuItems"
        :key="item.key"
        class="menu-item"
        @click="navigateTo(item.path)"
      >
        <span class="menu-icon" v-html="getIcon(item.icon)" />
        <span class="menu-label">{{ item.label }}</span>
        <span v-if="item.badge && notificationStore.unreadCount > 0" class="menu-badge">{{ notificationStore.unreadCount }}</span>
        <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </button>
    </div>

    <!-- 修改密码 -->
    <button class="change-password-btn" @click="openPasswordDialog">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
      </svg>
      <span>修改密码</span>
    </button>

    <!-- 退出登录 -->
    <button class="logout-btn" @click="handleLogout">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
        <polyline points="16 17 21 12 16 7"/>
        <line x1="21" y1="12" x2="9" y2="12"/>
      </svg>
      <span>退出登录</span>
    </button>

    <!-- 修改密码对话框 -->
    <div v-if="passwordDialogVisible" class="dialog-overlay" @click.self="passwordDialogVisible = false">
      <div class="dialog-box">
        <div class="dialog-header">
          <span class="dialog-title">修改密码</span>
          <button class="dialog-close" @click="passwordDialogVisible = false">&times;</button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>旧密码</label>
            <input
              v-model="passwordForm.oldPassword"
              type="password"
              placeholder="请输入旧密码"
              autocomplete="current-password"
            />
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input
              v-model="passwordForm.newPassword"
              type="password"
              placeholder="请输入新密码（至少6位）"
              autocomplete="new-password"
            />
          </div>
          <div class="form-group">
            <label>确认密码</label>
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              autocomplete="new-password"
            />
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="passwordDialogVisible = false">取消</button>
          <button class="btn-confirm" :disabled="passwordLoading" @click="handleChangePassword">
            {{ passwordLoading ? '提交中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 版本信息 -->
    <div class="version-info">
      <p>磐盘资产管理系统 v1.0.0</p>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  padding: var(--space-4);
}

.user-card {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-600));
  border-radius: 16px;
  padding: var(--space-5);
  margin-bottom: var(--space-6);
  color: white;
}

.user-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
}

.user-info {
  flex: 1;
}

.user-name {
  font-size: 20px;
  font-weight: 600;
}

.user-phone {
  font-size: 14px;
  opacity: 0.9;
  margin-top: 4px;
}

.user-role {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 4px;
}

.edit-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.edit-btn svg {
  width: 18px;
  height: 18px;
}

.menu-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: var(--space-4);
}

.menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: none;
  border: none;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-item:active {
  background: var(--color-bg-elevated);
}

.menu-icon {
  width: 22px;
  height: 22px;
  color: var(--color-text-secondary);
}

.menu-icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.menu-label {
  flex: 1;
  font-size: 15px;
  color: var(--color-text-primary);
  text-align: left;
}

.menu-badge {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  background: var(--color-danger);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.arrow-icon {
  width: 18px;
  height: 18px;
  color: var(--color-text-tertiary);
}

.logout-btn {
  width: 100%;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  font-size: 15px;
  color: var(--color-danger);
  cursor: pointer;
}

.logout-btn svg {
  width: 18px;
  height: 18px;
}

.change-password-btn {
  width: 100%;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  font-size: 15px;
  color: var(--color-primary-500);
  cursor: pointer;
  margin-bottom: var(--space-4);
}

.change-password-btn svg {
  width: 18px;
  height: 18px;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  padding: var(--space-4);
}

.dialog-box {
  width: 100%;
  max-width: 400px;
  background: var(--color-bg-card);
  border-radius: 12px;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.dialog-close {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  font-size: 20px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.dialog-close:active {
  background: var(--color-bg-elevated);
}

.dialog-body {
  padding: var(--space-4);
}

.form-group {
  margin-bottom: var(--space-4);
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--color-bg-elevated);
  color: var(--color-text-primary);
  outline: none;
  box-sizing: border-box;
}

.form-group input::placeholder {
  color: var(--color-text-tertiary);
}

.form-group input:focus {
  border-color: var(--color-primary-500);
}

.dialog-footer {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.btn-cancel,
.btn-confirm {
  flex: 1;
  height: 40px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
}

.btn-cancel {
  background: var(--color-bg-elevated);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.btn-confirm {
  background: var(--color-primary-500);
  color: white;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.version-info {
  text-align: center;
  margin-top: var(--space-6);
  color: var(--color-text-tertiary);
  font-size: 12px;
}
</style>
