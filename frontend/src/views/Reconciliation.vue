<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, Download, Edit, Refresh, Upload } from '@element-plus/icons-vue'
import {
  archiveReconciliationTask,
  exportReconciliationDifferences,
  exportReconciliationTask,
  getReconciliationIssueHistory,
  getReconciliationTask,
  getReconciliationTasks,
  importReconciliationOrder,
  previewReconciliationOrder,
  updateReconciliationIssue,
  type ReconciliationComparison,
  type ReconciliationImportPreview,
  type ReconciliationIssue,
  type ReconciliationSupplier,
  type ReconciliationTask,
  type ReconciliationTaskDetail,
  type ReconciliationUnresolvedSummary,
} from '@/api/reconciliation'
import { handleApiError } from '@/utils/request'
import { generateReconciliationTemplate } from '@/utils/importTemplate'
import BasePagination from '@/components/BasePagination.vue'
import { useUserStore } from '@/store/user'

const suppliers = ref<ReconciliationSupplier[]>([])
const userStore = useUserStore()
const canViewReconciliation = computed(() => userStore.can('view_reconciliation'))
const canManageReconciliation = computed(() => userStore.can('manage_reconciliation'))
const canImportReconciliation = computed(() => canManageReconciliation.value && userStore.can('view_suppliers'))
const tasks = ref<ReconciliationTask[]>([])
const unresolvedSummary = ref<ReconciliationUnresolvedSummary>({ totalCount: 0, groups: [] })
const task = ref<ReconciliationTaskDetail | null>(null)
const loading = ref(false)
const uploading = ref(false)
const listLoadError = ref('')
const importDialogOpen = ref(false)
const importModalElement = ref<HTMLElement | null>(null)
const importTriggerElement = ref<HTMLElement | null>(null)
const importError = ref('')
const importRowErrors = ref<Array<{ row?: number; field?: string; message?: string }>>([])
const importPreview = ref<ReconciliationImportPreview | null>(null)
const previewing = ref(false)
const selectedSupplier = ref('')
const selectedPeriod = ref(currentPeriod())
const selectedFile = ref<File | null>(null)
const supplierFilter = ref('all')
const periodFilter = ref('all')
const resultFilter = ref('pending')
const serialFilter = ref('')
const branchFilter = ref('all')
const issueDialog = ref(false)
const activeIssue = ref<ReconciliationIssue | null>(null)
const issueConclusion = ref('')
const issueNote = ref('')
const issueSaving = ref(false)
const issueHistory = ref<Array<Record<string, string>>>([])
const listPage = ref(1)
const listPageSize = ref(20)
const listTotal = ref(0)
const listPeriods = ref<string[]>([])
const listServerMode = ref(false)
const detailPage = ref(1)
const detailPageSize = ref(50)
const detailTotal = ref(0)
const detailServerMode = ref(false)
const importTargetTaskOverride = ref<ReconciliationTask | null>(null)
const suppressListFilterReload = ref(false)
const suppressSerialReload = ref(false)
let serialSearchTimer: ReturnType<typeof setTimeout> | undefined
let listRequestSequence = 0
let detailRequestSequence = 0

const resultLabels: Record<string, string> = {
  matched: '匹配',
  branch_mismatch: '分公司不一致',
  order_only: '仅订单有',
  system_only: '仅系统有',
  system_duplicate: '系统序列号重复',
  system_missing_serial: '系统缺少序列号',
}
function currentPeriod() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? value : []
}

function taskDifferenceCount(item: Pick<ReconciliationTask, 'counts'>) {
  return Object.entries(item.counts || {}).reduce((total, [type, count]) => total + (type === 'matched' ? 0 : count), 0)
}

function taskResultCount(item: Pick<ReconciliationTask, 'counts'> | null | undefined, type: string) {
  if (!item) return 0
  const camelType = type.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase())
  return item.counts?.[type] ?? item.counts?.[camelType] ?? 0
}

const periodOptions = computed(() => listPeriods.value.length ? listPeriods.value : [...new Set(tasks.value.map((item) => item.period))].sort((a, b) => b.localeCompare(a)))
const filteredTasks = computed(() => listServerMode.value ? tasks.value : tasks.value.filter((item) =>
  (supplierFilter.value === 'all' || item.supplierId === supplierFilter.value)
  && (periodFilter.value === 'all' || item.period === periodFilter.value),
))
const importTargetTask = computed(() => importTargetTaskOverride.value || tasks.value.find((item) =>
  item.supplierId === selectedSupplier.value && item.period === selectedPeriod.value,
))

const resultFilterOptions = computed(() => {
  const counts = task.value?.counts || {}
  return [
    { value: 'pending', label: `待填写结论（${pendingConclusionCount.value}）` },
    { value: 'differences', label: `全部差异（${task.value ? taskDifferenceCount(task.value) : 0}）` },
    { value: 'matched', label: `匹配记录（${counts.matched || 0}）` },
    { value: 'all', label: `全部结果（${detailTotal.value || task.value?.comparisonCount || 0}）` },
  ]
})
const pendingConclusionCount = computed(() => task.value?.pendingCount ?? asArray<ReconciliationComparison>(task.value?.comparisons)
  .filter((row) => row.resultType !== 'matched' && row.issue?.status !== 'closed' && !row.issue?.conclusion?.trim()).length)

async function loadTasks() {
  const requestSequence = ++listRequestSequence
  loading.value = true
  listLoadError.value = ''
  try {
    const { data } = await getReconciliationTasks({
      supplier: supplierFilter.value === 'all' ? undefined : supplierFilter.value,
      period: periodFilter.value === 'all' ? undefined : periodFilter.value,
      page: listPage.value,
      pageSize: listPageSize.value,
    })
    if (requestSequence !== listRequestSequence) return
    suppliers.value = asArray<ReconciliationSupplier>(data.suppliers)
    tasks.value = asArray<ReconciliationTask>(data.results)
    unresolvedSummary.value = data.unresolvedSummary || { totalCount: 0, groups: [] }
    listServerMode.value = Object.prototype.hasOwnProperty.call(data, 'count')
    listTotal.value = typeof data.count === 'number' ? data.count : tasks.value.length
    listPeriods.value = asArray<string>(data.periods)
  } catch (error) {
    if (requestSequence !== listRequestSequence) return
    listLoadError.value = handleApiError(error)
  } finally {
    if (requestSequence === listRequestSequence) loading.value = false
  }
}

async function loadTaskDetails(id: string) {
  const requestSequence = ++detailRequestSequence
  loading.value = true
  try {
    const { data } = await getReconciliationTask(id, {
      result: resultFilter.value,
      branch: branchFilter.value === 'all' ? undefined : branchFilter.value,
      serial: serialFilter.value.trim() || undefined,
      page: detailPage.value,
      pageSize: detailPageSize.value,
    })
    if (requestSequence !== detailRequestSequence) return
    task.value = data
    detailServerMode.value = Object.prototype.hasOwnProperty.call(data, 'comparisonTotal')
    detailTotal.value = typeof data.comparisonTotal === 'number'
      ? data.comparisonTotal
      : asArray<ReconciliationComparison>(data.comparisons).length
    if (typeof data.comparisonPage === 'number') detailPage.value = data.comparisonPage
    if (typeof data.comparisonPageSize === 'number') detailPageSize.value = data.comparisonPageSize
  } catch (error) {
    if (requestSequence !== detailRequestSequence) return
    ElMessage.error(handleApiError(error))
  } finally {
    if (requestSequence === detailRequestSequence) loading.value = false
  }
}

