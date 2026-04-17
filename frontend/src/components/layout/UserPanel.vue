<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'
import { uploadAvatar, updateUser, setSystemAvatar } from '@/api/users'
import { getSystemAvatarSvg } from '@/utils/avatar'
import SystemAvatars from '@/components/SystemAvatars.vue'
import PasswordChangeModal from './PasswordChangeModal.vue'

interface UserInfo {
  name: string
  phone: string
  role: string
  branch: string
  avatar: string
  systemAvatar: string
}

const props = defineProps<{
  userInfo: UserInfo
  roleLabels: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'logout'): void
}>()

const userStore = useUserStore()

const panelRef = ref<HTMLElement | null>(null)
const avatarInput = ref<HTMLInputElement | null>(null)
const activeSection = ref<'main' | 'password'>('main')

// 头像上传
const selectedFile = ref<File | null>(null)
const previewUrl = ref('')

// 个人信息编辑
const editForm = ref({
  name: ''
})
const editLoading = ref(false)

// 当前有效的 system_avatar（仅在没有自定义头像时）
const effectiveSystemAvatar = computed(() => {
  return props.userInfo.avatar ? null : props.userInfo.systemAvatar
})

function adjustPanelPosition() {
  if (!panelRef.value) return
  const rect = panelRef.value.getBoundingClientRect()
  const viewportHeight = window.innerHeight
  if (rect.bottom > viewportHeight) {
    panelRef.value.style.bottom = 'auto'
    panelRef.value.style.top = '0'
  }
}

function initPanel() {
  editForm.value.name = props.userInfo.name
  activeSection.value = 'main'
  selectedFile.value = null
  previewUrl.value = ''
  nextTick(adjustPanelPosition)
}

// 头像上传
function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const allowed = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowed.includes(file.type)) {
    ElMessage.error('仅支持 JPG、PNG、WebP 格式')
    input.value = ''
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 2MB')
    input.value = ''
    return
  }

  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  input.value = ''
}

async function confirmAvatarUpload() {
  if (!selectedFile.value) return

  try {
    const userId = userStore.profile?.id
    if (!userId) return
    await uploadAvatar(userId, selectedFile.value)
    await userStore.fetchProfile()
    ElMessage.success('头像已更新')
    selectedFile.value = null
    previewUrl.value = ''
  } catch {
    ElMessage.error('头像上传失败')
  }
}

// 选择系统预设头像
async function handleSelectSystemAvatar(key: string) {
  if (key === effectiveSystemAvatar.value) return
  try {
    const userId = userStore.profile?.id
    if (!userId) return
    await setSystemAvatar(userId, key)
    await userStore.fetchProfile()
    ElMessage.success('头像已更新')
  } catch {
    ElMessage.error('头像设置失败')
  }
}

// 触发自定义上传
function triggerUpload() {
  avatarInput.value?.click()
}

// 保存个人信息
async function saveUserInfo() {
  if (!editForm.value.name.trim()) {
    ElMessage.warning('姓名不能为空')
    return
  }

  editLoading.value = true
  try {
    const userId = userStore.profile?.id
    if (!userId) return
    await updateUser(userId, { name: editForm.value.name })
    await userStore.fetchProfile()
    ElMessage.success('个人信息已更新')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    editLoading.value = false
  }
}

// 修改密码
function showPasswordSection() {
  activeSection.value = 'password'
}

function hidePasswordSection() {
  activeSection.value = 'main'
}

defineExpose({ initPanel, panelRef })
</script>

<template>
  <div class="user-panel-wrapper">
    <div class="user-panel-overlay" @click="$emit('close')"></div>
    <div ref="panelRef" class="user-panel">
      <div class="panel-header">
        <h3 v-if="activeSection === 'main'">个人中心</h3>
        <div v-else class="section-header-inline">
          <button class="back-btn" @click="hidePasswordSection">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </button>
          <span>修改密码</span>
        </div>
        <button class="panel-close" @click="$emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- 主面板 -->
      <div v-if="activeSection === 'main'" class="panel-body">
        <!-- 区域1: 用户信息卡片（纯展示） -->
        <div class="user-card-section">
          <div class="panel-avatar-lg">
            <img v-if="previewUrl || userInfo.avatar" :src="previewUrl || userInfo.avatar" class="avatar-img" />
            <span v-else-if="userInfo.systemAvatar" class="avatar-svg" v-html="getSystemAvatarSvg(userInfo.systemAvatar, 80)" />
            <span v-else class="avatar-initial">{{ userInfo.name.charAt(0) }}</span>
          </div>
          <div class="user-card-info">
            <div class="user-name-lg">{{ userInfo.name }}</div>
            <div class="user-meta">
              <span class="role-tag">{{ roleLabels[userInfo.role] || userInfo.role }}</span>
              <span v-if="userInfo.branch" class="branch-tag">{{ userInfo.branch }}</span>
            </div>
          </div>
        </div>

        <!-- 区域2: 头像管理 -->
        <div class="avatar-manage-section">
          <SystemAvatars
            :model-value="effectiveSystemAvatar"
            @select="handleSelectSystemAvatar"
            @upload="triggerUpload"
          />
          <input ref="avatarInput" type="file" accept="image/jpeg,image/png,image/webp" style="display:none" @change="handleFileSelect" />
          <div class="avatar-upload-actions" v-if="selectedFile">
            <div class="upload-preview">
              <img :src="previewUrl" class="preview-img" />
              <span>预览</span>
            </div>
            <div class="upload-actions">
              <button class="btn-text" @click="confirmAvatarUpload">确认更换</button>
              <button class="btn-text-secondary" @click="selectedFile = null; previewUrl = ''">取消</button>
            </div>
          </div>
        </div>

        <!-- 区域3: 信息编辑 -->
        <div class="info-section">
          <div class="info-item">
            <label>姓名</label>
            <input v-model="editForm.name" type="text" placeholder="请输入姓名" />
          </div>
          <div class="info-item readonly">
            <label>手机号</label>
            <span class="info-value">{{ userInfo.phone }}</span>
          </div>
          <div class="info-item readonly">
            <label>所属分公司</label>
            <span class="info-value">{{ userInfo.branch || '未设置' }}</span>
          </div>
          <button class="btn-save" :disabled="editLoading" @click="saveUserInfo">
            {{ editLoading ? '保存中...' : '保存修改' }}
          </button>
        </div>

        <!-- 区域4: 操作区 -->
        <div class="action-section">
          <button class="action-btn" @click="showPasswordSection">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <span>修改密码</span>
            <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button class="action-btn logout" @click="$emit('logout')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            <span>退出登录</span>
          </button>
        </div>
      </div>

      <!-- 修改密码面板 -->
      <div v-else class="panel-body">
        <PasswordChangeModal @done="hidePasswordSection" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-panel-wrapper {
  /* 无定位 — 让面板的 position: absolute 相对于 .sidebar-footer (position: relative) 定位 */
}

