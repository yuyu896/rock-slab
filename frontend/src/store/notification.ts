import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import * as notificationApi from '@/api/notifications'
import { handleApiError } from '@/utils/request'
import type { Notification, NotificationStats } from '@/api/notifications'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)
  const stats = ref<NotificationStats[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 分组后的通知
  const groupedNotifications = computed(() => {
    const groups: Record<string, Notification[]> = {
      approval: [],
      task: [],
      cc: [],
      system: [],
    }
    notifications.value.forEach((n) => {
      if (groups[n.notificationType]) {
        groups[n.notificationType].push(n)
      }
    })
    return groups
  })

  // 获取通知列表
  async function fetchNotifications(params?: { isRead?: boolean }) {
    loading.value = true
    error.value = null
    try {
      const { data } = await notificationApi.getNotifications(params)
      notifications.value = data.results || []
      return data
    } catch (err) {
      error.value = handleApiError(err)
      ElMessage.error(error.value)
    } finally {
      loading.value = false
    }
  }

  // 获取未读数量
  async function fetchUnreadCount() {
    const { data } = await notificationApi.getUnreadCount()
    unreadCount.value = data.count
  }

  // 获取统计数据
  async function fetchStats() {
    const { data } = await notificationApi.getNotificationsByType()
    stats.value = data
  }

  // 标记单条已读
  async function markAsRead(id: string) {
    await notificationApi.markNotificationRead(id)
    const notification = notifications.value.find((n) => n.id === id)
    if (notification) {
      notification.isRead = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  // 标记全部已读
  async function markAllAsRead() {
    const { data } = await notificationApi.markAllNotificationsRead()
    notifications.value.forEach((n) => {
      n.isRead = true
    })
    unreadCount.value = 0
    return data.updated
  }

  // 初始化 - 获取未读数量
  async function init() {
    await Promise.all([fetchUnreadCount(), fetchStats()])
  }

  return {
    notifications,
    unreadCount,
    stats,
    loading,
    error,
    groupedNotifications,
    fetchNotifications,
    fetchUnreadCount,
    fetchStats,
    markAsRead,
    markAllAsRead,
    init,
  }
})