async function openTask(row: ReconciliationTask) {
  resultFilter.value = 'pending'
  if (serialFilter.value) suppressSerialReload.value = true
  serialFilter.value = ''
  branchFilter.value = 'all'
  detailPage.value = 1
  await loadTaskDetails(row.id)
}

function handleListPaginationChange(page: number, pageSize: number) {
  listPage.value = page
  listPageSize.value = pageSize
  if (listServerMode.value) void loadTasks()
}

function handleListFilterChange() {
  if (task.value) return
  if (suppressListFilterReload.value) {
    suppressListFilterReload.value = false
    return
  }
  listPage.value = 1
  if (listServerMode.value) void loadTasks()
}

function handleDetailPaginationChange(page: number, pageSize: number) {
  detailPage.value = page
  detailPageSize.value = pageSize
  if (task.value && detailServerMode.value) void loadTaskDetails(task.value.id)
}

function handleDetailFilterChange() {
  detailPage.value = 1
  if (task.value && detailServerMode.value) void loadTaskDetails(task.value.id)
}

function changeResultFilter(value: string) {
  resultFilter.value = value
  handleDetailFilterChange()
}

watch([supplierFilter, periodFilter], handleListFilterChange)
watch([selectedSupplier, selectedPeriod], () => {
  importTargetTaskOverride.value = null
})
watch(serialFilter, () => {
  if (!task.value || !detailServerMode.value) {
    suppressSerialReload.value = false
    return
  }
  if (suppressSerialReload.value) {
    suppressSerialReload.value = false
    if (serialSearchTimer) clearTimeout(serialSearchTimer)
    return
  }
  if (serialSearchTimer) clearTimeout(serialSearchTimer)
  serialSearchTimer = setTimeout(() => {
    detailPage.value = 1
    if (task.value) void loadTaskDetails(task.value.id)
  }, 250)
})

async function openUnresolvedGroup(group: ReconciliationUnresolvedSummary['groups'][number]) {
  suppressListFilterReload.value = listServerMode.value
  supplierFilter.value = group.supplierId
  periodFilter.value = group.firstPeriod
  if (listServerMode.value) await loadTasks()
  suppressListFilterReload.value = false
  const firstTask = tasks.value.find((item) => item.supplierId === group.supplierId && item.period === group.firstPeriod)
  if (firstTask) void openTask(firstTask)
}

function returnToList() {
  detailRequestSequence += 1
  task.value = null
  detailServerMode.value = false
  void loadTasks()
}

function openImportDialog(event?: Event) {
  if (!canImportReconciliation.value || !suppliers.value.length) return
  const target = event?.target
  importTriggerElement.value = (target instanceof Element ? target.closest('button') : null)
    || (document.activeElement instanceof HTMLElement ? document.activeElement : null)
  resetImportPreview()
  selectedFile.value = null
  const fileInput = document.querySelector<HTMLInputElement>('#reconciliation-file')
  if (fileInput) fileInput.value = ''
  importDialogOpen.value = true
  void nextTick(() => importModalElement.value?.querySelector<HTMLElement>('.modal-close')?.focus())
}

function restoreImportTriggerFocus() {
  void nextTick(() => {
    if (importTriggerElement.value?.isConnected) importTriggerElement.value.focus()
  })
}

function closeImportDialog() {
  if (previewing.value || uploading.value) return
  importDialogOpen.value = false
  restoreImportTriggerFocus()
}

function trapImportFocus(event: KeyboardEvent) {
  const focusable = Array.from(importModalElement.value?.querySelectorAll<HTMLElement>(
    'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
  ) || []).filter((element) => element.getAttribute('aria-hidden') !== 'true')
  const first = focusable[0]
  const last = focusable[focusable.length - 1]

  if (!first || !last) {
    event.preventDefault()
    return
  }
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  } else if (!importModalElement.value?.contains(document.activeElement)) {
    event.preventDefault()
    first.focus()
  }
}

function resetImportPreview() {
  importPreview.value = null
  importError.value = ''
  importRowErrors.value = []
}

function chooseFile(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] || null
  resetImportPreview()
}

function downloadOrderTemplate() {
  void generateReconciliationTemplate()
}

function setImportError(error: unknown) {
  const data = (error as { response?: { data?: { errors?: Array<{ row?: number; field?: string; message?: string }> } } })?.response?.data
  importRowErrors.value = data?.errors || []
  importError.value = importRowErrors.value.length
    ? '订单未通过完整校验，请按以下提示修正后重新预览。'
    : handleApiError(error)
}

async function resolveImportTargetTask() {
  if (!listServerMode.value || !selectedSupplier.value || !selectedPeriod.value) return importTargetTask.value
  if (importTargetTaskOverride.value) return importTargetTaskOverride.value
  try {
    const { data } = await getReconciliationTasks({
      supplier: selectedSupplier.value,
      period: selectedPeriod.value,
      page: 1,
      pageSize: 1,
    })
    importTargetTaskOverride.value = asArray<ReconciliationTask>(data.results).find((item) =>
      item.supplierId === selectedSupplier.value && item.period === selectedPeriod.value,
    ) || null
  } catch {
    importTargetTaskOverride.value = null
  }
  return importTargetTaskOverride.value
}

async function previewImport() {
  if (!canImportReconciliation.value || !suppliers.value.length) return
  resetImportPreview()
  if (!selectedSupplier.value || !selectedPeriod.value || !selectedFile.value) {
    importError.value = '请选择供应商、月份和订单文件。'
    return
  }
  const targetTask = await resolveImportTargetTask()
  if (targetTask?.status === 'archived') {
    importError.value = '该供应商月份任务已归档，不能覆盖。'
    return
  }
  previewing.value = true
  try {
    const { data } = await previewReconciliationOrder(selectedSupplier.value, selectedPeriod.value, selectedFile.value)
    importPreview.value = data
  } catch (error) {
    setImportError(error)
  } finally {
    previewing.value = false
  }
}

async function submitImport() {
  if (!canImportReconciliation.value || !suppliers.value.length) return
  if (!importPreview.value || !selectedSupplier.value || !selectedPeriod.value || !selectedFile.value) return
  importError.value = ''
  importRowErrors.value = []
  const targetTask = await resolveImportTargetTask()
  if (targetTask?.status === 'archived') {
    importError.value = '该供应商月份任务已归档，不能覆盖。'
    resetImportPreview()
    return
  }
  uploading.value = true
  try {
    const { data } = await importReconciliationOrder(selectedSupplier.value, selectedPeriod.value, selectedFile.value)
    selectedFile.value = null
    const fileInput = document.querySelector<HTMLInputElement>('#reconciliation-file')
    if (fileInput) fileInput.value = ''
    ElMessage.success(`订单已导入，当前版本 ${data.currentVersion}`)
    importDialogOpen.value = false
    restoreImportTriggerFocus()
    await loadTasks()
    await openTask(data)
  } catch (error) {
    setImportError(error)
    importPreview.value = null
  } finally {
    uploading.value = false
  }
}