.user-panel-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 1000;
}

.user-panel {
  position: absolute;
  left: calc(100% + 8px);
  bottom: 0;
  z-index: 1001;
  background: white;
  border-radius: 12px;
  width: 380px;
  max-width: calc(100vw - var(--sidebar-width) - 40px);
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.panel-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}

.section-header-inline {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.section-header-inline span {
  font-size: var(--text-base);
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}

.panel-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 0, 0, 0.45);
  transition: all var(--transition-fast);
}

.panel-close:hover {
  background: var(--color-bg-elevated);
  color: rgba(0, 0, 0, 0.75);
}

.panel-close svg {
  width: 18px;
  height: 18px;
}

.panel-body {
  padding: var(--space-4) var(--space-5);
  overflow-y: auto;
}

/* 区域1: 用户信息卡片 */
.user-card-section {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.panel-avatar-lg {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
  flex-shrink: 0;
  overflow: hidden;
}

.panel-avatar-lg .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.panel-avatar-lg .avatar-svg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel-avatar-lg .avatar-initial {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-card-info {
  flex: 1;
  min-width: 0;
}

.user-name-lg {
  font-size: var(--text-lg);
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
}

.user-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.role-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--color-primary-50);
  color: var(--color-primary-600);
  font-weight: 500;
}

.branch-tag {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.5);
}

/* 区域2: 头像管理 */
.avatar-manage-section {
  padding-bottom: var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.avatar-upload-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-elevated);
  border-radius: 8px;
}

.upload-preview {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.preview-img {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
}

.upload-preview span {
  font-size: var(--text-xs);
  color: rgba(0, 0, 0, 0.5);
}

.upload-actions {
  display: flex;
  gap: var(--space-2);
  margin-left: auto;
}

.btn-text {
  padding: var(--space-1) var(--space-3);
  border: none;
  background: var(--color-primary-50);
  color: var(--color-primary-600);
  border-radius: 4px;
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-text:hover {
  background: var(--color-primary-100);
}

.btn-text-secondary {
  padding: var(--space-1) var(--space-3);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: 4px;
  font-size: var(--text-xs);
  cursor: pointer;
}

/* 区域3: 信息编辑 */
.info-section {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.info-item {
  display: flex;
  align-items: center;
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border-light);
}

.info-item:last-of-type {
  border-bottom: none;
}

.info-item label {
  width: 80px;
  font-size: var(--text-sm);
  color: rgba(0, 0, 0, 0.5);
  flex-shrink: 0;
}

.info-item input {
  flex: 1;
  height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: var(--text-sm);
  background: var(--color-bg-elevated);
  color: rgba(0, 0, 0, 0.85);
  outline: none;
  transition: border-color var(--transition-fast);
}

.info-item input:focus {
  border-color: var(--color-primary-500);
}

.info-item.readonly .info-value {
  font-size: var(--text-sm);
  color: rgba(0, 0, 0, 0.75);
}

.btn-save {
  width: 100%;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: var(--color-primary-500);
  color: white;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
  margin-top: var(--space-3);
}

.btn-save:hover:not(:disabled) {
  background: var(--color-primary-600);
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 区域4: 操作按钮 */
.action-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all var(--transition-fast);
  width: 100%;
}

.action-btn:hover {
  background: var(--color-bg-elevated);
  border-color: var(--color-primary-200);
}

.action-btn svg {
  width: 18px;
  height: 18px;
  color: rgba(0, 0, 0, 0.5);
}

.action-btn span {
  flex: 1;
  text-align: left;
  font-size: var(--text-sm);
  color: rgba(0, 0, 0, 0.75);
}

.action-btn .arrow-icon {
  width: 16px;
  height: 16px;
  color: rgba(0, 0, 0, 0.3);
}

.action-btn.logout {
  color: var(--color-danger);
}

.action-btn.logout svg,
.action-btn.logout span {
  color: var(--color-danger);
}

.action-btn.logout:hover {
  background: var(--color-danger-bg);
  border-color: var(--color-danger-bg);
}

/* 返回按钮 */
.back-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: var(--color-bg-elevated);
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 0, 0, 0.5);
  transition: all var(--transition-fast);
}

.back-btn:hover {
  background: var(--color-border);
  color: rgba(0, 0, 0, 0.75);
}

.back-btn svg {
  width: 16px;
  height: 16px;
}
</style>
