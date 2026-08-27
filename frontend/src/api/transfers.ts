/* 磐盘 - 调拨/流转 API（单头 + items 明细行） */
import request from '@/utils/request'
import type { TransferDocument, TransferLineInput, PaginatedResponse, PaginationParams } from '@/types'

/** 单据创建入参：单头字段 + items 明细行 */
export type TransferPayload = Partial<TransferDocument> & {
  items: TransferLineInput[]
  fromBranch?: string
  toBranch?: string
}

export function getTransfers(params?: PaginationParams & {
  status?: string
  fromBranch?: string
  toBranch?: string
  type?: string
  docNumber?: string
  assetCode?: string
  keyword?: string
  createdAt__gte?: string
}) {
  return request.get<PaginatedResponse<TransferDocument>>('/api/transfers/', { params })
}

export function getTransfer(id: string) {
  return request.get<TransferDocument>(`/api/transfers/${id}`)
}

/** 修改流转（仅已驳回可改；items 传了=整体替换，不传=保留原明细行） */
export function updateTransfer(id: string, data: Partial<TransferPayload>) {
  return request.patch<TransferDocument>(`/api/transfers/${id}`, data)
}

/** 采购入库（draft=true 保存为草稿） */
export function purchaseAsset(data: TransferPayload & { draft?: boolean }) {
  return request.post<TransferDocument>('/api/transfers/purchase', data)
}

/** 资产领用 */
export function assignAsset(data: TransferPayload) {
  return request.post<TransferDocument>('/api/transfers/assign', data)
}

/** 资产归还 */
export function returnAsset(data: TransferPayload) {
  return request.post<TransferDocument>('/api/transfers/return', data)
}

/** 资产调拨 */
export function transferAsset(data: TransferPayload) {
  return request.post<TransferDocument>('/api/transfers/transfer', data)
}

/** 资产回收（统一走审批流：待审批 → 审批通过生效；行内即时通道已下线） */
export function recoverAsset(data: TransferPayload) {
  return request.post<TransferDocument>('/api/transfers/recovery', data)
}

/** 审批通过 */
export function approveTransfer(id: string, data: { approved: boolean; reason?: string }) {
  return request.post<TransferDocument>(`/api/transfers/${id}/approve`, data)
}

/** 审批驳回 */
export function rejectTransfer(id: string, data: { reason?: string }) {
  return request.post<TransferDocument>(`/api/transfers/${id}/approve`, { approved: false, ...data })
}

/** 提交采购草稿（草稿→待审批） */
export function submitTransfer(id: string) {
  return request.post<TransferDocument>(`/api/transfers/${id}/submit`)
}

/** 重新提交流转（已驳回→待审批） */
export function resubmitTransfer(id: string) {
  return request.post<TransferDocument>(`/api/transfers/${id}/resubmit`)
}

/** 获取待审批列表 */
export function getPendingTransfers(params?: PaginationParams) {
  return request.get<PaginatedResponse<TransferDocument>>('/api/transfers/', {
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
