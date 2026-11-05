/* 磐盘 - 资产 API（P2 第三刀起 Asset 退役：台账 / 调整单 / 实例档案）*/
import request from '@/utils/request'
import type { AssetStock, FixedAsset, LedgerAdjustment, PaginatedResponse, PaginationParams } from '@/types'

// ── 资产汇总（库存台账） ──

export function getAssetStocks(params?: PaginationParams & {
  branch?: string
  category?: string
  /** 品目编号精确筛选（回收创建页在用预检取数） */
  asset_code?: string
  keyword?: string
  /** '0' = 仅不足行（在库 < 生效警戒线） */
  sufficient?: string
  /** 指定列>0（写单页品目点选按扣数列收口） */
  positive_column?: string
}) {
  return request.get<PaginatedResponse<AssetStock>>('/api/assets/summary', { params })
}

/** Resolve mobile transfer items through the branch ledger. */
export async function lookupAvailableTransferItem(branchName: string, assetCode: string) {
  const { data } = await getAssetStocks({
    branch: branchName,
    asset_code: assetCode,
    positive_column: '在库数量',
    pageSize: 1,
  })
  const row = data.results.find(item => item.资产编号 === assetCode)
  if (!row) throw new Error('该分公司台账中没有可用的此品目')
  if (row.管理方式 === 'instance') throw new Error('实例管理物品请在电脑端选择实例后建单')
  return row.item
}

/** 台账调整专用行信息：仅返回选择调整目标所需的最小字段。 */
export function getAdjustableAssetStocks(params?: PaginationParams & {
  branch?: string
  category?: string
  keyword?: string
  sufficient?: string
  positive_column?: string
}) {
  return request.get<PaginatedResponse<AssetStock>>('/api/assets/summary/adjustable', { params })
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

/** 手动开调整单（adjust_asset_ledger 权限；创建即生效走唯一写入口） */
export function createLedgerAdjustment(data: {
  branch: string
  资产编号: string
  目标列: string
  变动量: number
  事由: string
}) {
  return request.post<LedgerAdjustment>('/api/assets/adjustments', data)
}


// ── 固定资产实例（冻结通用写入；专用补录/图片/使用人交接 + 生平） ──

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

/** 换人权限专用的最小实例列表，不返回采购、档案维护、生平或图片字段。 */
export interface FixedAssetAssigneeTarget {
  id: string
  内部编号: string
  序列号: string
  当前状态: '在用'
  使用人?: string
  department?: string | null
  departmentName?: string
  branch?: string | null
  branchName?: string
  itemCode: string
  itemName: string
}

export function getFixedAssetAssigneeTargets(params?: PaginationParams & { keyword?: string }) {
  return request.get<PaginatedResponse<FixedAssetAssigneeTarget>>(
    '/api/assets/fixed-assets/assignee-targets', { params },
  )
}

/** 编辑权限专用的实例列表，只返回定位和编辑所需字段。 */
export interface FixedAssetEditTarget extends Pick<FixedAsset,
  'id' | '内部编号' | '序列号' | '当前状态' | '供应商' | '采购日期' | '备注' | '图片'
> {
  branch?: string | null
  branchName?: string
  itemCode: string
  itemName: string
  itemSpec?: string
  使用人?: string
  department?: string | null
  departmentName?: string
}

export function getFixedAssetEditTargets(params?: PaginationParams & { edit_keyword?: string }) {
  return request.get<PaginatedResponse<FixedAssetEditTarget>>(
    '/api/assets/fixed-assets/edit-targets', { params },
  )
}

export function getFixedAsset(id: string) {
  return request.get<FixedAsset>(`/api/assets/fixed-assets/${id}`)
}

/** 序列号补录（edit_instances 权限；仅 序列号/备注 两字段） */
export function supplementFixedAsset(id: string, data: { 序列号?: string; 备注?: string }) {
  return request.patch<FixedAsset>(`/api/assets/fixed-assets/${id}/supplement`, data)
}

/** 实例生平：出生信息 + 关联全部明细行倒序 */
export function getFixedAssetTimeline(id: string) {
  return request.get<import('@/types').FixedAssetTimeline>(`/api/assets/fixed-assets/${id}/timeline`)
}

/** 专用单实例使用人交接，与通用档案保存分离 */
export function changeFixedAssetAssignee(id: string, data: {
  使用人: string
  department: string
  原因?: string
}) {
  return request.post<{ asset: FixedAsset | FixedAssetAssigneeTarget; changed: boolean }>(
    `/api/assets/fixed-assets/${id}/change-assignee`, data,
  )
}

/** 导出固定资产 Excel（遵循页面筛选） */
export function exportFixedAssets(params?: Record<string, string>) {
  return request.get<Blob>('/api/assets/fixed-assets/export', { params, responseType: 'blob' })
}

/** 上传/覆盖物品图片（edit_instances 权限；JPG/PNG/WebP ≤10MB） */
export function uploadFixedAssetImage(id: string, file: File) {
  const formData = new FormData()
  formData.append('image', file)
  return request.post<FixedAsset>(`/api/assets/fixed-assets/${id}/image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 删除物品图片（edit_instances 权限） */
export function deleteFixedAssetImage(id: string) {
  return request.delete<FixedAsset>(`/api/assets/fixed-assets/${id}/image`)
}

/** 实例批量维护（白名单：供应商/规格 个体覆盖 / 备注 / 序列号一一对应） */
export function batchUpdateFixedAssets(data: {
  ids: string[]
  供应商?: string
  规格?: string
  采购日期?: string
  备注?: string
  序列号列表?: string[]
}) {
  return request.post<{ updated: number; results: string[]; errors: string[] }>(
    '/api/assets/fixed-assets/batch-update', data,
  )
}
