import request from '@/utils/request'

export type ScopeNodeType = 'region' | 'branch' | 'team'
export type AuthorizationScopeMode = 'default' | 'custom' | 'all'

export interface ScopeNode {
  id: string
  type: ScopeNodeType
  name: string
}

export interface PermissionOperation {
  code: string
  label: string
  module: string
  module_label: string
  catalog_version: number
  description?: string
  prerequisites: string[]
  conditional_prerequisites: Record<string, string[]>
}

export interface AuthorizationUser {
  id: string
  name: string
  phone: string
  role: string
  status: string
  region: string | null
  branch: string | null
  region_name: string | null
  branch_name: string | null
}

export interface UserAuthorization {
  user: AuthorizationUser
  scope: {
    mode: AuthorizationScopeMode
    nodes: ScopeNode[]
  }
  operations: string[]
  legacy_operations?: string[]
  legacy_operation_details?: { code: string; label: string }[]
}

export interface EffectivePermissionRow {
  user: string
  id?: string
  name: string
  phone: string
  role: string
  status?: string
  region?: string | null
  branch?: string | null
  region_name?: string | null
  branch_name?: string | null
  scope?: {
    mode?: AuthorizationScopeMode
    summary?: string
    nodes?: ScopeNode[]
  }
  scope_summary?: string
  scopeSummary?: { all: boolean; branchCount: number | null }
  operations: string[] | null
  legacy_operations?: string[]
}

export interface EffectivePermissionFilters {
  keyword?: string
  region?: string
  branch?: string
  operation?: string
  module?: string
}

export interface PermissionMatrixOrganizationDirectory {
  regions: { id: string; name: string }[]
  branches: { id: string; name: string; region: string | null }[]
}

export interface PositionBaselinePermission {
  code: string
  label: string
}

export interface PositionBaselineEmployeeDifference {
  user: string
  name: string
  phone: string
  role: string
  role_label: string
  branch_name: string | null
  added: PositionBaselinePermission[]
  removed: PositionBaselinePermission[]
  legacy_codes: string[]
  scope_preserved: boolean
}

export interface PositionBaselinePreview {
  from_version: string | null
  to_version: string
  has_changes: boolean
  active_employee_count: number
  changed_employee_count: number
  added_permission_count: number
  removed_permission_count: number
  legacy_permission_count: number
  inactive_employee_count: number
  role_changes: {
    role: string
    role_label: string
    added: PositionBaselinePermission[]
    removed: PositionBaselinePermission[]
  }[]
  employees: PositionBaselineEmployeeDifference[]
  preview_token: string
}

export interface MyPermissionSummary {
  id: string
  name: string
  phone: string
  role: string
  operations: string[]
  pageOperations: Record<string, string[]>
  operationPrerequisites: Record<string, string[]>
}

export function getOperationCatalog() {
  return request.get<PermissionOperation[]>('/api/permissions/operations')
}

export function getMyPermissions() {
  return request.get<MyPermissionSummary>('/api/permissions/me')
}

export function getUserAuthorization(userId: string) {
  return request.get<UserAuthorization>(`/api/permissions/users/${userId}/authorization`)
}

export function saveUserAuthorization(
  userId: string,
  body: {
    operations: string[]
    scope: { mode: AuthorizationScopeMode; nodes: ScopeNode[] }
    reason?: string
    remove_legacy_operations?: string[]
  },
) {
  return request.put<UserAuthorization>(`/api/permissions/users/${userId}/authorization`, body)
}

export function getEffectivePermissions(params?: EffectivePermissionFilters) {
  return request.get<EffectivePermissionRow[]>('/api/permissions/effective', { params })
}

export function getPermissionMatrixOrganizations() {
  return request.get<PermissionMatrixOrganizationDirectory>('/api/permissions/matrix-organizations')
}

export function getPositionBaselinePreview() {
  return request.get<PositionBaselinePreview>('/api/permissions/position-baselines/preview')
}

export function applyPositionBaseline(data: {
  expected_from_version: string | null
  preview_token: string
}) {
  return request.post<{
    detail: string
    version: string
    synchronized_users: number
    added_permission_count: number
    removed_permission_count: number
    legacy_permission_count_retained_for_review: number
  }>('/api/permissions/position-baselines/apply', data)
}
