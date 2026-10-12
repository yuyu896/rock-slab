import request from '@/utils/request'

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
  status: 'open' | 'not_recurred' | 'closed'
  conclusion: string
  note: string
  firstPeriod: string
  lastPeriod: string
  handledBy?: string | null
  handledAt?: string | null
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
  unresolvedIssues: Array<ReconciliationIssue & { issueType: string; serial: string }>
}

export function getReconciliationTasks() {
  return request.get<{
    suppliers: ReconciliationSupplier[]
    results: ReconciliationTask[]
    unresolvedSummary: ReconciliationUnresolvedSummary
  }>('/api/reconciliation/tasks')
}

export function previewReconciliationOrder(supplier: string, period: string, file: File) {
  const form = new FormData()
  form.append('supplier', supplier)
  form.append('period', period)
  form.append('file', file)
  return request.post<ReconciliationImportPreview>('/api/reconciliation/tasks/preview', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function importReconciliationOrder(supplier: string, period: string, file: File) {
  const form = new FormData()
  form.append('supplier', supplier)
  form.append('period', period)
  form.append('file', file)
  return request.post<ReconciliationTask>('/api/reconciliation/tasks/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getReconciliationTask(id: string) {
  return request.get<ReconciliationTaskDetail>(`/api/reconciliation/tasks/${id}`)
}

export function archiveReconciliationTask(id: string) {
  return request.post<ReconciliationTask>(`/api/reconciliation/tasks/${id}/archive`)
}

export function updateReconciliationIssue(id: string, data: {
  status?: ReconciliationIssue['status']
  conclusion?: string
  note?: string
}) {
  return request.patch<ReconciliationIssue>(`/api/reconciliation/issues/${id}`, data)
}

export function getReconciliationIssueHistory(id: string) {
  return request.get<{ history: Array<Record<string, string>> }>(`/api/reconciliation/issues/${id}`)
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