const visibleComparisons = computed(() => {
  const rows = asArray<ReconciliationComparison>(task.value?.comparisons)
  if (detailServerMode.value) {
    return [...rows].sort((a, b) => comparisonBranchName(a).localeCompare(comparisonBranchName(b), 'zh-CN'))
  }
  return rows.filter((row) => {
    if (resultFilter.value === 'pending' && (row.resultType === 'matched' || row.issue?.status === 'closed' || row.issue?.conclusion?.trim())) return false
    if (resultFilter.value === 'differences' && row.resultType === 'matched') return false
    if (resultFilter.value === 'matched' && row.resultType !== 'matched') return false
    if (!['all', 'differences', 'pending', 'matched'].includes(resultFilter.value) && row.resultType !== resultFilter.value) return false
    const serial = `${row.serial || ''} ${row.normalizedSerial || ''}`.toLocaleLowerCase()
    if (serialFilter.value && !serial.includes(serialFilter.value.trim().toLocaleLowerCase())) return false
    if (branchFilter.value !== 'all' && row.supplierBranchId !== branchFilter.value && row.systemBranchId !== branchFilter.value) return false
    return true
  }).sort((a, b) => comparisonBranchName(a).localeCompare(comparisonBranchName(b), 'zh-CN'))
})

function comparisonBranchName(row: ReconciliationComparison) {
  return row.supplierBranch || row.systemBranch || '未归属分公司'
}

const comparisonGroups = computed(() => {
  const groups = new Map<string, { key: string; name: string; rows: ReconciliationComparison[]; matched: ReconciliationComparison[]; differences: ReconciliationComparison[]; amountCents: number }>()
  for (const row of visibleComparisons.value) {
    const key = row.supplierBranchId || row.systemBranchId || 'unassigned'
    const group = groups.get(key) || { key, name: comparisonBranchName(row), rows: [], matched: [], differences: [], amountCents: 0 }
    group.rows.push(row)
    group.amountCents += Math.round(Number(row.monthAmount || 0) * 100)
    if (row.resultType === 'matched') group.matched.push(row)
    else group.differences.push(row)
    groups.set(key, group)
  }
  return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
})

const branchOptions = computed(() => {
  if (task.value?.branchOptions?.length) return task.value.branchOptions
  const values = new Map<string, string>()
  for (const row of asArray<ReconciliationComparison>(task.value?.comparisons)) {
    if (row.supplierBranchId && row.supplierBranch) values.set(row.supplierBranchId, row.supplierBranch)
    if (row.systemBranchId && row.systemBranch) values.set(row.systemBranchId, row.systemBranch)
  }
  return [...values].map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
})

function resultCount(type: string) {
  if (type === 'all') return detailTotal.value || task.value?.comparisonCount || 0
  if (type === 'differences') return task.value ? taskDifferenceCount(task.value) : 0
  if (type === 'pending') return pendingConclusionCount.value
  return taskResultCount(task.value, type)
}

function clearDetailFilters() {
  resultFilter.value = 'pending'
  if (serialFilter.value) suppressSerialReload.value = true
  serialFilter.value = ''
  branchFilter.value = 'all'
  handleDetailFilterChange()
}

function resultTagType(type: string) {
  if (type === 'matched') return 'success'
  if (type === 'order_only' || type === 'system_duplicate') return 'danger'
  if (type === 'branch_mismatch' || type === 'system_only' || type === 'system_missing_serial') return 'warning'
  return 'info'
}

async function loadIssueHistory(issueId: string) {
  try {
    const { data } = await getReconciliationIssueHistory(issueId)
    issueHistory.value = data.history || []
  } catch {
    issueHistory.value = []
  }
}

function openIssue(row: ReconciliationComparison) {
  if (!canManageReconciliation.value || !row.issue) return
  activeIssue.value = row.issue
  issueConclusion.value = row.issue.conclusion || ''
  issueNote.value = row.issue.note || ''
  void loadIssueHistory(row.issue.id)
  issueDialog.value = true
}

function openIssueRecord(issue: ReconciliationIssue) {
  if (!canManageReconciliation.value) return
  activeIssue.value = issue
  issueConclusion.value = issue.conclusion || ''
  issueNote.value = issue.note || ''
  void loadIssueHistory(issue.id)
  issueDialog.value = true
}

async function saveIssue() {
  if (!canManageReconciliation.value || !activeIssue.value) return
  issueSaving.value = true
  try {
    await updateReconciliationIssue(activeIssue.value.id, {
      conclusion: issueConclusion.value,
      note: issueNote.value,
    })
    ElMessage.success('处理记录已保存')
    issueDialog.value = false
    if (task.value) await loadTaskDetails(task.value.id)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    issueSaving.value = false
  }
}

async function closeIssue(issue: ReconciliationIssue) {
  if (!canManageReconciliation.value) return
  try {
    await ElMessageBox.confirm('确认结案？结案后仍可在差异记录中追溯。', '结案确认', { type: 'warning' })
    await updateReconciliationIssue(issue.id, { status: 'closed' })
    ElMessage.success('差异已结案')
    if (task.value) await loadTaskDetails(task.value.id)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(handleApiError(error))
  }
}

async function archiveTask() {
  if (!canManageReconciliation.value || !task.value) return
  const currentPageDifferences = asArray<ReconciliationComparison>(task.value.comparisons)
    .filter((row) => row.resultType !== 'matched')
  const differenceCount = detailServerMode.value ? taskDifferenceCount(task.value) : currentPageDifferences.length
  const pendingCount = detailServerMode.value
    ? pendingConclusionCount.value
    : currentPageDifferences.filter((row) => !row.issue?.conclusion?.trim()).length
  const concludedCount = Math.max(0, differenceCount - pendingCount)
  const historicalCount = task.value.unresolvedIssues.length
  try {
    await ElMessageBox.confirm(
      `归档 ${task.value.period} · ${task.value.supplierName}？\n差异总数：${differenceCount} 条\n已有处理结论：${concludedCount} 条\n待填写结论：${pendingCount} 条\n历史未决事项：${historicalCount} 条，将继续跨期追踪。归档后不能覆盖本期订单。`,
      '完成并归档', { confirmButtonText: '确认归档', cancelButtonText: '继续处理', type: 'warning' },
    )
    await archiveReconciliationTask(task.value.id)
    ElMessage.success('对账任务已归档')
    await openTask(task.value)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(handleApiError(error))
  }
}

