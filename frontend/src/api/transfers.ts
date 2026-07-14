/* 磐盘 - 调拨/流转 API */
import request from '@/utils/request'
import type { Transfer, PaginatedResponse, PaginationParams } from '@/types'

export function getTransfers(params?: PaginationParams & {
  status?: string
  fromBranch?: string
  toBranch?: string
  type?: string
  keyword?: string
  createdAt__gte?: string
}) {
  return request.get<PaginatedResponse<Transfer>>('/api/transfers/', { params })
}

export function getTransfer(id: string) {
  return request.get<Transfer>(`/api/transfers/${id}`)
}

/** 采购入库（draft=true 保存为草稿） */
export function purchaseAsset(data: Partial<Transfer> & { draft?: boolean }) {
  return request.post<Transfer>('/api/transfers/purchase', data)
}

/** 资产领用 */
export function assignAsset(data: Partial<Transfer>) {
  return request.post<Transfer>('/api/transfers/assign', data)
}

/** 资产归还 */
export function returnAsset(data: Partial<Transfer>) {
  return request.post<Transfer>('/api/transfers/return', data)
}

/** 资产调拨 */
export function transferAsset(data: Partial<Transfer>) {
  return request.post<Transfer>('/api/transfers/transfer', data)
}

/** 资产回收 */
export function recoverAsset(data: Partial<Transfer>) {
  return request.post<Transfer>('/api/transfers/recovery', data)
}

/** 审批通过 */
export function approveTransfer(id: string, data: { approved: boolean; reason?: string }) {
  return request.post<Transfer>(`/api/transfers/${id}/approve`, data)
}

/** 审批驳回 */
export function rejectTransfer(id: string, data: { reason?: string }) {
  return request.post<Transfer>(`/api/transfers/${id}/approve`, { approved: false, ...data })
}

/** 提交采购草稿（草稿→待审批） */
export function submitTransfer(id: string) {
  return request.post<Transfer>(`/api/transfers/${id}/submit`)
}

/** 获取待审批列表 */
export function getPendingTransfers(params?: PaginationParams) {
  return request.get<PaginatedResponse<Transfer>>('/api/transfers/', {
    params: { ...params, status: '待审批' }
  })
}

/** Excel 批量导入流转记录 */
export function importTransfers(file: File, type?: string) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ imported: number; errors: string[] }>('/api/transfers/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params: type ? { type } : undefined,
  })
}

/** Excel 导出流转记录 */
export function exportTransfers(params?: Record<string, string>) {
  return request.get<Blob>('/api/transfers/export', { params, responseType: 'blob' })
}
