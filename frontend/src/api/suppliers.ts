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

export function createSupplier(data: { name: string; 联系人?: string; 电话?: string }) {
  return request.post<Supplier>('/api/suppliers/', data)
}

export function updateSupplier(id: string, data: Partial<{ name: string; 联系人: string; 电话: string }>) {
  return request.patch<Supplier>(`/api/suppliers/${id}`, data)
}

export function deleteSupplier(id: string) {
  return request.delete(`/api/suppliers/${id}`)
}
