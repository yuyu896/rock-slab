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

/** 台账增量导入（P1）：默认差异预览；confirm=true 逐差异生成调整单 */
export function importAssetStocks(file: File, confirm = false) {
  const formData = new FormData()
  formData.append('file', file)
  if (confirm) formData.append('confirm', '1')
  return request.post<{
    diffs?: import('@/types').LedgerImportDiff[]
    applied?: number
    errors: string[]
  }>('/api/assets/summary/import', formData, {
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

// ── 固定资产实例（P2 第二刀：冻结只读 + 序列号补录 + 生平；变动经流转单） ──

export function getFixedAssets(params?: PaginationParams & {
  branch?: string
  status?: string
  /** 品目编号精确筛选（实例点选器用） */
  asset_code?: string
  /** 品目编号/名称关键字 */
  item_keyword?: string
  /** '1' = 仅待补录序列号 */
  pending_serial?: string
  keyword?: string
}) {
  return request.get<PaginatedResponse<FixedAsset>>('/api/assets/fixed-assets', { params })
}

export function getFixedAsset(id: string) {
  return request.get<FixedAsset>(`/api/assets/fixed-assets/${id}`)
}

/** 序列号补录（manage_instances 权限；仅 序列号/备注 两字段） */
export function supplementFixedAsset(id: string, data: { 序列号?: string; 备注?: string }) {
  return request.patch<FixedAsset>(`/api/assets/fixed-assets/${id}/supplement`, data)
}

/** 实例生平：出生信息 + 关联全部明细行倒序 */
export function getFixedAssetTimeline(id: string) {
  return request.get<import('@/types').FixedAssetTimeline>(`/api/assets/fixed-assets/${id}/timeline`)
}

/** 导出固定资产 Excel（遵循页面筛选） */
export function exportFixedAssets(params?: Record<string, string>) {
  return request.get<Blob>('/api/assets/fixed-assets/export', { params, responseType: 'blob' })
}
