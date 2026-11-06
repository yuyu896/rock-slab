<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  getBranchSummary,
  getReconciliationTask,
  rematchTask,
  updateReconciliationIssue,
  type BranchSummaryItem,
  type ReconciliationComparison,
} from '@/api/reconciliation'
import { useUserStore } from '@/store/user'
import { useReconciliationTask } from '@/composables/useReconciliationTask'
import ReconciliationTaskSelector from '@/components/ReconciliationTaskSelector.vue'

const userStore = useUserStore()
const { currentTaskId, setTask } = useReconciliationTask()

const canManageReconciliation = computed(() => userStore.can('manage_reconciliation'))

// Branch summary list
const branches = ref<BranchSummaryItem[]>([])
const loadingBranches = ref(false)
const rematching = ref(false)

// Expanded detail: branchId -> comparisons (lazily loaded on first expand)
const branchDetailCache = ref<Record<string, ReconciliationComparison[]>>({})
const loadingBranchId = ref<string | null>(null)

// Note editing state: issueId -> draft value
const noteEditing = ref<Record<string, string>>({})

const CONCLUSION_OPTIONS = [
  { value: '', label: '未填写' },
  { value: 'system_not_registered', label: '系统未登记已补录' },
  { value: 'serial_corrected', label: '序列号已纠正' },
  { value: 'supplier_overbilled', label: '供应商多报' },
  { value: 'supplier_underbilled', label: '供应商少报' },
  { value: 'period_adjustment', label: '期间调整' },
]

async function loadBranchSummary() {
  if (!currentTaskId.value) return
  loadingBranches.value = true
  try {
    const { data } = await getBranchSummary(currentTaskId.value)
    branches.value = Array.isArray(data) ? data : []
  } catch {
    ElMessage.error('加载分公司汇总失败')
  } finally {
    loadingBranches.value = false
  }
}

async function doRematch() {
  if (!currentTaskId.value || !canManageReconciliation.value || rematching.value) return
  rematching.value = true
  try {
    const { data } = await rematchTask(currentTaskId.value)
    ElMessage.success(`已重新对账，版本 ${data.version}`)
    branchDetailCache.value = {}
    await loadBranchSummary()
    await setTask(currentTaskId.value)
  } catch {
    ElMessage.error('重新对账失败')
  } finally {
    rematching.value = false
  }
}

async function loadComparisons(branchId: string) {
  if (!currentTaskId.value) return
  loadingBranchId.value = branchId
  try {
    const { data } = await getReconciliationTask(currentTaskId.value, { branch: branchId })
    const comps = data.comparisons ?? []
    branchDetailCache.value[branchId] = comps
    // Initialise note drafts
    for (const row of comps) {
      if (row.issue) noteEditing.value[row.issue.id] = row.issue.note ?? ''
    }
  } catch {
    ElMessage.error('加载明细失败')
  } finally {
    loadingBranchId.value = null
  }
}

function handleExpandChange(row: BranchSummaryItem, expandedRows: BranchSummaryItem[]) {
  const isExpanded = expandedRows.some((r) => r.branchId === row.branchId)
  if (isExpanded && !branchDetailCache.value[row.branchId]) {
    void loadComparisons(row.branchId)
  }
}

async function handleConclusionChange(comparison: ReconciliationComparison, value: string) {
  if (!comparison.issue) return
  try {
    await updateReconciliationIssue(comparison.issue.id, { conclusionType: value })
    await loadBranchSummary()
  } catch {
    ElMessage.error('保存结论失败')
  }
}

function onConclusionChange(comparison: ReconciliationComparison, val: unknown) {
  void handleConclusionChange(comparison, String(val))
}

async function handleNoteBlur(comparison: ReconciliationComparison) {
  if (!comparison.issue) return
  const note = noteEditing.value[comparison.issue.id] ?? ''
  try {
    await updateReconciliationIssue(comparison.issue.id, { note })
  } catch {
    ElMessage.error('保存备注失败')
  }
}

// KPI sums
const totalDiffCount = computed(() => branches.value.reduce((sum, b) => sum + b.diffCount, 0))
const totalPendingCount = computed(() => branches.value.reduce((sum, b) => sum + b.pendingCount, 0))
const totalOrderCount = computed(() => branches.value.reduce((sum, b) => sum + b.orderCount, 0))
const totalMatchedCount = computed(() => branches.value.reduce((sum, b) => sum + b.matchedCount, 0))
const matchRate = computed(() => {
  if (!totalOrderCount.value) return '—'
  return (totalMatchedCount.value / totalOrderCount.value * 100).toFixed(1) + '%'
})

