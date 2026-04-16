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

/** 修改密码 */
export function updatePassword(data: { oldPassword: string; newPassword: string }) {
  return request.put('/api/auth/password/', data)
}
