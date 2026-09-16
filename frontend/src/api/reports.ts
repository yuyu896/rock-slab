/* 磐盘 - 报表 API */
import request from '@/utils/request'
import type {
  ReportOverview, BranchStat, StatusStat, CategoryStat, TransferReportRow, ConsumptionReport,
} from '@/types'

export function getOverview(params?: Record<string, string>) {
  return request.get<ReportOverview>('/api/reports/overview/', { params })
}

export function getByBranch(params?: Record<string, string>) {
  return request.get<BranchStat[]>('/api/reports/by-branch/', { params })
}

export function getByStatus(params?: Record<string, string>) {
  return request.get<StatusStat[]>('/api/reports/by-status/', { params })
}

export function getByCategory(params?: Record<string, string>) {
  return request.get<CategoryStat[]>('/api/reports/by-category/', { params })
}

export function getTransferReport(params?: Record<string, string>) {
  return request.get<TransferReportRow[]>('/api/reports/transfers/', { params })
}

/* 部门消耗统计：已生效领用单中消耗品行，部门×品目按月展开（数量口径） */
export function getConsumptionReport(params?: Record<string, string>) {
  return request.get<ConsumptionReport>('/api/reports/consumables/', { params })
}

/* 当前用户数据范围内的分公司列表（用于报表分公司筛选下拉） */
export function getReportBranches() {
  return request.get<{ id: string; name: string; code: string }[]>('/api/reports/branches/')
}

/** 变动按品目聚合：每品目一行，各类动作合计（生效单据，时间范围可选） */
export function getChangesByItem(params?: { dateRange?: string }) {
  return request.get<{ columns: string[]; results: { itemId: string; code: string; name: string; unit: string; cols: Record<string, number> }[] }>(
    '/api/reports/changes-by-item', { params },
  )
}
