<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadAvatar, updateUser, updatePassword, setSystemAvatar } from '@/api/users'
import { getSystemAvatarSvg } from '@/utils/avatar'
import SystemAvatars from '@/components/SystemAvatars.vue'

interface NavItem {
  icon: string
  label: string
  path: string
  badge?: number
  children?: NavItem[]
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapsed = ref(false)
const activeMenu = computed(() => route.path)
const avatarInput = ref<HTMLInputElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const expandedMenu = ref<string | null>(null)

// 用户面板弹窗状态
const showUserPanel = ref(false)
const activeSection = ref<'main' | 'password'>('main')

// 头像上传
const selectedFile = ref<File | null>(null)
const previewUrl = ref('')

// 个人信息编辑
const editForm = ref({
  name: ''
})
const editLoading = ref(false)

// 修改密码
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const passwordLoading = ref(false)

const navItems: NavItem[] = [
  {
    icon: 'dashboard',
    label: '工作台',
    path: '/dashboard'
  },
  {
    icon: 'chart',
    label: '统计报表',
    path: '/reports'
  },
  {
    icon: 'category',
    label: '资产分类',
    path: '/categories'
  },
  {
    icon: 'box',
    label: '资产列表',
    path: '/assets/list'
  },
  {
    icon: 'transfer',
    label: '资产流转',
    path: '/transfers',
    children: [
      { icon: '', label: '采购入库', path: '/assets/purchase' },
      { icon: '', label: '领用出库', path: '/transfers/assign' },
      { icon: '', label: '调拨', path: '/transfers/transfer' },
    ]
  },
  {
    icon: 'scan',
    label: '资产盘点',
    path: '/inventory',
    badge: 3
  },
  {
    icon: 'organization',
    label: '组织架构',
    path: '/organization'
  }
]

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const navigateTo = (path: string) => {
  router.push(path)
}

const isActive = (path: string) => {
  return activeMenu.value === path || activeMenu.value.startsWith(path + '/')
}

const isChildActive = (item: NavItem) => {
  if (!item.children) return false
  return item.children.some(child => activeMenu.value === child.path || activeMenu.value.startsWith(child.path + '/'))
}

const toggleDropdown = (path: string) => {
  expandedMenu.value = expandedMenu.value === path ? null : path
}

const closeDropdown = () => {
  expandedMenu.value = null
}

const userInfo = computed(() => ({
  name: userStore.profile?.name || '用户',
  phone: userStore.profile?.phone || '',
  role: userStore.profile?.role || 'staff',
  branch: userStore.profile?.branch || '',
  avatar: userStore.profile?.avatar || '',
  systemAvatar: userStore.profile?.systemAvatar || ''
}))

const roleLabels: Record<string, string> = {
  admin: '超级管理员',
  manager: '行政经理',
  supervisor: '主管',
  leader: '组长',
  staff: '员工'
}

// 当前有效的 system_avatar（仅在没有自定义头像时）
const effectiveSystemAvatar = computed(() => {
  return userInfo.value.avatar ? null : userInfo.value.systemAvatar
})

// 打开用户面板
function openUserPanel() {
  if (isCollapsed.value) return
  editForm.value.name = userInfo.value.name
  activeSection.value = 'main'
  selectedFile.value = null
  previewUrl.value = ''
  passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  showUserPanel.value = true
  nextTick(adjustPanelPosition)
}

function closeUserPanel() {
  showUserPanel.value = false
}

// 面板定位调整
function adjustPanelPosition() {
  if (!panelRef.value) return
  const rect = panelRef.value.getBoundingClientRect()
  const viewportHeight = window.innerHeight
  if (rect.bottom > viewportHeight) {
    panelRef.value.style.bottom = 'auto'
    panelRef.value.style.top = '0'
  }
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
  passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
}

function hidePasswordSection() {
  activeSection.value = 'main'
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
    await updatePassword({
      oldPassword: passwordForm.value.oldPassword,
      newPassword: passwordForm.value.newPassword
    })
    ElMessage.success('密码修改成功')
    activeSection.value = 'main'
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '密码修改失败')
  } finally {
    passwordLoading.value = false
  }
}

// 退出登录
async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch {
    // 用户取消
  }
}

