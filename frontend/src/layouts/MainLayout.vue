<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSystemAvatarSvg } from '@/utils/avatar'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import UserPanel from '@/components/layout/UserPanel.vue'

const router = useRouter()
const userStore = useUserStore()

const isCollapsed = ref(false)
const showUserPanel = ref(false)
const userPanelRef = ref<InstanceType<typeof UserPanel> | null>(null)

const roleLabels: Record<string, string> = {
  admin: '超级管理员',
  manager: '行政经理',
  supervisor: '主管',
  leader: '组长',
  staff: '员工'
}

const userInfo = computed(() => ({
  name: userStore.profile?.name || '用户',
  phone: userStore.profile?.phone || '',
  role: userStore.profile?.role || 'staff',
  branch: userStore.profile?.branch || '',
  avatar: userStore.profile?.avatar || '',
  systemAvatar: userStore.profile?.systemAvatar || ''
}))

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value
}

function openUserPanel() {
  if (isCollapsed.value) return
  showUserPanel.value = true
  nextTick(() => {
    userPanelRef.value?.initPanel()
  })
}

function closeUserPanel() {
  showUserPanel.value = false
}

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

      <SidebarNav :is-collapsed="isCollapsed" />

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

        <!-- 用户面板弹窗 -->
        <Transition name="panel">
          <UserPanel
            v-if="showUserPanel"
            ref="userPanelRef"
            :user-info="userInfo"
            :role-labels="roleLabels"
            @close="closeUserPanel"
            @logout="handleLogout"
          />
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

/* sidebar-footer */
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

/* 面板过渡动画 */
.panel-enter-active {
  transition: opacity 0.2s ease;
}
.panel-leave-active {
  transition: opacity 0.15s ease;
}
.panel-enter-from {
  opacity: 0;
}
.panel-leave-to {
  opacity: 0;
}

.main {
  flex: 1;
  min-width: 0;
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

  .collapse-btn {
    width: 44px;
    height: 44px;
  }
}
</style>
