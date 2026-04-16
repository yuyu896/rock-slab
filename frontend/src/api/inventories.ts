/* 磐盘 - 盘点 API */
import request from '@/utils/request'
import type {
  InventoryTask,
  InventoryItem,
  InventoryCheck,
  InventoryProgress,
  InventoryReport,
  PaginatedResponse,
  PaginationParams,
} from '@/types'

export function getInventoryTasks(params?: PaginationParams & {
  status?: string
  branchId?: string
}) {
  return request.get<PaginatedResponse<InventoryTask>>('/api/inventories/', { params })
}

export function getInventoryTask(id: string) {
  return request.get<InventoryTask>(`/api/inventories/${id}`)
}

export function createInventoryTask(data: Partial<InventoryTask>) {
  return request.post<InventoryTask>('/api/inventories/', data)
}

export function updateInventoryTask(id: string, data: Partial<InventoryTask>) {
  return request.put<InventoryTask>(`/api/inventories/${id}`, data)
}

export function deleteInventoryTask(id: string) {
  return request.delete(`/api/inventories/${id}`)
}

/** 开始盘点 */
export function startInventory(id: string) {
  return request.post<InventoryTask>(`/api/inventories/${id}/start`)
}

/** 盘点单项 */
export function checkInventoryItem(id: string, data: { assetId: string; qty: number; remarks?: string }) {
  return request.post<InventoryCheck>(`/api/inventories/${id}/check`, data)
}

/** 提交审核 */
export function submitInventory(id: string) {
  return request.post<InventoryTask>(`/api/inventories/${id}/submit`)
}

/** 审核通过 */
export function approveInventory(id: string) {
  return request.post<InventoryTask>(`/api/inventories/${id}/approve`)
}

/** 审核驳回 */
export function rejectInventory(id: string, data: { reason: string }) {
  return request.post<InventoryTask>(`/api/inventories/${id}/reject`, data)
}

/** 重新盘点（驳回后） */
export function recountInventory(id: string, data?: { reset_scope?: 'all' | 'abnormal_only' }) {
  return request.post<InventoryTask>(`/api/inventories/${id}/recount`, data)
}

/** 作废 */
export function cancelInventory(id: string) {
  return request.post<InventoryTask>(`/api/inventories/${id}/cancel`)
}

/** 盘点报告 */
export function getInventoryReport(id: string) {
  return request.get<InventoryReport>(`/api/inventories/${id}/report`)
}

/** 盘点进度 */
export function getInventoryProgress(id: string) {
  return request.get<InventoryProgress>(`/api/inventories/${id}/progress`)
}

/** 盘点记录（多人协作） */
export function getInventoryChecks(id: string, params?: PaginationParams) {
  return request.get<PaginatedResponse<InventoryCheck>>(`/api/inventories/${id}/checks`, { params })
}

/** 下载盘点模板 */
export function downloadInventoryTemplate(id: string) {
  return request.get(`/api/inventories/${id}/import-template`, { responseType: 'blob' })
}

/** 导入盘点结果 */
export function importInventoryResult(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/api/inventories/${id}/import-result`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
