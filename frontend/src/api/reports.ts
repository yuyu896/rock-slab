/* 磐盘 - 报表 API */
import request from '@/utils/request'
import type { ReportOverview, BranchStat, StatusStat, CategoryStat } from '@/types'

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
  return request.get('/api/reports/transfers/', { params })
}
