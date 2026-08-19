/* 磐盘 - 资产 API */
import request from '@/utils/request'
import type { Asset, AssetStock, FixedAsset, PaginatedResponse, PaginationParams } from '@/types'

export function getAssets(params?: PaginationParams & {
  branch?: string
  category?: string
  status?: string
  keyword?: string
  ordering?: string
}) {
  return request.get<PaginatedResponse<Asset>>('/api/assets/', { params })
}

// ── 资产汇总（库存台账） ──

export function getAssetStocks(params?: PaginationParams & {
  branch?: string
  category?: string
  keyword?: string
}) {
  return request.get<PaginatedResponse<AssetStock>>('/api/assets/summary', { params })
}

export function createAssetStock(data: Partial<AssetStock>) {
  return request.post<AssetStock>('/api/assets/summary', data)
}

export function updateAssetStock(id: string, data: Partial<AssetStock>) {
  return request.patch<AssetStock>(`/api/assets/summary/${id}`, data)
}

export function deleteAssetStock(id: string) {
  return request.delete(`/api/assets/summary/${id}`)
}

/** 批量删除台账行 */
export function batchDeleteAssetStocks(ids: string[]) {
  return request.post<{ deleted: number }>('/api/assets/summary/batch-delete', { ids })
}

/** Excel 批量导入台账 */
export function importAssetStocks(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ imported: number; errors: string[] }>('/api/assets/summary/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** Excel 导出台账 */
export function exportAssetStocks(params?: Record<string, string>) {
  return request.get<Blob>('/api/assets/summary/export', { params, responseType: 'blob' })
}

/** 下载台账导入模板 */
export function downloadAssetStockTemplate() {
  return request.get<Blob>('/api/assets/summary/template', { responseType: 'blob' })
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

/** Excel 导出（遵循页面筛选） */
export function exportAssets(params?: { branch?: string; category?: string; status?: string; keyword?: string }) {
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
