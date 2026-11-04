/* 磐盘 - 供应商字典 API（全集团扁平，admin 维护） */
import request from '@/utils/request'
import type { PaginatedResponse } from '@/types'

export interface Supplier {
  id: string
  name: string
  联系人?: string
  电话?: string
}

export function getSuppliers(params?: { page?: number; pageSize?: number }) {
  return request.get<PaginatedResponse<Supplier>>('/api/suppliers/', { params })
}

/** 实例编辑只需供应商 ID 和名称，不授予查看供应商联系人、电话的权限。 */
export function getInstanceSupplierOptions() {
  return request.get<Array<Pick<Supplier, 'id' | 'name'>>>('/api/suppliers/instance-options')
}

export function createSupplier(data: { name: string; 联系人?: string; 电话?: string }) {
  return request.post<Supplier>('/api/suppliers/', data)
}

export function updateSupplier(id: string, data: Partial<{ name: string; 联系人: string; 电话: string }>) {
  return request.patch<Supplier>(`/api/suppliers/${id}`, data)
}

export function deleteSupplier(id: string) {
  return request.delete(`/api/suppliers/${id}`)
}