const getIcon = (name: string) => {
  const icons: Record<string, string> = {
    dashboard: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>`,
    category: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>`,
    box: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>`,
    scan: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/></svg>`,
    organization: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    chart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
    transfer: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`
  }
  return icons[name] || icons.dashboard
}
</script>

<template>
  <div class="layout" :class="{ collapsed: isCollapsed }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 32 32" fill="none">
              <rect x="2" y="2" width="12" height="12" rx="2" fill="currentColor" opacity="0.9"/>
              <rect x="18" y="2" width="12" height="12" rx="2" fill="currentColor" opacity="0.6"/>
              <rect x="2" y="18" width="12" height="12" rx="2" fill="currentColor" opacity="0.6"/>
              <rect x="18" y="18" width="12" height="12" rx="2" fill="currentColor" opacity="0.3"/>
            </svg>
          </div>
          <transition name="fade">
            <span v-if="!isCollapsed" class="logo-text">磐盘</span>
          </transition>
        </div>
        <button class="collapse-btn" @click="toggleSidebar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 19l-7-7 7-7M18 19l-7-7 7-7" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>

      <nav class="sidebar-nav">
        <ul class="nav-list">
          <li v-for="item in navItems" :key="item.path" class="nav-item">
            <a
              v-if="!item.children"
              class="nav-link"
              :class="{ active: isActive(item.path) }"
              @click="navigateTo(item.path)"
            >
              <span class="nav-icon" v-html="getIcon(item.icon)" />
              <transition name="fade">
                <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
              </transition>
              <span v-if="item.badge && !isCollapsed" class="nav-badge">{{ item.badge }}</span>
            </a>

            <template v-else>
              <a class="nav-link" :class="{ active: isActive(item.path) || isChildActive(item) }" @click.stop="toggleDropdown(item.path)">
                <span class="nav-icon" v-html="getIcon(item.icon)" />
                <transition name="fade">
                  <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
                </transition>
                <svg v-if="!isCollapsed" class="nav-arrow" :class="{ rotated: expandedMenu === item.path }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9 18l6-6-6-6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </a>
              <div v-if="!isCollapsed" class="nav-submenu" :class="{ expanded: expandedMenu === item.path }">
                <a
                  v-for="child in item.children"
                  :key="child.path"
                  class="nav-submenu-item"
                  :class="{ active: isActive(child.path) }"
                  @click="navigateTo(child.path)"
                >
                  {{ child.label }}
                </a>
              </div>
            </template>
          </li>
        </ul>
      </nav>

      <div class="sidebar-footer">
        <div class="user-card" @click="openUserPanel">
          <div class="user-avatar" :class="{ 'has-avatar': !!userInfo.avatar || !!userInfo.systemAvatar }">
            <img v-if="userInfo.avatar" :src="userInfo.avatar" class="avatar-img" />
            <span v-else-if="userInfo.systemAvatar" class="avatar-svg" v-html="getSystemAvatarSvg(userInfo.systemAvatar, 36)" />
            <span v-else class="avatar-initial">{{ userInfo.name.charAt(0) }}</span>
          </div>
          <transition name="fade">
            <div v-if="!isCollapsed" class="user-info">
              <div class="user-name">{{ userInfo.name }}</div>
              <div class="user-role">{{ roleLabels[userInfo.role] || userInfo.role }}</div>
            </div>
          </transition>
        </div>

        <!-- 用户面板弹窗（锚定侧边栏） -->
        <Transition name="panel">
          <div v-if="showUserPanel" class="user-panel-wrapper">
            <div class="user-panel-overlay" @click="closeUserPanel"></div>
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
                <button class="panel-close" @click="closeUserPanel">
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
                  <button class="action-btn logout" @click="handleLogout">
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
                <div class="password-form">
                  <div class="form-item">
                    <label>旧密码</label>
                    <input v-model="passwordForm.oldPassword" type="password" placeholder="请输入旧密码" autocomplete="current-password" />
                  </div>
                  <div class="form-item">
                    <label>新密码</label>
                    <input v-model="passwordForm.newPassword" type="password" placeholder="请输入新密码（至少6位）" autocomplete="new-password" />
                  </div>
                  <div class="form-item">
                    <label>确认密码</label>
                    <input v-model="passwordForm.confirmPassword" type="password" placeholder="请再次输入新密码" autocomplete="new-password" />
                  </div>
                  <button class="btn-save" :disabled="passwordLoading" @click="handleChangePassword">
                    {{ passwordLoading ? '提交中...' : '确认修改' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </aside>

    <div class="main">
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg-page);
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--color-bg-sidebar);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-base);
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 100;
}

.layout.collapsed .sidebar {
  width: var(--sidebar-collapsed-width);
}

.sidebar-header {
  height: var(--header-height);
  padding: 0 var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--color-border);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: var(--color-primary-500);
  flex-shrink: 0;
}

.logo-text {
  font-size: var(--text-xl);
  font-weight: 700;
  color: rgba(255, 255, 255, 0.95);
  letter-spacing: -0.02em;
}

.collapse-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.collapse-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.95);
}

.collapse-btn:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

.layout.collapsed .collapse-btn svg {
  transform: rotate(180deg);
}

.collapse-btn svg {
  width: 18px;
  height: 18px;
  transition: transform var(--transition-base);
}

.sidebar-nav {
  flex: 1;
  padding: var(--space-4) var(--space-3);
  overflow-y: auto;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  margin-bottom: var(--space-1);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 1);
}

.nav-link:focus-visible {
  outline: 2px solid var(--color-primary-300);
  outline-offset: 2px;
}

.nav-link.active {
  background: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 1);
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon :deep(svg) {
  width: 100%;
  height: 100%;
}

.nav-label {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: 500;
  white-space: nowrap;
}

.nav-badge {
  background: var(--color-danger);
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.nav-arrow {
  width: 16px;
  height: 16px;
  margin-left: auto;
  transition: transform var(--transition-fast);
}

.nav-arrow.rotated {
  transform: rotate(90deg);
}

/* 内联折叠子菜单 */
.nav-submenu {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.2s ease;
}

.nav-submenu.expanded {
  max-height: 400px;
}

.nav-submenu-item {
  display: block;
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-10);
  font-size: var(--text-sm);
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-submenu-item:hover {
  color: rgba(255, 255, 255, 1);
  background: rgba(255, 255, 255, 0.1);
}

.nav-submenu-item.active {
  color: rgba(255, 255, 255, 1);
  background: rgba(255, 255, 255, 0.15);
  font-weight: 500;
}

/* sidebar-footer：定位锚点 */
.sidebar-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
  position: relative;
}

.user-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
  border-radius: 8px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.user-card:hover {
  background: rgba(255, 255, 255, 0.1);
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: var(--text-sm);
  flex-shrink: 0;
  cursor: pointer;
  overflow: hidden;
  position: relative;
  transition: box-shadow var(--transition-fast);
}

.user-avatar:hover {
  box-shadow: 0 0 0 2px var(--color-primary-200);
}

.user-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-avatar .avatar-svg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar .avatar-initial {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
}

.user-role {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.65);
}

/* 用户面板弹窗 - 锚定侧边栏底部 */
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

/* 面板过渡动画 */
.panel-enter-active {
  transition: opacity 0.2s ease;
}
.panel-enter-active .user-panel {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.panel-leave-active {
  transition: opacity 0.15s ease;
}
.panel-leave-active .user-panel {
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.panel-enter-from {
  opacity: 0;
}
.panel-enter-from .user-panel {
  transform: translateX(-8px) scale(0.97);
  opacity: 0;
}
.panel-leave-to {
  opacity: 0;
}
.panel-leave-to .user-panel {
  transform: translateX(-8px) scale(0.97);
  opacity: 0;
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

/* 修改密码区域 */
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

.password-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-item label {
  font-size: var(--text-sm);
  color: rgba(0, 0, 0, 0.65);
  font-weight: 500;
}

.form-item input {
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: var(--text-sm);
  background: var(--color-bg-elevated);
  color: rgba(0, 0, 0, 0.85);
  outline: none;
  transition: border-color var(--transition-fast);
}

.form-item input:focus {
  border-color: var(--color-primary-500);
}

.form-item input::placeholder {
  color: rgba(0, 0, 0, 0.35);
}

.main {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left var(--transition-base);
}

.layout.collapsed .main {
  margin-left: var(--sidebar-collapsed-width);
}

.content {
  flex: 1;
  padding: var(--space-6);
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-fast);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
  }

  .main {
    margin-left: 0;
  }

  .nav-link {
    min-height: 44px;
    padding: var(--space-3) var(--space-4);
  }

  .collapse-btn {
    width: 44px;
    height: 44px;
  }
}
</style>
