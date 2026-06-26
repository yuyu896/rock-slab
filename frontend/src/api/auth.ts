/* 磐盘 - 认证 API */
import request from '@/utils/request'
import type { LoginRequest, LoginResponse, User } from '@/types'

/** 手机号 + 密码登录 */
export function login(data: LoginRequest) {
  return request.post<LoginResponse>('/api/auth/login/', data)
}

/** 登出 */
export function logout() {
  return request.post('/api/auth/logout/')
}

/** 获取当前用户信息 */
export function getProfile() {
  return request.get<User>('/api/auth/profile/')
}

/** 修改密码（成功后后端会签发新 Token，需同步本地凭证） */
export function updatePassword(data: { oldPassword: string; newPassword: string }) {
  return request.put<{ detail: string; token: string }>('/api/auth/password/', data)
}
