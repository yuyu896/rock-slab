<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/store/notification'

const router = useRouter()
const notificationStore = useNotificationStore()

const showDropdown = ref(false)
const activeTab = ref<'all' | 'unread'>('all')

const typeLabels: Record<string, string> = {
  approval: '审批提醒',
  task: '任务通知',
  cc: '抄送通知',
  system: '系统通知',
}

const typeColors: Record<string, string> = {
  approval: 'var(--color-warning-500)',
  task: 'var(--color-primary-500)',
  cc: 'var(--color-info-500)',
  system: 'var(--color-text-tertiary)',
}

const filteredNotifications = computed(() => {
  if (activeTab.value === 'unread') {
    return notificationStore.notifications.filter((n) => !n.isRead)
  }
  return notificationStore.notifications
})

function toggleDropdown() {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value) {
    notificationStore.fetchNotifications()
  }
}

function closeDropdown() {
  showDropdown.value = false
}

async function handleNotificationClick(notification: any) {
  await notificationStore.markAsRead(notification.id)
  closeDropdown()

  // 根据关联对象跳转
  if (notification.relatedObjectType === 'transfer') {
    router.push('/assets/transfer')
  } else if (notification.relatedObjectType === 'inventory_task') {
    router.push('/inventory')
  }
}

async function handleMarkAllRead() {
  await notificationStore.markAllAsRead()
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins} 分钟前`
  if (diffHours < 24) return `${diffHours} 小时前`
  if (diffDays < 7) return `${diffDays} 天前`
  return date.toLocaleDateString('zh-CN')
}

// 点击外部关闭
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.notification-center')) {
    closeDropdown()
  }
}

onMounted(() => {
  notificationStore.init()
  document.addEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="notification-center" @click.stop>
    <!-- 触发按钮 -->
    <div class="notification-trigger" @click="toggleDropdown">
      <svg class="bell-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
      <span
        v-if="notificationStore.unreadCount > 0"
        class="badge"
      >
        {{ notificationStore.unreadCount > 99 ? '99+' : notificationStore.unreadCount }}
      </span>
    </div>

    <!-- 下拉面板 -->
    <Transition name="dropdown">
      <div v-if="showDropdown" class="notification-dropdown">
        <!-- 头部 -->
        <div class="dropdown-header">
          <h3>消息通知</h3>
          <button
            v-if="notificationStore.unreadCount > 0"
            class="mark-all-btn"
            @click="handleMarkAllRead"
          >
            全部已读
          </button>
        </div>

        <!-- Tab 切换 -->
        <div class="tab-bar">
          <button
            :class="{ active: activeTab === 'all' }"
            @click="activeTab = 'all'"
          >
            全部
          </button>
          <button
            :class="{ active: activeTab === 'unread' }"
            @click="activeTab = 'unread'"
          >
            未读 ({{ notificationStore.unreadCount }})
          </button>
        </div>

        <!-- 通知列表 -->
        <div class="notification-list">
          <div
            v-for="notification in filteredNotifications.slice(0, 10)"
            :key="notification.id"
            class="notification-item"
            :class="{ unread: !notification.isRead }"
            @click="handleNotificationClick(notification)"
          >
            <div class="notification-header">
              <span
                class="type-tag"
                :style="{ background: typeColors[notification.notificationType] || typeColors.system }"
              >
                {{ typeLabels[notification.notificationType] || '系统' }}
              </span>
              <span class="time">{{ formatTime(notification.createdAt) }}</span>
            </div>
            <div class="notification-title">{{ notification.title }}</div>
            <div class="notification-content">{{ notification.content }}</div>
          </div>

          <div v-if="filteredNotifications.length === 0" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>暂无通知</p>
          </div>
        </div>

        <!-- 底部 -->
        <div class="dropdown-footer">
          <router-link to="/notifications" @click="closeDropdown">
            查看全部消息
          </router-link>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.notification-center {
  position: relative;
}

.notification-trigger {
  position: relative;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.2s;
}

.notification-trigger:hover {
  background: var(--color-bg-elevated);
}

.bell-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-secondary);
}

.badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 600;
  color: white;
  background: var(--color-danger-500);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 360px;
  max-height: 480px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--color-border);
}

.dropdown-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.mark-all-btn {
  font-size: 13px;
  color: var(--color-primary-500);
  background: none;
  border: none;
  cursor: pointer;
}

.mark-all-btn:hover {
  text-decoration: underline;
}

.tab-bar {
  display: flex;
  padding: 8px 16px;
  gap: 8px;
  border-bottom: 1px solid var(--color-border);
}

.tab-bar button {
  flex: 1;
  height: 32px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.tab-bar button.active {
  background: var(--color-primary-500);
  color: white;
}

.notification-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.notification-item {
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: var(--color-bg-elevated);
}

.notification-item.unread {
  background: var(--color-primary-50);
}

.notification-item.unread:hover {
  background: var(--color-primary-100);
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.type-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  color: white;
}

.time {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.notification-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 2px;
}

.notification-content {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin-bottom: 12px;
}

.dropdown-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.dropdown-footer a {
  font-size: 13px;
  color: var(--color-primary-500);
  text-decoration: none;
}

.dropdown-footer a:hover {
  text-decoration: underline;
}

/* 过渡动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
