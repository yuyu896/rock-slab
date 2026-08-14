/* 磐盘 - 资产 API */
import request from '@/utils/request'
import type { Asset, AssetSummaryRow, FixedAsset, PaginatedResponse, PaginationParams } from '@/types'

export function getAssets(params?: PaginationParams & {
  branch?: string
  category?: string
  status?: string
  keyword?: string
  ordering?: string
}) {
  return request.get<PaginatedResponse<Asset>>('/api/assets/', { params })
}

/** 按分公司汇总资产编号（数据范围与列表一致） */
export function getAssetSummary() {
  return request.get<AssetSummaryRow[]>('/api/assets/summary')
}

export function getAsset(id: string) {
  return request.get<Asset>(`/api/assets/${id}`)
}

export function createAsset(data: Partial<Asset>) {
  return request.post<Asset>('/api/assets/', data)
}

export function updateAsset(id: string, data: Partial<Asset>) {
  return request.patch<Asset>(`/api/assets/${id}`, data)
}

export function deleteAsset(id: string) {
  return request.delete(`/api/assets/${id}`)
}

/** 批量删除资产（ids: 资产 id 列表） */
export function batchDeleteAssets(ids: string[]) {
  return request.post<{ deleted: number }>('/api/assets/batch-delete', { ids })
}

/** Excel 批量导入 */
export function importAssets(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ imported: number; errors: string[] }>('/api/assets/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** Excel 导出 */
export function exportAssets(params?: { branch?: string }) {
  return request.get<Blob>('/api/assets/export', { params, responseType: 'blob' })
}

// ── 固定资产实例 ──

export function getFixedAssets(params?: PaginationParams & {
  branch?: string
  status?: string
  keyword?: string
  资产名称?: string
  ordering?: string
}) {
  return request.get<PaginatedResponse<FixedAsset>>('/api/assets/fixed-assets', { params })
}

export function updateFixedAsset(id: string, data: Partial<FixedAsset>) {
  return request.patch<FixedAsset>(`/api/assets/fixed-assets/${id}`, data)
}

export function deleteFixedAsset(id: string) {
  return request.delete(`/api/assets/fixed-assets/${id}`)
}

/** 批量删除固定资产（ids: 固定资产 id 列表） */
export function batchDeleteFixedAssets(ids: string[]) {
  return request.post<{ deleted: number }>('/api/assets/fixed-assets/batch-delete', { ids })
}

export function importFixedAssets(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ imported: number; errors: string[] }>('/api/assets/fixed-assets/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 导出固定资产 Excel */
export function exportFixedAssets(params?: Record<string, string>) {
  return request.get<Blob>('/api/assets/fixed-assets/export', { params, responseType: 'blob' })
}

/** 新增固定资产 */
export function createFixedAsset(data: Partial<FixedAsset>) {
  return request.post<FixedAsset>('/api/assets/fixed-assets', data)
}

/** 下载固定资产导入模板 */
export function downloadFixedAssetTemplate() {
  return request.get<Blob>('/api/assets/fixed-assets/template', { responseType: 'blob' })
}
