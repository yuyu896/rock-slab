/* 磐盘 - 部门字典 API */
import request from '@/utils/request'
import type { PaginatedResponse } from '@/types'

export interface Department {
  id: string
  branch: string
  branchName?: string
  name: string
}

export function getDepartments(params?: { page?: number; pageSize?: number; branch?: string }) {
  return request.get<PaginatedResponse<Department>>('/api/departments/', { params })
}

export function createDepartment(data: { branch: string; name: string }) {
  return request.post<Department>('/api/departments/', data)
}

export function deleteDepartment(id: string) {
  return request.delete(`/api/departments/${id}`)
}

/** 按分公司返回部门选项（表单下拉；登录即可） */
export function getDepartmentOptions(params: { branch?: string; branch_id?: string }) {
  return request.get<Department[]>('/api/departments/options', { params })
}
