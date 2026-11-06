import request from '@/utils/request'
import type { AxiosResponse } from 'axios'

function camelize(value: unknown, preserveObjectKeys = false): unknown {
  if (Array.isArray(value)) return value.map((item) => camelize(item))
  if (!value || typeof value !== 'object' || (typeof Blob !== 'undefined' && value instanceof Blob)) return value
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [
    preserveObjectKeys ? key : key.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase()),
    camelize(item, preserveObjectKeys || key === 'counts'),
  ]))
}

function camelizeResponse<T>(response: AxiosResponse<unknown>): AxiosResponse<T> {
  return { ...response, data: camelize(response.data) as T }
}

export interface ReconciliationSupplier {
  id: string
  name: string
}

export interface ReconciliationTask {
  id: string
  supplierId: string
  supplierName: string
  period: string
  status: 'draft' | 'archived'
  currentVersion: number | null
  rowCount: number
  comparisonCount?: number
  pendingCount?: number
  scopeDiagnostics?: {
    excludedCount: number
    unknownSupplierCount: number
    unknownSupplierSerials?: string[]
    unknownSupplierSerialCount?: number
    foreignSupplierSerials?: string[]
    foreignSupplierSerialCount?: number
  }
  totalAmount: string
  counts: Record<string, number>
  branchTotals: Array<{
    branchId: string
    branchName: string
    rowCount: number
    monthlyRent: string
    monthAmount: string
  }>
  createdAt: string
  uploadedAt: string | null
  uploadedBy: string | null
  archivedAt: string | null
}

export interface ReconciliationUnresolvedSummary {
  totalCount: number
  groups: Array<{
    supplierId: string
    supplierName: string
    firstPeriod: string
    count: number
  }>
}

export interface ReconciliationImportPreview {
  supplierId: string
  supplierName: string
  period: string
  branchCount: number
  orderCount: number
  rowCount: number
  totalAmount: string
  branchTotals: Array<{
    branchId: string
    branchName: string
    rowCount: number
    monthAmount: string
  }>
  calculationWarnings: Array<{
    row: number
    uploadedBillingDays: number | null
    calculatedBillingDays: number
    uploadedMonthAmount: string | null
    calculatedMonthAmount: string
  }>
}

export interface ReconciliationIssue {
  id: string
  firstPeriod: string
  lastPeriod: string
}

export interface ReconciliationComparison {
  id: string
  resultType: string
  serial: string
  normalizedSerial: string
  orderNumber: string
  supplierBranch: string
  supplierBranchId: string | null
  systemBranch: string
  systemBranchId: string | null
  internalCode: string
  systemStatus: string
  itemCode: string
  itemName: string
  leaseStartDate: string | null
  accountingDate: string | null
  billingDays: number | null
  monthlyRent: string | null
  monthAmount: string | null
  uploadedBillingDays: number | null
  uploadedMonthAmount: string | null
  billingStatus: 'billable' | 'not_started' | null
  issue: ReconciliationIssue | null
}

export interface ReconciliationTaskDetail extends ReconciliationTask {
  comparisons: ReconciliationComparison[]
  comparisonTotal?: number
  comparisonPage?: number
  comparisonPageSize?: number
  branchOptions?: Array<{ value: string; label: string }>
  versions: Array<{
    id: string
    versionNumber: number
    uploadedBy: string
    uploadedAt: string
    rowCount: number
    fileName: string
    calculationWarnings: Array<{
      row: number
      uploadedBillingDays: number | null
      calculatedBillingDays: number
      uploadedMonthAmount: string | null
      calculatedMonthAmount: string
    }>
  }>
  unresolvedIssues: Array<{ issueType: string; serial: string; id: string; firstPeriod: string; lastPeriod: string }>
}

export interface ReconciliationTaskListParams {
  supplier?: string
  period?: string
  page?: number
  pageSize?: number
}

export interface ReconciliationTaskListResponse {
  suppliers: ReconciliationSupplier[]
  results: ReconciliationTask[]
  unresolvedSummary: ReconciliationUnresolvedSummary
  count?: number
  page?: number
  pageSize?: number
  periods?: string[]
}

export interface ReconciliationTaskDetailParams {
  result?: string
  branch?: string
  serial?: string
  page?: number
  pageSize?: number
}

export function getReconciliationTasks(params: ReconciliationTaskListParams = {}) {
  return request.get<unknown>('/api/reconciliation/tasks', { params })
    .then((response) => camelizeResponse<ReconciliationTaskListResponse>(response))
}

export function previewReconciliationOrder(supplier: string, period: string, file: File) {
  const form = new FormData()
  form.append('supplier', supplier)
  form.append('period', period)
  form.append('file', file)
  return request.post<unknown>('/api/reconciliation/tasks/preview', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((response) => camelizeResponse<ReconciliationImportPreview>(response))
}

export function importReconciliationOrder(supplier: string, period: string, file: File) {
  const form = new FormData()
  form.append('supplier', supplier)
  form.append('period', period)
  form.append('file', file)
  return request.post<unknown>('/api/reconciliation/tasks/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((response) => camelizeResponse<ReconciliationTask>(response))
}

export function getReconciliationTask(id: string, params: ReconciliationTaskDetailParams = {}) {
  return request.get<unknown>(`/api/reconciliation/tasks/${id}`, { params })
    .then((response) => camelizeResponse<ReconciliationTaskDetail>(response))
}

export function archiveReconciliationTask(id: string) {
  return request.post<unknown>(`/api/reconciliation/tasks/${id}/archive`)
    .then((response) => camelizeResponse<ReconciliationTask>(response))
}

export interface BranchSummaryItem {
  branchId: string
  branchName: string
  orderCount: number
  matchedCount: number
  diffCount: number
  monthAmount: string
}

export function getBranchSummary(taskId: string) {
  return request.get<unknown>(`/api/reconciliation/tasks/${taskId}/branch-summary`)
    .then((response) => camelizeResponse<BranchSummaryItem[]>(response))
}

export function rematchTask(taskId: string) {
  return request.post<unknown>(`/api/reconciliation/tasks/${taskId}/rematch`)
    .then((response) => camelizeResponse<{ version: number }>(response))
}

export function exportReconciliationTask(id: string) {
  return request.get<Blob>('/api/reconciliation/export', {
    params: { task: id }, responseType: 'blob',
  })
}

export function exportReconciliationDifferences(id: string) {
  return request.get<Blob>('/api/reconciliation/export', {
    params: { task: id, type: 'differences' }, responseType: 'blob',
  })
}

export interface ReconciliationPaymentRow {
  serial: string | null
  internalCode: string
  resultType: string
  leaseStartDate: string | null
  accountingDate: string | null
  billingDays: number | null
  monthlyRent: string | null
  monthAmount: string | null
}

export interface ReconciliationPaymentBranch {
  branchId: string
  branchName: string
  confirmedAmount: string
  pendingAmount: string
  totalAmount: string
  diffCount: number
  rows: ReconciliationPaymentRow[]
}

export interface ReconciliationPaymentSummary {
  confirmedAmount: string
  pendingAmount: string
  totalAmount: string
  canArchive: boolean
  branches: ReconciliationPaymentBranch[]
}

export function getPaymentSummary(taskId: string) {
  return request.get<unknown>(`/api/reconciliation/tasks/${taskId}/payment`)
    .then((response) => camelizeResponse<ReconciliationPaymentSummary>(response))
}

export function exportPayment(taskId: string) {
  return request.get<Blob>('/api/reconciliation/export', {
    params: { task: taskId, type: 'payment' }, responseType: 'blob',
  })
}
