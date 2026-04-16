/* 磐盘 - 用户 API */
import request from '@/utils/request'
import type { User, PaginationParams } from '@/types'

export function getUsers(params?: PaginationParams & { role?: string; branch?: string; keyword?: string }) {
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

export function deleteUser(id: string) {
  return request.delete(`/api/users/${id}`)
}

export function updatePassword(data: { oldPassword: string; newPassword: string }) {
  return request.put('/api/auth/password/', data)
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