async function exportTask() {
  if (!canViewReconciliation.value || !task.value) return
  try {
    const { data } = await exportReconciliationTask(task.value.id)
    const url = URL.createObjectURL(data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `对账结果-${task.value.period}-${task.value.supplierName}.xlsx`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

async function exportDifferences() {
  if (!canViewReconciliation.value || !task.value) return
  try {
    const { data } = await exportReconciliationDifferences(task.value.id)
    const url = URL.createObjectURL(data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `对账差异-${task.value.period}-${task.value.supplierName}.xlsx`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

function formatMoney(value: string | null | undefined) {
  return value ? `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'
}

function formatDate(value: string | null | undefined) {
  return value || '—'
}

onMounted(loadTasks)
onBeforeUnmount(() => {
  if (serialSearchTimer) clearTimeout(serialSearchTimer)
})
</script>

<template>
  <div class="reconciliation-page page-fill">
    <div
      v-if="importDialogOpen"
      class="modal-overlay reconciliation-import-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reconciliation-import-title"
      @click.self="closeImportDialog"
      @keydown.esc.stop.prevent="closeImportDialog"
      @keydown.tab="trapImportFocus"
    >
      <div ref="importModalElement" class="modal-content reconciliation-import-modal">
        <div class="modal-header">
          <div class="modal-title-block">
            <h3 id="reconciliation-import-title">导入租赁订单</h3>
            <p>按供应商和月份上传订单，先预览后确认。</p>
          </div>
          <button class="modal-close" type="button" aria-label="关闭" :disabled="previewing || uploading" @click="closeImportDialog">&times;</button>
        </div>

        <div class="modal-body">
          <section class="import-step">
            <div class="import-step-header">
              <span class="import-step-num">1</span>
              <span class="import-step-title">选择对账范围</span>
            </div>
            <p class="import-step-desc">供应商和月份用于确定本次对账任务。</p>
            <div class="import-meta-grid">
              <div class="import-field">
                <span class="import-field-label">供应商</span>
                <el-select v-model="selectedSupplier" placeholder="选择供应商" filterable class="full-width" :disabled="previewing || uploading" @change="resetImportPreview">
                  <el-option v-for="supplier in suppliers" :key="supplier.id" :label="supplier.name" :value="supplier.id" />
                </el-select>
              </div>
              <div class="import-field">
                <span class="import-field-label">对账月份</span>
                <el-date-picker v-model="selectedPeriod" type="month" value-format="YYYY-MM" placeholder="选择月份" class="full-width" :disabled="previewing || uploading" @change="resetImportPreview" />
              </div>
            </div>
          </section>

          <section class="import-step">
            <div class="import-step-header">
              <span class="import-step-num">2</span>
              <span class="import-step-title">上传订单文件</span>
            </div>
            <p class="import-step-desc">每行填写一台设备，仅支持 .xlsx 文件。</p>
            <div class="import-file-actions">
              <button class="btn-secondary import-template-btn" type="button" @click="downloadOrderTemplate">
                <Download :size="16" />
                下载订单模板
              </button>
              <span>日期填写为 YYYY-MM-DD；计费天数和本月金额由系统计算。</span>
            </div>
            <label class="import-upload-area" :class="{ 'upload-loading': previewing || uploading, 'file-selected': selectedFile }">
              <input id="reconciliation-file" type="file" accept=".xlsx" class="import-file-input" :disabled="previewing || uploading" @change="chooseFile">
              <template v-if="previewing">
                <div class="import-spinner"></div>
                <span>正在解析...</span>
              </template>
              <template v-else-if="uploading">
                <div class="import-spinner"></div>
                <span>正在导入...</span>
              </template>
              <template v-else-if="selectedFile">
                <Upload :size="24" />
                <strong>{{ selectedFile.name }}</strong>
                <span class="import-upload-hint">文件已选择，可解析预览</span>
              </template>
              <template v-else>
                <Upload :size="24" />
                <span>点击选择 .xlsx 文件</span>
                <span class="import-upload-hint">选择文件后点击“解析并预览”</span>
              </template>
            </label>
          </section>

          <p class="scope-note">系统按指定电脑品目核对；分公司名称须与系统一致，任一行校验失败都会拒绝整份订单。</p>

          <section v-if="importPreview" class="import-step import-preview" aria-label="订单解析预览">
            <div class="import-step-header preview-step-header">
              <span class="import-step-num">3</span>
              <span class="import-step-title">解析预览</span>
              <span class="preview-context">{{ importPreview.supplierName }} · {{ importPreview.period }}</span>
            </div>
            <div v-if="importTargetTask" class="import-alert import-alert-warning" role="status">
              将创建第 {{ (importTargetTask.currentVersion || 0) + 1 }} 版并替换当前结果；旧版本仍可追溯。
            </div>
            <dl class="preview-metrics">
              <div><dt>分公司</dt><dd>{{ importPreview.branchCount }}</dd></div>
              <div><dt>订单</dt><dd>{{ importPreview.orderCount }}</dd></div>
              <div><dt>设备</dt><dd>{{ importPreview.rowCount }}</dd></div>
              <div><dt>本月应计</dt><dd>{{ formatMoney(importPreview.totalAmount) }}</dd></div>
            </dl>
            <div v-if="importPreview.branchTotals.length" class="preview-branches">
              <div v-for="branch in importPreview.branchTotals" :key="branch.branchId" class="preview-branch">
                <span>{{ branch.branchName }} · {{ branch.rowCount }} 台</span>
                <strong>{{ formatMoney(branch.monthAmount) }}</strong>
              </div>
            </div>
            <div v-if="importPreview.calculationWarnings.length" class="import-alert import-alert-warning" role="status">
              {{ importPreview.calculationWarnings.length }} 行上传的计费天数或金额与系统计算值不同，导入后以系统计算值为准。
            </div>
          </section>

          <div v-if="importError" class="import-alert import-alert-error" role="alert">
            <strong>{{ importError }}</strong>
            <ul v-if="importRowErrors.length" class="row-errors">
              <li v-for="(item, index) in importRowErrors" :key="index">
                第 {{ item.row || '?' }} 行{{ item.field ? `「${item.field}」` : '' }}：{{ item.message || '数据无效' }}
              </li>
            </ul>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" type="button" :disabled="previewing || uploading" @click="closeImportDialog">取消</button>
          <button v-if="importPreview" class="btn-secondary" type="button" :disabled="uploading" @click="resetImportPreview">
            <Refresh :size="16" />
            重新预览
          </button>
          <button v-if="!importPreview" class="btn-confirm" type="button" :disabled="uploading" :aria-busy="previewing" @click="previewImport">
            <Upload :size="16" />
            {{ previewing ? '解析中...' : '解析并预览' }}
          </button>
          <button v-else class="btn-confirm" type="button" :disabled="previewing" :aria-busy="uploading" @click="submitImport">
            <Check :size="16" />
            {{ uploading ? '导入中...' : (importTargetTask ? '替换订单并重新对账' : '确认导入并对账') }}
          </button>
        </div>
      </div>
    </div>

    <template v-if="!task">
      <header class="page-header">
        <div class="header-info">
          <h1 class="page-title">对账</h1>
          <p class="page-subtitle">电脑租赁月度任务</p>
        </div>
        <div class="header-actions">
          <el-button :icon="Refresh" :loading="loading" @click="loadTasks">刷新</el-button>
          <el-button v-if="canManageReconciliation" :icon="Download" @click="downloadOrderTemplate">下载订单模板</el-button>
          <el-button v-if="canImportReconciliation && suppliers.length" type="primary" :icon="Upload" @click="openImportDialog">导入订单</el-button>
        </div>
      </header>

      <section class="list-toolbar" aria-label="任务筛选">
        <el-select v-if="suppliers.length" v-model="supplierFilter" aria-label="按供应商筛选" placeholder="全部供应商" class="supplier-filter">
          <el-option label="全部供应商" value="all" />
          <el-option v-for="supplier in suppliers" :key="supplier.id" :label="supplier.name" :value="supplier.id" />
        </el-select>
        <el-select v-model="periodFilter" aria-label="按月份筛选" placeholder="全部月份" class="period-filter">
          <el-option label="全部月份" value="all" />
          <el-option v-for="period in periodOptions" :key="period" :label="period" :value="period" />
        </el-select>
        <el-button v-if="supplierFilter !== 'all' || periodFilter !== 'all'" text @click="supplierFilter = 'all'; periodFilter = 'all'">清除筛选</el-button>
        <span class="list-count">{{ listServerMode ? listTotal : filteredTasks.length }} 项任务</span>
      </section>

      <section v-if="unresolvedSummary.totalCount" class="unresolved-summary" aria-label="历史未决差异汇总">
        <div class="unresolved-summary-title"><strong>{{ unresolvedSummary.totalCount }} 条历史未决事项</strong><span>按首次发现月份汇总，已结案事项不计入</span></div>
        <button v-for="group in unresolvedSummary.groups" :key="`${group.supplierId}-${group.firstPeriod}`" type="button" class="unresolved-link" @click="openUnresolvedGroup(group)">
          {{ group.supplierName }} · {{ group.firstPeriod }} <strong>{{ group.count }}</strong>
        </button>
      </section>

      <el-alert v-if="listLoadError" type="error" :closable="false" show-icon :title="listLoadError">
        <el-button text type="primary" @click="loadTasks">重试</el-button>
      </el-alert>

      <div v-else-if="loading && !tasks.length" class="list-loading" role="status">正在加载对账任务…</div>
      <div v-else-if="filteredTasks.length" class="table-wrap">
        <el-table v-loading="loading" :data="filteredTasks" row-key="id" stripe class="task-table" @row-click="openTask">
          <el-table-column prop="period" label="期间" width="110" sortable />
          <el-table-column prop="supplierName" label="供应商" min-width="150" />
          <el-table-column label="订单设备" width="110" align="right">
            <template #default="scope">{{ scope.row.rowCount }}</template>
          </el-table-column>
          <el-table-column label="匹配" width="80" align="right"><template #default="scope">{{ taskResultCount(scope.row, 'matched') }}</template></el-table-column>
          <el-table-column label="仅系统有" width="95" align="right"><template #default="scope">{{ taskResultCount(scope.row, 'system_only') }}</template></el-table-column>
          <el-table-column label="仅订单有" width="95" align="right"><template #default="scope">{{ taskResultCount(scope.row, 'order_only') }}</template></el-table-column>
          <el-table-column label="其他差异" width="95" align="right"><template #default="scope">{{ Math.max(0, taskDifferenceCount(scope.row) - taskResultCount(scope.row, 'system_only') - taskResultCount(scope.row, 'order_only')) }}</template></el-table-column>
          <el-table-column label="本月应计" width="150" align="right">
            <template #default="scope">{{ formatMoney(scope.row.totalAmount) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'archived' ? 'success' : 'warning'" effect="plain">
                {{ scope.row.status === 'archived' ? '已归档' : '未归档' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="版本 / 导入人" min-width="160">
            <template #default="scope">v{{ scope.row.currentVersion }} · {{ scope.row.uploadedBy || '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click.stop="openTask(scope.row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
        <BasePagination
          v-if="listServerMode && listTotal > listPageSize"
          :total="listTotal"
          :current-page="listPage"
          :page-size="listPageSize"
          @change="handleListPaginationChange"
        />
      </div>
      <div v-else-if="!loading && (tasks.length || supplierFilter !== 'all' || periodFilter !== 'all')" class="empty-filter">
        <el-empty description="没有符合条件的对账任务" />
        <el-button text type="primary" @click="supplierFilter = 'all'; periodFilter = 'all'">清除筛选条件</el-button>
      </div>
      <div v-else-if="!loading" class="empty-start">
        <h2>还没有对账任务</h2>
        <p>导入供应商月度订单后，系统会按序列号核对设备并计算本月金额。</p>
        <el-button v-if="canImportReconciliation && suppliers.length" type="primary" :icon="Upload" @click="openImportDialog">导入第一份订单</el-button>
      </div>
    </template>

    <template v-else>
      <header class="page-header detail-header">
        <div class="header-info">
          <el-button text :icon="ArrowLeft" class="back-button" @click="returnToList">返回任务列表</el-button>
          <div class="task-title-line">
            <h1 class="page-title">{{ task.period }} · {{ task.supplierName }}</h1>
            <el-tag :type="task.status === 'archived' ? 'success' : 'warning'" effect="plain">
              {{ task.status === 'archived' ? '已归档' : '未归档' }}
            </el-tag>
          </div>
          <p class="page-subtitle">v{{ task.currentVersion }} · {{ task.uploadedBy || '—' }} · {{ task.rowCount }} 台订单设备</p>
        </div>
        <div class="header-actions">
          <div class="amount-summary"><span>本月应计金额</span><strong>{{ formatMoney(task.totalAmount) }}</strong></div>
          <el-button v-if="canViewReconciliation" :icon="Download" @click="exportTask">导出结果</el-button>
          <el-button v-if="canViewReconciliation" :icon="Download" @click="exportDifferences">导出差异</el-button>
          <el-button v-if="canManageReconciliation && task.status !== 'archived'" type="primary" :icon="Check" @click="archiveTask">完成并归档</el-button>
        </div>
      </header>

      <section class="comparison-section">
        <div class="comparison-toolbar">
          <nav class="result-filters" aria-label="核对结果筛选">
            <button
              v-for="item in resultFilterOptions"
              :key="item.value"
              type="button"
              class="result-filter"
              :class="{ active: resultFilter === item.value }"
              :aria-pressed="resultFilter === item.value"
              @click="changeResultFilter(item.value)"
            >{{ item.label }}</button>
          </nav>
          <div class="filters">
            <el-input v-model="serialFilter" aria-label="搜索序列号" placeholder="搜索序列号" clearable class="serial-search" />
            <el-select v-model="branchFilter" aria-label="按分公司筛选" class="branch-select" @change="handleDetailFilterChange">
              <el-option label="全部分公司" value="all" />
              <el-option v-for="branch in branchOptions" :key="branch.value" :label="branch.label" :value="branch.value" />
            </el-select>
            <el-button v-if="serialFilter || branchFilter !== 'all' || resultFilter !== 'pending'" text @click="clearDetailFilters">重置</el-button>
          </div>
        </div>

        <el-alert
          v-if="task.scopeDiagnostics && (task.scopeDiagnostics.excludedCount || task.scopeDiagnostics.unknownSupplierCount || task.scopeDiagnostics.foreignSupplierSerials?.length)"
          class="scope-diagnostics"
          type="warning"
          :closable="false"
          show-icon
          :title="`供应商范围诊断：排除 ${task.scopeDiagnostics.excludedCount} 个系统实例，未知供应商 ${task.scopeDiagnostics.unknownSupplierCount} 个，跨供应商序列号 ${task.scopeDiagnostics.foreignSupplierSerials?.length || 0} 个。`"
          :description="task.scopeDiagnostics.foreignSupplierSerials?.length ? `跨供应商序列号：${task.scopeDiagnostics.foreignSupplierSerials.join('、')}` : ''"
        />

      <el-alert
        v-if="task.versions.find((version) => version.versionNumber === task?.currentVersion)?.calculationWarnings.length"
        class="calculation-alert"
        type="warning"
        :closable="false"
        show-icon
        :title="`订单中有 ${task.versions.find((version) => version.versionNumber === task?.currentVersion)?.calculationWarnings.length} 行计费天数或本月金额与系统计算不一致，明细以系统重算值为准。可在导出结果中核对。`"
      />

        <section v-for="group in comparisonGroups" :key="group.key" class="branch-group">
          <header class="branch-group-heading">
            <h2>{{ group.name }}</h2>
            <span>{{ group.rows.length }} 台 · {{ group.differences.length }} 条差异 · {{ group.matched.length }} 条匹配 · 本月应计 {{ formatMoney((group.amountCents / 100).toFixed(2)) }}</span>
          </header>
        <el-table v-loading="loading" :data="group.differences" stripe table-layout="auto" class="comparison-table">
          <el-table-column label="核对结果" width="150" fixed="left">
            <template #default="scope"><el-tag :type="resultTagType(scope.row.resultType)" effect="plain">{{ resultLabels[scope.row.resultType] || scope.row.resultType }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="serial" label="序列号" min-width="180" show-overflow-tooltip />
          <el-table-column label="供应商订单">
            <el-table-column prop="orderNumber" label="订单号" min-width="140" show-overflow-tooltip />
            <el-table-column prop="supplierBranch" label="分公司" min-width="130" show-overflow-tooltip />
            <el-table-column prop="leaseStartDate" label="起租日期" width="115"><template #default="scope">{{ formatDate(scope.row.leaseStartDate) }}</template></el-table-column>
            <el-table-column prop="accountingDate" label="记账日期" width="115"><template #default="scope">{{ formatDate(scope.row.accountingDate) }}</template></el-table-column>
            <el-table-column prop="billingDays" label="计费天数" width="95" align="right" />
            <el-table-column label="计费状态" width="110"><template #default="scope"><el-tag v-if="scope.row.billingStatus === 'not_started'" type="info" effect="plain">本期未开始</el-tag><span v-else class="muted">正常</span></template></el-table-column>
            <el-table-column label="月租金" width="120" align="right"><template #default="scope">{{ formatMoney(scope.row.monthlyRent) }}</template></el-table-column>
            <el-table-column label="本月金额" width="125" align="right"><template #default="scope">{{ formatMoney(scope.row.monthAmount) }}</template></el-table-column>
          </el-table-column>
          <el-table-column label="系统资产">
            <el-table-column prop="systemBranch" label="分公司" min-width="130" show-overflow-tooltip />
            <el-table-column prop="internalCode" label="内部编号" min-width="155" show-overflow-tooltip />
            <el-table-column prop="itemCode" label="资产品目" width="125" show-overflow-tooltip />
            <el-table-column prop="systemStatus" label="状态" width="90" />
          </el-table-column>
          <el-table-column label="处理" width="100" fixed="right">
            <template #default="scope">
              <el-button v-if="canManageReconciliation && scope.row.issue" link type="primary" :icon="Edit" @click="openIssue(scope.row)">
                {{ scope.row.issue.status === 'closed' ? '查看' : '处理' }}
              </el-button>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>
        <details v-if="group.matched.length && (resultFilter === 'all' || resultFilter === 'matched')" class="matched-records">
          <summary>匹配记录 <span>{{ group.matched.length }} 条，默认收起</span></summary>
          <el-table :data="group.matched" stripe table-layout="auto" class="comparison-table matched-table">
            <el-table-column label="核对结果" width="120"><template #default><el-tag type="success" effect="plain">匹配</el-tag></template></el-table-column>
            <el-table-column prop="serial" label="序列号" min-width="180" show-overflow-tooltip />
            <el-table-column prop="orderNumber" label="订单号" min-width="140" show-overflow-tooltip />
            <el-table-column prop="supplierBranch" label="订单分公司" min-width="130" show-overflow-tooltip />
            <el-table-column prop="internalCode" label="内部编号" min-width="155" show-overflow-tooltip />
            <el-table-column prop="systemStatus" label="状态" width="90" />
          </el-table>
        </details>
        </section>
        <div v-if="!visibleComparisons.length" class="empty-filter">
          {{ resultFilter === 'pending' && resultCount('pending') === 0 ? '没有待填写结论的差异。' : '当前筛选下没有记录。' }}
          <el-button v-if="resultFilter === 'pending' && resultCount('pending') === 0" text type="primary" @click="changeResultFilter('differences')">查看全部差异</el-button>
        </div>
      </section>

      <BasePagination
        v-if="detailServerMode && detailTotal > detailPageSize"
        :total="detailTotal"
        :current-page="detailPage"
        :page-size="detailPageSize"
        @change="handleDetailPaginationChange"
      />

      <details class="supporting-info">
        <summary>辅助信息 <span>分公司汇总 {{ task.branchTotals.length }} · 历史未决 {{ task.unresolvedIssues.length }} · 导入版本 {{ task.versions.length }}</span></summary>
        <section class="supporting-section" aria-label="分公司金额汇总">
          <div class="section-heading"><h2>分公司汇总</h2></div>
          <el-table :data="task.branchTotals" size="small" stripe>
            <el-table-column prop="branchName" label="分公司" min-width="160" />
            <el-table-column prop="rowCount" label="设备数" width="100" align="right" />
            <el-table-column label="月租合计" width="150" align="right"><template #default="scope">{{ formatMoney(scope.row.monthlyRent) }}</template></el-table-column>
            <el-table-column label="本月应计" width="150" align="right"><template #default="scope">{{ formatMoney(scope.row.monthAmount) }}</template></el-table-column>
          </el-table>
        </section>

        <section v-if="task.unresolvedIssues.length" class="supporting-section">
          <div class="section-heading"><h2>历史未决事项</h2><span>未重现不代表自动结案</span></div>
          <el-table :data="task.unresolvedIssues" size="small" stripe>
            <el-table-column prop="serial" label="序列号" min-width="180" />
            <el-table-column label="类型" min-width="150"><template #default="scope">{{ resultLabels[scope.row.issueType] || scope.row.issueType }}</template></el-table-column>
            <el-table-column prop="firstPeriod" label="首次发现" width="120" />
            <el-table-column prop="lastPeriod" label="最近出现" width="120" />
            <el-table-column label="状态" width="130"><template #default="scope">{{ scope.row.status === 'not_recurred' ? '本期未重现' : '待处理' }}</template></el-table-column>
            <el-table-column prop="conclusion" label="处理结论" min-width="160" />
            <el-table-column v-if="canManageReconciliation" label="操作" width="100" fixed="right">
              <template #default="scope"><el-button link type="primary" @click="openIssueRecord(scope.row)">处理</el-button></template>
            </el-table-column>
          </el-table>
        </section>

        <section v-if="task.versions.length" class="supporting-section version-history">
          <div class="section-heading"><h2>上传版本记录</h2></div>
          <div v-for="version in task.versions" :key="version.id" class="version-row">
            <strong>v{{ version.versionNumber }}</strong><span>{{ version.fileName }}</span>
            <span>{{ version.uploadedBy }} · {{ new Date(version.uploadedAt).toLocaleString('zh-CN') }}</span>
            <el-tag v-if="version.versionNumber === task.currentVersion" type="success" effect="plain">当前版本</el-tag>
          </div>
        </section>
      </details>
    </template>

    <el-dialog v-model="issueDialog" title="差异处理" width="min(560px, calc(100vw - 32px))">
      <div v-if="activeIssue" class="issue-context">
        <el-tag :type="activeIssue.status === 'closed' ? 'success' : 'warning'" effect="plain">
          {{ activeIssue.status === 'closed' ? '已结案' : activeIssue.status === 'not_recurred' ? '本期未重现' : '待处理' }}
        </el-tag>
        <span>首次发现 {{ activeIssue.firstPeriod }} · 最近出现 {{ activeIssue.lastPeriod }}</span>
      </div>
      <el-form label-position="top">
        <el-form-item label="处理结论"><el-input v-model="issueConclusion" maxlength="100" placeholder="如：已补录 / 已向供应商确认" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="issueNote" type="textarea" :rows="4" maxlength="2000" /></el-form-item>
      </el-form>
      <div v-if="issueHistory.length" class="issue-history">
        <h3>处理记录</h3>
        <div v-for="(entry, index) in issueHistory" :key="index" class="history-entry">
          <strong>{{ entry.user }}</strong><time>{{ new Date(entry.createdAt).toLocaleString('zh-CN') }}</time>
          <span>{{ entry.oldConclusion || '未填写结论' }} → {{ entry.newConclusion || '未填写结论' }}</span>
          <span v-if="entry.newNote">{{ entry.newNote }}</span>
        </div>
      </div>
      <template #footer>
        <el-button v-if="canManageReconciliation && activeIssue && activeIssue.status !== 'closed'" @click="closeIssue(activeIssue)">确认结案</el-button>
        <el-button @click="issueDialog = false">取消</el-button>
        <el-button v-if="canManageReconciliation" type="primary" :loading="issueSaving" @click="saveIssue">保存记录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.reconciliation-page { width: 100%; max-width: 1400px; min-width: 0; margin: 0 auto; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 18px; }
.header-info { display: flex; min-width: 0; flex-direction: column; gap: 5px; }
.page-title { margin: 0; font-size: var(--text-xl); font-weight: 600; }
.page-subtitle { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.header-actions { display: flex; align-items: center; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.amount-summary { display: flex; flex-direction: column; gap: 3px; min-width: 150px; padding: 0 16px 0 0; margin-right: 4px; border-right: 1px solid var(--color-border-light); }
.amount-summary span { color: var(--color-text-secondary); font-size: var(--text-xs); }
.amount-summary strong { color: var(--color-primary-700); font-size: 20px; font-variant-numeric: tabular-nums; }
.task-title-line { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.list-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; min-height: 54px; padding: 10px 0; margin-bottom: 2px; border-top: 1px solid var(--color-border-light); border-bottom: 1px solid var(--color-border-light); }
.supplier-filter { width: 220px; }
.period-filter { width: 170px; }
.list-count { margin-left: auto; color: var(--color-text-secondary); font-size: var(--text-sm); font-variant-numeric: tabular-nums; }
.unresolved-summary { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 14px; padding: 12px 0; border-bottom: 1px solid var(--color-border-light); }
.unresolved-summary-title { display: flex; flex-direction: column; gap: 3px; min-width: 190px; margin-right: 4px; }
.unresolved-summary-title strong { color: var(--color-warning-700, #a16207); font-size: var(--text-sm); }
.unresolved-summary-title span { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.unresolved-link { display: inline-flex; align-items: center; gap: 8px; min-height: 34px; padding: 0 10px; border: 1px solid var(--color-border-light); border-radius: 4px; background: var(--color-background); color: var(--color-text-secondary); cursor: pointer; font: inherit; font-size: var(--text-sm); }
.unresolved-link:hover { border-color: var(--color-primary); color: var(--color-primary-700); }
.unresolved-link strong { font-variant-numeric: tabular-nums; }
.table-wrap { min-width: 0; }
.list-loading { min-height: 96px; padding: 36px 0; color: var(--color-text-secondary); text-align: center; }
.empty-start { max-width: 560px; padding: 64px 0; }
.empty-start h2 { margin: 0 0 8px; font-size: var(--text-md); }
.empty-start p { margin: 0 0 18px; color: var(--color-text-secondary); line-height: 1.5; }
.empty-filter { display: flex; min-height: 120px; align-items: center; justify-content: center; flex-wrap: wrap; gap: 6px; padding: 20px; color: var(--color-text-secondary); text-align: center; }
.modal-overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 16px; background: rgba(0, 0, 0, 0.5); }
.modal-content { display: flex; width: min(760px, calc(100vw - 32px)); max-height: min(90vh, 860px); flex-direction: column; overflow: hidden; border-radius: 16px; background: var(--color-bg-card); box-shadow: var(--shadow-xl); }
.modal-header { display: flex; flex: 0 0 auto; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.modal-title-block { min-width: 0; }
.modal-title-block h3 { margin: 0; color: var(--color-text-primary); font-size: var(--text-lg); font-weight: 600; }
.modal-title-block p { margin: 4px 0 0; color: var(--color-text-secondary); font-size: var(--text-xs); line-height: 1.5; }
.modal-close { display: flex; width: 32px; height: 32px; flex: 0 0 auto; align-items: center; justify-content: center; padding: 0; border: 0; border-radius: 6px; background: transparent; color: var(--color-text-tertiary); cursor: pointer; font-size: 20px; line-height: 1; }
.modal-close:hover { background: var(--color-bg-elevated); color: var(--color-text-primary); }
.modal-close:disabled { cursor: not-allowed; opacity: 0.5; }
.modal-body { min-height: 0; flex: 1 1 auto; overflow-y: auto; padding: 20px; }
.modal-footer { display: flex; flex: 0 0 auto; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 8px; padding: 12px 20px; border-top: 1px solid var(--color-border); }
.import-step { margin-bottom: 22px; }
.import-step:last-child { margin-bottom: 0; }
.import-step-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.import-step-num { display: inline-flex; width: 22px; height: 22px; flex: 0 0 auto; align-items: center; justify-content: center; border-radius: 50%; background: var(--color-primary-500); color: #fff; font-size: var(--text-xs); font-weight: 600; }
.import-step-title { color: var(--color-text-primary); font-size: var(--text-sm); font-weight: 600; }
.import-step-desc { margin: 0 0 10px; color: var(--color-text-tertiary); font-size: var(--text-xs); line-height: 1.5; }
.import-meta-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 16px; }
.import-field { display: grid; min-width: 0; gap: 6px; }
.import-field-label { color: var(--color-text-secondary); font-size: var(--text-xs); font-weight: 500; }
.full-width { width: 100%; }
.import-file-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; margin-bottom: 10px; }
.import-file-actions > span { color: var(--color-text-tertiary); font-size: var(--text-xs); line-height: 1.5; }
.import-template-btn svg { width: 16px; height: 16px; }
.import-upload-area { position: relative; display: flex; min-height: 124px; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 20px; border: 2px dashed var(--color-border); border-radius: 12px; background: var(--color-bg-page); color: var(--color-text-secondary); cursor: pointer; font-size: var(--text-sm); text-align: center; transition: border-color var(--transition-fast), background var(--transition-fast); }
.import-upload-area:hover { border-color: var(--color-primary-300); background: var(--color-primary-50); }
.import-upload-area.file-selected { border-color: var(--color-primary-300); background: var(--color-primary-50); }
.import-upload-area.upload-loading { cursor: not-allowed; opacity: 0.7; }
.import-upload-area svg { width: 24px; height: 24px; color: var(--color-primary-500); }
.import-upload-area strong { max-width: 100%; overflow: hidden; color: var(--color-text-primary); font-size: var(--text-sm); font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.import-upload-hint { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.import-file-input { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; clip-path: inset(50%); }
.import-upload-area:focus-within { outline: 2px solid var(--color-primary-500); outline-offset: 2px; }
.import-spinner { width: 20px; height: 20px; border: 2px solid var(--color-border); border-top-color: var(--color-primary-500); border-radius: 50%; animation: import-spin 0.8s linear infinite; }
@keyframes import-spin { to { transform: rotate(360deg); } }
.scope-note { margin: -4px 0 18px; color: var(--color-text-tertiary); font-size: var(--text-xs); line-height: 1.5; }
.import-preview { display: grid; gap: 12px; padding-top: 16px; border-top: 1px solid var(--color-border-light); }
.preview-step-header { flex-wrap: wrap; }
.preview-context { margin-left: auto; color: var(--color-text-tertiary); font-size: var(--text-xs); }
.preview-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 0; }
.preview-metrics > div { display: grid; min-width: 0; gap: 4px; padding: 10px 12px; border: 1px solid var(--color-border-light); border-radius: 8px; background: var(--color-bg-page); }
.preview-metrics dt { color: var(--color-text-secondary); font-size: var(--text-xs); }
.preview-metrics dd { margin: 0; color: var(--color-text-primary); font-size: var(--text-md); font-variant-numeric: tabular-nums; font-weight: 600; }
.preview-branches { display: grid; gap: 0; border-top: 1px solid var(--color-border-light); }
.preview-branch { display: flex; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--color-border-light); font-size: var(--text-sm); }
.preview-branch span { color: var(--color-text-secondary); }
.preview-branch strong { color: var(--color-text-primary); font-variant-numeric: tabular-nums; }
.import-alert { padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 6px; font-size: var(--text-xs); line-height: 1.6; }
.import-alert-warning { border-color: color-mix(in oklch, var(--color-warning) 55%, var(--color-border)); background: color-mix(in oklch, var(--color-warning) 12%, var(--color-bg-card)); color: var(--color-text-primary); }
.import-alert-error { border-color: color-mix(in oklch, var(--color-danger) 55%, var(--color-border)); background: color-mix(in oklch, var(--color-danger) 10%, var(--color-bg-card)); color: var(--color-danger); }
.row-errors { max-height: 180px; overflow: auto; padding-left: 20px; margin: 8px 0 0; line-height: 1.6; }
.btn-secondary, .btn-confirm, .btn-cancel { display: inline-flex; height: 40px; flex: 0 0 auto; align-items: center; justify-content: center; gap: 6px; padding: 0 16px; border-radius: 8px; cursor: pointer; font: inherit; font-size: var(--text-sm); font-weight: 500; white-space: nowrap; transition: border-color var(--transition-fast), background var(--transition-fast), color var(--transition-fast); }
.modal-footer svg { width: 16px; height: 16px; flex: 0 0 16px; }
.btn-secondary { border: 1px solid var(--color-border); background: var(--color-bg-card); color: var(--color-text-primary); }
.btn-secondary:hover:not(:disabled) { border-color: var(--color-primary-300); background: var(--color-primary-50); color: var(--color-primary-700); }
.btn-confirm { border: 1px solid var(--color-primary-500); background: var(--color-primary-500); color: #fff; }
.btn-confirm:hover:not(:disabled) { border-color: var(--color-primary-600); background: var(--color-primary-600); }
.btn-cancel { border: 1px solid var(--color-border); background: var(--color-bg-card); color: var(--color-text-primary); }
.btn-cancel:hover:not(:disabled) { border-color: var(--color-primary-300); color: var(--color-primary-700); }
.btn-secondary:disabled, .btn-confirm:disabled, .btn-cancel:disabled { cursor: not-allowed; opacity: 0.5; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; }
.detail-header { align-items: center; padding-bottom: 16px; border-bottom: 1px solid var(--color-border-light); }
.back-button { justify-content: flex-start; padding-left: 0; width: fit-content; }
.comparison-section { min-width: 0; margin: 0 0 22px; }
.branch-group { min-width: 0; margin-top: 14px; }
.branch-group-heading { display: flex; align-items: baseline; flex-wrap: wrap; gap: 8px 14px; padding: 10px 0; border-bottom: 1px solid var(--color-border-light); }
.branch-group-heading h2 { margin: 0; font-size: var(--text-md); font-weight: 600; }
.branch-group-heading span { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.matched-records { margin-top: 6px; border-top: 1px solid var(--color-border-light); }
.matched-records > summary { min-height: 40px; padding: 10px 0; color: var(--color-text-secondary); cursor: pointer; font-size: var(--text-sm); }
.matched-records > summary span { margin-left: 8px; color: var(--color-text-tertiary); font-size: var(--text-xs); }
.comparison-toolbar { display: grid; gap: 10px; margin: 14px 0 12px; }
.result-filters { display: flex; gap: 4px; overflow-x: auto; border-bottom: 1px solid var(--color-border-light); scrollbar-width: thin; }
.result-filter { position: relative; flex: 0 0 auto; min-height: 42px; padding: 0 12px; border: 0; background: transparent; color: var(--color-text-secondary); cursor: pointer; font: inherit; white-space: nowrap; }
.result-filter:hover { color: var(--color-text-primary); background: var(--color-background-soft); }
.result-filter.active { color: var(--color-primary-700); font-weight: 600; }
.result-filter.active::after { position: absolute; right: 10px; bottom: -1px; left: 10px; height: 2px; background: var(--color-primary); content: ''; }
.filters { display: grid; grid-template-columns: minmax(200px, 1fr) minmax(180px, 240px) auto; align-items: center; gap: 8px; }
.serial-search, .branch-select { width: 100%; }
.comparison-table { width: 100%; }
.comparison-table :deep(th.el-table__cell) {
  background-color: var(--color-bg-table-header);
  color: var(--color-text-secondary);
  font-weight: 600;
}
.muted { color: var(--color-text-tertiary); }
.calculation-alert { margin: 10px 0; }
.supporting-info { border-top: 1px solid var(--color-border-light); border-bottom: 1px solid var(--color-border-light); }
.supporting-info > summary { display: flex; min-height: 48px; align-items: center; justify-content: space-between; gap: 12px; color: var(--color-text-primary); cursor: pointer; font-size: var(--text-sm); font-weight: 600; list-style-position: inside; }
.supporting-info > summary span { color: var(--color-text-secondary); font-size: var(--text-xs); font-weight: 400; }
.supporting-section { padding: 8px 0 18px; }
.section-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 14px 0 8px; }
.section-heading h2 { margin: 0; font-size: var(--text-md); font-weight: 600; }
.section-heading > span { color: var(--color-text-tertiary); font-size: var(--text-sm); }
.version-history { margin: 0; border-top: 1px solid var(--color-border-light); }
.version-row { display: flex; min-height: 42px; align-items: center; flex-wrap: wrap; gap: 8px 16px; border-bottom: 1px solid var(--color-border-light); color: var(--color-text-secondary); font-size: var(--text-sm); }
.version-row strong { color: var(--color-text-primary); }
.version-row span:nth-child(2) { min-width: 180px; flex: 1; }
.issue-context { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; color: var(--color-text-secondary); font-size: var(--text-sm); }
.issue-history { border-top: 1px solid var(--color-border-light); padding-top: 14px; }
.issue-history h3 { margin: 0 0 8px; font-size: var(--text-sm); }
.history-entry { display: grid; grid-template-columns: auto 1fr; gap: 3px 12px; padding: 8px 0; border-bottom: 1px solid var(--color-border-light); color: var(--color-text-secondary); font-size: var(--text-xs); }
.history-entry time { text-align: right; }
.history-entry span { grid-column: 1 / -1; overflow-wrap: anywhere; }
@media (max-width: 760px) {
  .page-header, .detail-header { align-items: flex-start; flex-direction: column; }
  .header-actions { width: 100%; justify-content: flex-start; }
  .modal-overlay { align-items: flex-end; padding: 8px; }
  .modal-content { width: 100%; max-height: calc(100vh - 16px); border-radius: 12px; }
  .modal-header, .modal-body { padding-right: 16px; padding-left: 16px; }
  .modal-footer { padding-right: 16px; padding-left: 16px; }
  .import-meta-grid { grid-template-columns: 1fr; row-gap: 8px; }
  .preview-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .import-file-actions { align-items: flex-start; flex-direction: column; }
  .import-file-actions > span { width: 100%; }
  .preview-context { width: 100%; margin-left: 30px; }
  .amount-summary { min-width: 0; width: 100%; padding: 0 0 10px; margin: 0 0 2px; border-right: 0; border-bottom: 1px solid var(--color-border-light); }
  .list-toolbar { align-items: stretch; }
  .unresolved-summary { align-items: stretch; }
  .unresolved-summary-title { width: 100%; }
  .supplier-filter, .period-filter { width: 100%; }
  .list-count { width: 100%; margin-left: 0; }
  .filters { grid-template-columns: 1fr; }
  .result-filters { margin-right: -12px; padding-right: 12px; }
  .result-filter { min-height: 44px; padding: 0 10px; }
  .supporting-info > summary { align-items: flex-start; flex-direction: column; justify-content: center; padding: 10px 0; }
  .empty-start { padding: 42px 0; }
}
</style>
