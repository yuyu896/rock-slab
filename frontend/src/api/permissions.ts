/* 磐盘 - 管理权限 API（组织节点授权 + 业务操作授权） */
import request from '@/utils/request'

/** 组织节点授权：is_all_data（全部数据）或 region / branch / team 三选一 */
export interface ManagementScope {
  id: string
  user: string
  is_all_data?: boolean
  isAllData?: boolean
  region: string | null
  branch: string | null
  team: string | null
  created_at?: string
}

/** 业务操作授权 */
export interface OperationGrant {
  id: string
  user: string
  code: string
  label?: string
  created_at?: string
}

/** 操作码目录项 */
export interface OperationItem {
  code: string
  label: string
}

/** 当前用户权限摘要（/me） */
export interface MyPermissionSummary {
  id: string
  name: string
  phone: string
  role: string
  managementScopes: ManagementScope[]
  operations: string[]
}

/* ===== 组织节点授权 ===== */
export function getManagementScopes(params?: { user?: string }) {
  return request.get<ManagementScope[]>('/api/permissions/management-scopes', { params })
}
export function createManagementScope(data: Partial<ManagementScope>) {
  return request.post<ManagementScope>('/api/permissions/management-scopes', data)
}
export function deleteManagementScope(id: string) {
  return request.delete(`/api/permissions/management-scopes/${id}`)
}

/* ===== 业务操作授权 ===== */
export function getOperationGrants(params?: { user?: string; code?: string }) {
  return request.get<OperationGrant[]>('/api/permissions/operation-grants', { params })
}
export function createOperationGrant(data: { user: string; code: string }) {
  return request.post<OperationGrant>('/api/permissions/operation-grants', data)
}
export function deleteOperationGrant(id: string) {
  return request.delete(`/api/permissions/operation-grants/${id}`)
}

/* ===== 目录与当前用户 ===== */
export function getOperationCatalog() {
  return request.get<OperationItem[]>('/api/permissions/operations')
}
export function getMyPermissions() {
  return request.get<MyPermissionSummary>('/api/permissions/me')
}
