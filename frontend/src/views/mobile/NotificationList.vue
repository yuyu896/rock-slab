<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/store/notification'
import type { Notification } from '@/api/notifications'
import { ElMessage } from 'element-plus'

const router = useRouter()
const notificationStore = useNotificationStore()

const notifications = ref<Notification[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const currentPage = ref(1)
const pageSize = 20
const hasMore = ref(true)
const filterUnreadOnly = ref(false)

async function fetchNotifications(loadMore = false) {
  if (loadMore) {
    loadingMore.value = true
  } else {
    loading.value = true
  }

  try {
    const result = await notificationStore.fetchNotifications({
      isRead: filterUnreadOnly.value ? false : undefined,
    })
    if (!loadMore) {
      notifications.value = result?.results || []
    }
    const results = result?.results || []
    hasMore.value = results.length >= pageSize
  } catch {
    ElMessage.error('获取通知列表失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function handleMarkAsRead(id: string) {
  try {
    await notificationStore.markAsRead(id)
    const notification = notifications.value.find(n => n.id === id)
    if (notification) {
      notification.isRead = true
    }
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleMarkAllRead() {
  try {
    await notificationStore.markAllAsRead()
    notifications.value.forEach(n => {
      n.isRead = true
    })
    ElMessage.success('已全部标记为已读')
  } catch {
    ElMessage.error('操作失败')
  }
}

function loadMore() {
  if (loadingMore.value || !hasMore.value) return
  currentPage.value++
  fetchNotifications(true)
}

function toggleFilter() {
  filterUnreadOnly.value = !filterUnreadOnly.value
  currentPage.value = 1
  fetchNotifications()
}

function goBack() {
  router.back()
}

function formatTime(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function getTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    approval: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4.5 4.5"/></svg>',
    task: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/></svg>',
    cc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    system: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  }
  return icons[type] || icons.system
}

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    approval: '审批',
    task: '任务',
    cc: '抄送',
    system: '系统',
  }
  return labels[type] || '通知'
}

onMounted(() => {
  fetchNotifications()
})
</script>

<template>
  <div class="notification-page">
    <!-- 头部 -->
    <div class="page-header">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
      <h1>通知中心</h1>
      <button class="mark-all-btn" @click="handleMarkAllRead">全部已读</button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <button class="filter-btn" :class="{ active: !filterUnreadOnly }" @click="filterUnreadOnly ? toggleFilter() : null">
        全部
      </button>
      <button class="filter-btn" :class="{ active: filterUnreadOnly }" @click="!filterUnreadOnly ? toggleFilter() : null">
        未读
      </button>
    </div>

    <!-- 通知列表 -->
    <div class="notification-list">
      <div v-if="loading" class="loading-state">
        <span>加载中...</span>
      </div>

      <template v-else-if="notifications.length > 0">
        <div
          v-for="item in notifications"
          :key="item.id"
          class="notification-item"
          :class="{ unread: !item.isRead }"
        >
          <div class="notification-icon" :class="item.notificationType">
            <span v-html="getTypeIcon(item.notificationType)" />
          </div>
          <div class="notification-content">
            <div class="notification-header">
              <span class="notification-type-tag">{{ getTypeLabel(item.notificationType) }}</span>
              <span class="notification-time">{{ formatTime(item.createdAt) }}</span>
            </div>
            <div class="notification-title">{{ item.title }}</div>
            <div class="notification-text">{{ item.content }}</div>
          </div>
          <div class="notification-actions">
            <span v-if="!item.isRead" class="unread-dot"></span>
            <button v-if="!item.isRead" class="read-btn" @click.stop="handleMarkAsRead(item.id)">
              标已读
            </button>
          </div>
        </div>

        <div v-if="hasMore" class="load-more">
          <button class="load-more-btn" @click="loadMore" :disabled="loadingMore">
            {{ loadingMore ? '加载中...' : '加载更多' }}
          </button>
        </div>
      </template>

      <div v-else class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <p>暂无通知</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notification-page {
  min-height: 100vh;
  background: var(--color-bg-page);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.page-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.back-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-elevated);
  border: none;
  border-radius: 50%;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.back-btn svg {
  width: 20px;
  height: 20px;
}

.mark-all-btn {
  font-size: 13px;
  color: var(--color-primary-500);
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-2);
}

.filter-bar {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
}

.filter-btn {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-bg-page);
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
}

.filter-btn.active {
  background: var(--color-primary-500);
  color: white;
  border-color: var(--color-primary-500);
}

.notification-list {
  padding: var(--space-3);
}

.notification-item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  margin-bottom: var(--space-2);
  position: relative;
}

.notification-item.unread {
  border-left: 3px solid var(--color-primary-500);
}

.notification-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.notification-icon svg {
  width: 20px;
  height: 20px;
}

.notification-icon.approval {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.notification-icon.task {
  background: var(--color-primary-50);
  color: var(--color-primary-500);
}

.notification-icon.cc {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.notification-icon.system {
  background: var(--color-bg-elevated);
  color: var(--color-text-tertiary);
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 4px;
}

.notification-type-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--color-bg-elevated);
  color: var(--color-text-tertiary);
}

.notification-time {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.notification-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 4px;
  line-height: 1.4;
}

.notification-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notification-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary-500);
}

.read-btn {
  font-size: 11px;
  padding: 4px 8px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-elevated);
  color: var(--color-text-secondary);
  cursor: pointer;
  white-space: nowrap;
}

.loading-state,
.empty-state {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin-bottom: var(--space-3);
}

.load-more {
  text-align: center;
  padding: var(--space-4);
}

.load-more-btn {
  padding: var(--space-2) var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
}

.load-more-btn:disabled {
  opacity: 0.5;
}
</style>
