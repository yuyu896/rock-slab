/* 磐盘 - 部门字典 API（全集团扁平，department-dictionary-flatten） */
import request from '@/utils/request'
import type { PaginatedResponse } from '@/types'

export interface Department {
  id: string
  name: string
}

export function getDepartments(params?: { page?: number; pageSize?: number }) {
  return request.get<PaginatedResponse<Department>>('/api/departments/', { params })
}

export function createDepartment(data: { name: string }) {
  return request.post<Department>('/api/departments/', data)
}

export function deleteDepartment(id: string) {
  return request.delete(`/api/departments/${id}`)
}

/** 返回全集团部门选项（表单下拉；登录即可） */
export function getDepartmentOptions() {
  return request.get<Department[]>('/api/departments/options')
}