function branchStatusIcon(branch: BranchSummaryItem) {
  if (branch.pendingCount > 0) return '🔴'
  if (branch.diffCount > 0) return '🟡'
  return '✅'
}

function formatMoney(value: string | null | undefined) {
  if (!value) return '—'
  return '¥' + Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function resultTypeLabel(resultType: string) {
  const map: Record<string, string> = {
    matched: '匹配',
    serial_diff: '序列号差异',
    amount_diff: '金额差异',
    supplier_only: '仅供应商',
    system_only: '仅系统',
  }
  return map[resultType] ?? resultType
}

function resultTagType(resultType: string): '' | 'success' | 'warning' | 'danger' {
  if (resultType === 'matched') return 'success'
  if (resultType === 'supplier_only' || resultType === 'system_only') return 'danger'
  if (resultType === 'serial_diff' || resultType === 'amount_diff') return 'warning'
  return ''
}

watch(() => currentTaskId.value, (newId) => {
  branchDetailCache.value = {}
  if (newId) {
    void loadBranchSummary()
  } else {
    branches.value = []
  }
}, { immediate: true })
</script>

<template>
  <div class="differences-page page-fill">
    <!-- Task selector banner -->
    <ReconciliationTaskSelector />

    <!-- Empty state when no task selected -->
    <div v-if="!currentTaskId" class="empty-start">
      <h2>请先在订单页选择任务</h2>
      <p>在顶部选择供应商和月份，或前往订单页导入订单。</p>
    </div>

    <template v-else>
      <!-- Page header -->
      <header class="page-header">
        <div class="header-info">
          <h1 class="page-title">对账 · 序列号差异</h1>
          <p class="page-subtitle">分公司状态与差异明细</p>
        </div>
        <div class="header-actions">
          <el-button :icon="Refresh" @click="loadBranchSummary">刷新</el-button>
          <el-button
            v-if="canManageReconciliation"
            type="primary"
            :icon="Refresh"
            :loading="rematching"
            :disabled="rematching"
            @click="doRematch"
          >
            {{ rematching ? '对账中...' : '重新对账' }}
          </el-button>
        </div>
      </header>

      <!-- KPI bar -->
      <div class="kpi-bar">
        <div class="kpi-item">
          <span class="kpi-label">总差异数</span>
          <strong class="kpi-value kpi-diff">{{ totalDiffCount }}</strong>
        </div>
        <div class="kpi-item">
          <span class="kpi-label">待结论</span>
          <strong class="kpi-value kpi-pending">{{ totalPendingCount }}</strong>
        </div>
        <div class="kpi-item">
          <span class="kpi-label">匹配率</span>
          <strong class="kpi-value">{{ matchRate }}</strong>
        </div>
      </div>

      <!-- Branch table -->
      <div class="table-wrap">
        <el-table
          v-loading="loadingBranches"
          :data="branches"
          row-key="branchId"
          stripe
          class="branch-table"
          @expand-change="handleExpandChange"
        >
          <el-table-column type="expand">
            <template #default="scope">
              <div class="expand-panel">
                <div v-if="loadingBranchId === scope.row.branchId" class="expand-loading">加载中...</div>
                <el-table
                  v-else
                  :data="branchDetailCache[scope.row.branchId] || []"
                  size="small"
                  class="detail-table"
                >
                  <el-table-column label="核对结果" width="100">
                    <template #default="detail">
                      <el-tag :type="resultTagType(detail.row.resultType)" size="small" effect="light">
                        {{ resultTypeLabel(detail.row.resultType) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="serial" label="序列号" min-width="140" show-overflow-tooltip />
                  <el-table-column prop="orderNumber" label="订单号" min-width="130" show-overflow-tooltip />
                  <el-table-column prop="supplierBranch" label="分公司" min-width="120" show-overflow-tooltip />
                  <el-table-column prop="systemBranch" label="系统分公司" min-width="120" show-overflow-tooltip />
                  <el-table-column prop="internalCode" label="内部编号" width="120" show-overflow-tooltip />
                  <el-table-column label="结论" width="170">
                    <template #default="detail">
                      <el-select
                        v-if="detail.row.issue"
                        :model-value="detail.row.issue.conclusionType ?? ''"
                        size="small"
                        class="conclusion-select"
                        @change="(val) => onConclusionChange(detail.row, val)"
                      >
                        <el-option
                          v-for="opt in CONCLUSION_OPTIONS"
                          :key="opt.value"
                          :value="opt.value"
                          :label="opt.label"
                        />
                      </el-select>
                      <span v-else class="muted">—</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="备注" min-width="150">
                    <template #default="detail">
                      <input
                        v-if="detail.row.issue"
                        v-model="noteEditing[detail.row.issue.id]"
                        class="note-input"
                        type="text"
                        placeholder="添加备注"
                        @blur="handleNoteBlur(detail.row)"
                      >
                      <span v-else class="muted">—</span>
                    </template>
                  </el-table-column>
                </el-table>
                <div
                  v-if="loadingBranchId !== scope.row.branchId
                    && !(branchDetailCache[scope.row.branchId] || []).length"
                  class="empty-filter"
                >该分公司暂无差异记录。</div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="56" align="center">
            <template #default="scope">{{ branchStatusIcon(scope.row) }}</template>
          </el-table-column>
          <el-table-column prop="branchName" label="分公司" min-width="140" />
          <el-table-column label="订单台数" width="90" align="right">
            <template #default="scope">{{ scope.row.orderCount }}</template>
          </el-table-column>
          <el-table-column label="差异数" width="80" align="right">
            <template #default="scope">
              <span :class="scope.row.diffCount > 0 ? 'count-diff' : ''">{{ scope.row.diffCount }}</span>
            </template>
          </el-table-column>
          <el-table-column label="待结论" width="80" align="right">
            <template #default="scope">
              <span :class="scope.row.pendingCount > 0 ? 'count-pending' : ''">{{ scope.row.pendingCount }}</span>
            </template>
          </el-table-column>
          <el-table-column label="本月金额" width="130" align="right">
            <template #default="scope">{{ formatMoney(scope.row.monthAmount) }}</template>
          </el-table-column>
        </el-table>
        <div v-if="!loadingBranches && !branches.length" class="empty-filter">暂无分公司数据，请先导入订单并运行对账。</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.differences-page { width: 100%; max-width: 1400px; min-width: 0; margin: 0 auto; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin: 18px 0 12px; }
.header-info { display: flex; min-width: 0; flex-direction: column; gap: 5px; }
.page-title { margin: 0; font-size: var(--text-xl); font-weight: 600; }
.page-subtitle { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.header-actions { display: flex; align-items: center; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.kpi-bar { display: flex; gap: 16px; margin-bottom: 16px; }
.kpi-item { display: flex; flex-direction: column; gap: 4px; padding: 12px 20px; border: 1px solid var(--color-border-light); border-radius: 8px; background: var(--color-bg-card); min-width: 120px; }
.kpi-label { color: var(--color-text-secondary); font-size: var(--text-xs); }
.kpi-value { font-size: var(--text-lg); font-weight: 600; font-variant-numeric: tabular-nums; }
.kpi-diff { color: color-mix(in oklch, var(--color-warning) 80%, var(--color-text-primary)); }
.kpi-pending { color: var(--color-danger); }
.table-wrap { min-width: 0; }
.branch-table { width: 100%; }
.branch-table :deep(th.el-table__cell) { background-color: var(--color-bg-table-header); color: var(--color-text-secondary); font-weight: 600; }
.expand-panel { padding: 12px 16px; background: var(--color-bg-page); }
.expand-loading { padding: 20px; color: var(--color-text-secondary); text-align: center; font-size: var(--text-sm); }
.detail-table { width: 100%; }
.detail-table :deep(th.el-table__cell) { background-color: var(--color-bg-elevated); color: var(--color-text-secondary); font-size: var(--text-xs); font-weight: 600; }
.conclusion-select { width: 100%; }
.note-input { width: 100%; padding: 3px 6px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-bg-card); color: var(--color-text-primary); font: inherit; font-size: var(--text-xs); outline: none; }
.note-input:focus { border-color: var(--color-primary-400); }
.count-diff { color: color-mix(in oklch, var(--color-warning) 80%, var(--color-text-primary)); font-weight: 600; }
.count-pending { color: var(--color-danger); font-weight: 600; }
.muted { color: var(--color-text-tertiary); }
.empty-start { max-width: 560px; padding: 64px 0; }
.empty-start h2 { margin: 0 0 8px; font-size: var(--text-md); }
.empty-start p { margin: 0 0 18px; color: var(--color-text-secondary); line-height: 1.5; }
.empty-filter { display: flex; min-height: 80px; align-items: center; justify-content: center; gap: 6px; padding: 20px; color: var(--color-text-secondary); text-align: center; }
@media (max-width: 760px) {
  .page-header { align-items: flex-start; flex-direction: column; }
  .header-actions { width: 100%; justify-content: flex-start; }
  .kpi-bar { flex-wrap: wrap; }
}
</style>
