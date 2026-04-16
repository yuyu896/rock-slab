import request from '@/utils/request'
import type { PaginatedResponse, PaginationParams } from '@/types'

export interface AuditLog {
  id: string
  userId: string
  userName: string
  userPhone: string
  action: 'login' | 'logout' | 'create' | 'update' | 'delete' | 'approve' | 'reject' | 'export' | 'import' | 'view'
  actionDisplay: string
  resourceType: string
  resourceId?: string
  resourceName: string
  description: string
  beforeData?: Record<string, any>
  afterData?: Record<string, any>
  ipAddress?: string
  userAgent?: string
  requestPath?: string
  requestMethod?: string
  isSuccess: boolean
  errorMessage?: string
  createdAt: string
}

export interface AuditLogStats {
  date: string
  total: number
  success: number
  failed: number
}

export interface ActionStats {
  action: string
  count: number
}

export interface ResourceStats {
  resourceType: string
  count: number
}

// 获取审计日志列表
export function getAuditLogs(params?: PaginationParams & {
  action?: string
  resourceType?: string
  userId?: string
  isSuccess?: boolean
  startDate?: string
  endDate?: string
  search?: string
}) {
  return request.get<PaginatedResponse<AuditLog>>('/api/audit/', { params })
}

// 获取单条审计日志详情
export function getAuditLogDetail(id: string) {
  return request.get<AuditLog>(`/api/audit/${id}/`)
}

// 获取操作统计（最近7天）
export function getAuditStatistics() {
  return request.get<AuditLogStats[]>('/api/audit/statistics/')
}

// 按操作类型统计
export function getAuditByAction() {
  return request.get<ActionStats[]>('/api/audit/by_action/')
}

// 按资源类型统计
export function getAuditByResource() {
  return request.get<ResourceStats[]>('/api/audit/by_resource/')
}

// 用户活跃度统计
export function getAuditUserActivity() {
  return request.get<any[]>('/api/audit/user_activity/')
}

// 获取当前用户的操作日志
export function getMyAuditLogs() {
  return request.get<AuditLog[]>('/api/audit/my_logs/')
}
