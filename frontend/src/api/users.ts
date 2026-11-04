/* 磐盘 - 用户 API */
import request from '@/utils/request'
import type { User, PaginationParams } from '@/types'

export function getUsers(params?: PaginationParams & {
  role?: string
  branch?: string
  keyword?: string
  scope?: 'write'
}) {
  return request.get<User[]>('/api/users/', { params })
}

export function getUser(id: string) {
  return request.get<User>(`/api/users/${id}`)
}

export function createUser(data: Partial<User> & { password: string }) {
  return request.post<User>('/api/users/', data)
}

export function updateUser(id: string, data: Partial<User>) {
  return request.patch<User>(`/api/users/${id}`, data)
}

export interface UserDeleteResponsibility {
  key: string
  node_type: 'region' | 'team' | 'branch'
  type: string
  id: string
  name: string
  role: string
  candidates: Array<{ id: string; name: string }>
}

export interface UserDeletePreview {
  user: { id: string; name: string }
  responsibilities: UserDeleteResponsibility[]
  legacy_draft_candidates: UserLegacyDraftCandidate[]
}

export interface UserLegacyDraftCandidate {
  id: string
  document_number: string
  action_type: string
  creator_snapshot: string
  date: string | null
}

export function getUserDeletePreview(id: string) {
  return request.get<UserDeletePreview>(`/api/users/${id}/delete-preview`)
}

export interface UserSuccessorAssignment {
  node_type: UserDeleteResponsibility['node_type']
  node_id: string
  user_id: string
}

export function deleteUser(
  id: string,
  successors: UserSuccessorAssignment[] = [],
  legacyDraftReviewedIds: string[] = [],
  legacyDraftIds: string[] = [],
) {
  return request.delete(`/api/users/${id}`, { data: {
    successors,
    legacy_draft_reviewed_ids: legacyDraftReviewedIds,
    legacy_draft_ids: legacyDraftIds,
  } })
}

export function uploadAvatar(id: string, file: File) {
  const formData = new FormData()
  formData.append('avatar', file)
  return request.post<User>(`/api/users/${id}/avatar`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteAvatar(id: string) {
  return request.delete<User>(`/api/users/${id}/avatar`)
}

export function setSystemAvatar(id: string, avatarKey: string) {
  return request.post<User>(`/api/users/${id}/system-avatar`, { system_avatar: avatarKey })
}
