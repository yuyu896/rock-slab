/* 磐盘 - 资产 API（P2 第三刀起 Asset 退役：台账 / 调整单 / 实例档案）*/
import request from '@/utils/request'
import type { AssetStock, FixedAsset, LedgerAdjustment, PaginatedResponse, PaginationParams } from '@/types'

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


// ── 台账调整单（P3：手动开单 + 记录列表；盘点差异单由审批自动生成） ──

export function getLedgerAdjustments(params?: PaginationParams & {
  branch?: string
  assetCode?: string
  dateFrom?: string
  dateTo?: string
}) {
  return request.get<PaginatedResponse<LedgerAdjustment>>('/api/assets/adjustments', { params })
}

/** 手动开调整单（adjust_ledger 权限；创建即生效走唯一写入口） */
export function createLedgerAdjustment(data: {
  branch: string
  资产编号: string
  目标列: string
  变动量: number
  事由: string
}) {
  return request.post<LedgerAdjustment>('/api/assets/adjustments', data)
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
