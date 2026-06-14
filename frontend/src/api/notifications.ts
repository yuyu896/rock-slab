import request from '@/utils/request'
import type { PaginatedResponse, PaginationParams } from '@/types'

export interface Notification {
  id: string
  recipient: string
  notificationType: 'approval' | 'task' | 'cc' | 'system'
  notificationTypeDisplay: string
  title: string
  content: string
  priority: 'high' | 'medium' | 'low'
  priorityDisplay: string
  isRead: boolean
  readAt?: string
  relatedObjectType?: string
  relatedObjectId?: string
  extraData?: Record<string, any>
  createdAt: string
}

export interface ApprovalCC {
  id: string
  transferId?: string
  inventoryTaskId?: string
  ccType: 'auto' | 'manual'
  ccTypeDisplay: string
  ccReason: string
  recipient: string
  recipientName: string
  isRead: boolean
  readAt?: string
  approvalSnapshot: Record<string, any>
  createdAt: string
}

export interface NotificationStats {
  notificationType: string
  total: number
  unread: number
}

// 获取通知列表
export function getNotifications(params?: PaginationParams & {
  notificationType?: string
  isRead?: boolean
  priority?: string
}) {
  return request.get<PaginatedResponse<Notification>>('/api/notifications/', { params })
}

// 获取未读数量
export function getUnreadCount() {
  return request.get<{ count: number }>('/api/notifications/unread_count/')
}

// 标记单条已读
export function markNotificationRead(id: string) {
  return request.post<Notification>(`/api/notifications/${id}/mark_read/`)
}

// 标记全部已读
export function markAllNotificationsRead() {
  return request.post<{ detail: string; updated: number }>('/api/notifications/mark_all_read/')
}

// 按类型分组统计
export function getNotificationsByType() {
  return request.get<NotificationStats[]>('/api/notifications/by_type/')
}

// 获取抄送列表
export function getApprovalCCs(params?: PaginationParams & {
  ccType?: string
  isRead?: boolean
}) {
  return request.get<PaginatedResponse<ApprovalCC>>('/api/notifications/cc/', { params })
}

// 标记抄送已读
export function markCCRead(id: string) {
  return request.post<ApprovalCC>(`/api/notifications/cc/${id}/mark_read/`)
}
