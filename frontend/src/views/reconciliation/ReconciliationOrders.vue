<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Download, Refresh, Upload } from '@element-plus/icons-vue'
import {
  getReconciliationTasks,
  importReconciliationOrder,
  previewReconciliationOrder,
  type ReconciliationImportPreview,
  type ReconciliationSupplier,
  type ReconciliationTask,
} from '@/api/reconciliation'
import { handleApiError } from '@/utils/request'
import { generateReconciliationTemplate } from '@/utils/importTemplate'
import { useUserStore } from '@/store/user'
import { useReconciliationTask } from '@/composables/useReconciliationTask'
import ReconciliationTaskSelector from '@/components/ReconciliationTaskSelector.vue'

const router = useRouter()
const userStore = useUserStore()
const { currentTask, setTask } = useReconciliationTask()

const canManageReconciliation = computed(() => userStore.can('manage_reconciliation'))
const canImportReconciliation = computed(() => canManageReconciliation.value && userStore.can('view_suppliers'))

const suppliers = ref<ReconciliationSupplier[]>([])
const suppliersLoaded = ref(false)

const importDialogOpen = ref(false)
const importModalElement = ref<HTMLElement | null>(null)
const importTriggerElement = ref<HTMLElement | null>(null)
const importError = ref('')
const importRowErrors = ref<Array<{ row?: number; field?: string; message?: string }>>([])
const importPreview = ref<ReconciliationImportPreview | null>(null)
const previewing = ref(false)
const uploading = ref(false)
const selectedSupplier = ref('')
const selectedPeriod = ref(currentPeriod())
const selectedFile = ref<File | null>(null)
const importTargetTaskOverride = ref<ReconciliationTask | null>(null)

function currentPeriod() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? value : []
}

const importTargetTask = computed(() => importTargetTaskOverride.value)

watch([selectedSupplier, selectedPeriod], () => {
  importTargetTaskOverride.value = null
})

async function loadSuppliers() {
  try {
    const { data } = await getReconciliationTasks()
    suppliers.value = asArray<ReconciliationSupplier>(data.suppliers)
  } catch {
    // silently ignore
  } finally {
    suppliersLoaded.value = true
  }
}

function openImportDialog(event?: Event) {
  if (!canImportReconciliation.value) return
  if (!suppliersLoaded.value) {
    void loadSuppliers().then(() => {
      if (suppliers.value.length) _openImportDialogInternal(event)
    })
    return
  }
  _openImportDialogInternal(event)
}

function _openImportDialogInternal(event?: Event) {
  const target = event?.target
  importTriggerElement.value = (target instanceof Element ? target.closest('button') : null)
    || (document.activeElement instanceof HTMLElement ? document.activeElement : null)
  resetImportPreview()
  selectedFile.value = null
  const fileInput = document.querySelector<HTMLInputElement>('#reconciliation-orders-file')
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
  if (!first || !last) { event.preventDefault(); return }
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault(); last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault(); first.focus()
  } else if (!importModalElement.value?.contains(document.activeElement)) {
    event.preventDefault(); first.focus()
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
  if (!selectedSupplier.value || !selectedPeriod.value) return importTargetTaskOverride.value
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
  if (!canImportReconciliation.value) return
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
  if (!canImportReconciliation.value) return
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
    const fileInput = document.querySelector<HTMLInputElement>('#reconciliation-orders-file')
    if (fileInput) fileInput.value = ''
    ElMessage.success(`订单已导入，当前版本 ${data.currentVersion}`)
    importDialogOpen.value = false
    restoreImportTriggerFocus()
    await setTask(data.id)
    await router.push('/reconciliation/differences')
  } catch (error) {
    setImportError(error)
    importPreview.value = null
  } finally {
    uploading.value = false
  }
}

function formatMoney(value: string | null | undefined) {
  return value ? `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'
}

const versions = computed(() => currentTask.value?.versions ?? [])
</script>

<template>
  <div class="orders-page page-fill">
    <!-- Import Dialog -->
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
              <input id="reconciliation-orders-file" type="file" accept=".xlsx" class="import-file-input" :disabled="previewing || uploading" @change="chooseFile">
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
                <span class="import-upload-hint">选择文件后点击"解析并预览"</span>
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

    <!-- Task selector banner -->
    <ReconciliationTaskSelector />

    <!-- Page header -->
    <header class="page-header">
      <div class="header-info">
        <h1 class="page-title">供应商订单<template v-if="currentTask"> · {{ currentTask.supplierName }}</template></h1>
        <p class="page-subtitle">版本历史与订单导入</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="loadSuppliers">刷新</el-button>
        <el-button :icon="Download" @click="downloadOrderTemplate">下载订单模板</el-button>
        <el-button v-if="canImportReconciliation" type="primary" :icon="Upload" @click="openImportDialog">导入订单</el-button>
      </div>
    </header>

    <!-- Version history table -->
    <div v-if="currentTask" class="table-wrap">
      <el-table :data="versions" stripe class="version-table">
        <el-table-column label="版本号" width="90" align="center">
          <template #default="scope">v{{ scope.row.versionNumber }}</template>
        </el-table-column>
        <el-table-column prop="fileName" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="uploadedBy" label="导入人" width="130" />
        <el-table-column label="导入时间" width="175">
          <template #default="scope">{{ new Date(scope.row.uploadedAt).toLocaleString('zh-CN') }}</template>
        </el-table-column>
        <el-table-column label="设备数" width="90" align="right">
          <template #default="scope">{{ scope.row.rowCount }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="scope">
            <el-tag v-if="scope.row.versionNumber === currentTask?.currentVersion" type="success" effect="plain">当前版本</el-tag>
            <span v-else class="muted">历史版本</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!versions.length" class="empty-filter">暂无版本记录。</div>
    </div>
    <div v-else class="empty-start">
      <h2>请先选择对账任务</h2>
      <p>在顶部选择供应商和月份，或导入新的供应商订单以开始对账。</p>
      <el-button v-if="canImportReconciliation" type="primary" :icon="Upload" @click="openImportDialog">导入第一份订单</el-button>
    </div>
  </div>
</template>

<style scoped>
.orders-page { width: 100%; max-width: 1400px; min-width: 0; margin: 0 auto; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin: 18px 0; }
.header-info { display: flex; min-width: 0; flex-direction: column; gap: 5px; }
.page-title { margin: 0; font-size: var(--text-xl); font-weight: 600; }
.page-subtitle { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.header-actions { display: flex; align-items: center; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.table-wrap { min-width: 0; }
.version-table { width: 100%; }
.version-table :deep(th.el-table__cell) { background-color: var(--color-bg-table-header); color: var(--color-text-secondary); font-weight: 600; }
.muted { color: var(--color-text-tertiary); }
.empty-start { max-width: 560px; padding: 64px 0; }
.empty-start h2 { margin: 0 0 8px; font-size: var(--text-md); }
.empty-start p { margin: 0 0 18px; color: var(--color-text-secondary); line-height: 1.5; }
.empty-filter { display: flex; min-height: 120px; align-items: center; justify-content: center; gap: 6px; padding: 20px; color: var(--color-text-secondary); text-align: center; }
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
@media (max-width: 760px) {
  .page-header { align-items: flex-start; flex-direction: column; }
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
}
</style>
