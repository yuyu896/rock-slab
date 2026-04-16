/* 磐盘 - 分公司 API */
import request from '@/utils/request'
import type { Branch } from '@/types'

export function getBranches(params?: { region?: string }) {
  return request.get<Branch[]>('/api/branches/', { params })
}

export function getBranch(id: string) {
  return request.get<Branch>(`/api/branches/${id}`)
}

export function createBranch(data: Partial<Branch>) {
  return request.post<Branch>('/api/branches/', data)
}

export function updateBranch(id: string, data: Partial<Branch>) {
  return request.put<Branch>(`/api/branches/${id}`, data)
}

export function deleteBranch(id: string) {
  return request.delete(`/api/branches/${id}`)
}
