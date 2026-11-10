<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import {
  getPaymentSummary,
  exportPayment,
  archiveReconciliationTask,
  type ReconciliationPaymentSummary,
  type ReconciliationPaymentBranch,
} from '@/api/reconciliation'
import { useUserStore } from '@/store/user'
import { useReconciliationTask } from '@/composables/useReconciliationTask'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()
const { currentTaskId, currentTask } = useReconciliationTask()

const canManageReconciliation = computed(() => userStore.can('manage_reconciliation'))
const canViewReconciliation = computed(() => userStore.can('view_reconciliation'))

const summary = ref<ReconciliationPaymentSummary | null>(null)
const loading = ref(false)
const archiving = ref(false)
const exporting = ref(false)

function formatMoney(value: string | null | undefined) {
  if (!value) return '—'
  return '¥' + Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return value
}

function resultTypeLabel(t: string) {
  const m: Record<string, string> = {
    matched: '匹配',
    branch_mismatch: '分公司不一致',
    order_only: '仅订单有',
    system_only: '仅系统有',
    system_duplicate: '序列号重复',
    system_missing_serial: '缺少序列号',
  }
  return m[t] ?? t
}

const pendingRowCount = computed(() => summary.value?.branches.reduce((s: number, b: ReconciliationPaymentBranch) => s + b.diffCount, 0) ?? 0)

async function loadSummary() {
  if (!currentTaskId.value) return
  loading.value = true
  try {
    const { data } = await getPaymentSummary(currentTaskId.value)
    summary.value = data
  } catch {
    ElMessage.error('加载待付金额失败')
  } finally {
    loading.value = false
  }
}

async function doExport() {
  if (!currentTaskId.value || !canViewReconciliation.value || exporting.value) return
  exporting.value = true
  try {
    const response = await exportPayment(currentTaskId.value)
    const blob = response.data
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const period = currentTask.value?.period ?? ''
    const supplierName = currentTask.value?.supplierName ?? ''
    a.href = url
    a.download = `付款明细-${period}-${supplierName}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

async function doArchive() {
  if (!currentTaskId.value || !canManageReconciliation.value || archiving.value) return
  if (!summary.value?.canArchive) return
  try {
    await ElMessageBox.confirm('确认归档此对账任务？归档后不可修改。', '归档确认', {
      confirmButtonText: '确认归档',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  archiving.value = true
  try {
    await archiveReconciliationTask(currentTaskId.value)
    ElMessage.success('任务已归档')
    await loadSummary()
  } catch {
    ElMessage.error('归档失败')
  } finally {
    archiving.value = false
  }
}

watch(() => currentTaskId.value, (newId) => {
  if (newId) {
    void loadSummary()
  } else {
    summary.value = null
  }
}, { immediate: true })
</script>

<template>
  <div class="payment-page page-fill">
    <!-- Current task supplier banner -->
    <div v-if="currentTask" class="supplier-banner">
      <span class="supplier-banner-name">{{ currentTask.supplierName }}</span>
      <span class="supplier-banner-sep">·</span>
      <span class="supplier-banner-period">{{ currentTask.period }}</span>
      <span class="supplier-banner-version">v{{ currentTask.currentVersion ?? 1 }}</span>
    </div>

    <!-- Empty state when no task selected -->
    <div v-if="!currentTaskId" class="empty-start">
      <h2>尚未选择对账任务</h2>
      <p>请前往<a class="link" @click="router.push('/reconciliation/orders')">供应商订单页</a>选择任务。</p>
    </div>

    <template v-else>
      <!-- Page header -->
      <header class="page-header">
        <div class="header-info">
          <h1 class="page-title">待付金额<template v-if="currentTask"> · {{ currentTask.supplierName }}</template></h1>
          <p class="page-subtitle">金额汇总与付款明细</p>
        </div>
        <div class="header-actions">
          <el-button
            v-if="canViewReconciliation"
            :icon="Download"
            :loading="exporting"
            :disabled="exporting"
            @click="doExport"
          >
            导出
          </el-button>
          <el-tooltip
            v-if="canManageReconciliation"
            :content="summary && !summary.canArchive ? `仍有 ${pendingRowCount} 条差异未处理` : ''"
            :disabled="summary?.canArchive ?? false"
            placement="top"
          >
            <span>
              <el-button
                type="primary"
                :loading="archiving"
                :disabled="archiving || !summary?.canArchive"
                @click="doArchive"
              >
                归档
              </el-button>
            </span>
          </el-tooltip>
        </div>
      </header>

      <!-- Amount cards -->
      <div v-loading="loading" class="amount-cards">
        <div class="amount-card">
          <span class="amount-label">已确认</span>
          <strong class="amount-value amount-confirmed">{{ formatMoney(summary?.confirmedAmount) }}</strong>
        </div>
        <div class="amount-card">
          <span class="amount-label">待确认</span>
          <strong class="amount-value amount-pending">{{ formatMoney(summary?.pendingAmount) }}</strong>
        </div>
        <div class="amount-card">
          <span class="amount-label">本月应计</span>
          <strong class="amount-value amount-total">{{ formatMoney(summary?.totalAmount) }}</strong>
        </div>
      </div>

      <!-- Detail table -->
      <div class="table-wrap">
        <el-table
          v-loading="loading"
          :data="summary?.branches ?? []"
          row-key="branchId"
          stripe
          class="payment-table"
        >
          <el-table-column type="expand">
            <template #default="scope">
              <el-table :data="scope.row.rows" size="small" class="detail-table">
                <el-table-column prop="serial" label="序列号" min-width="140" show-overflow-tooltip>
                  <template #default="d">{{ d.row.serial ?? '—' }}</template>
                </el-table-column>
                <el-table-column prop="internalCode" label="内部编号" width="120" show-overflow-tooltip />
                <el-table-column label="差异类型" width="130">
                  <template #default="d">{{ resultTypeLabel(d.row.resultType) }}</template>
                </el-table-column>
                <el-table-column label="起租日期" width="120">
                  <template #default="d">{{ formatDate(d.row.leaseStartDate) }}</template>
                </el-table-column>
                <el-table-column label="记账日期" width="120">
                  <template #default="d">{{ formatDate(d.row.accountingDate) }}</template>
                </el-table-column>
                <el-table-column label="计费天数" width="90" align="right">
                  <template #default="d">{{ d.row.billingDays ?? '—' }}</template>
                </el-table-column>
                <el-table-column label="月租金" width="130" align="right">
                  <template #default="d">{{ formatMoney(d.row.monthlyRent) }}</template>
                </el-table-column>
                <el-table-column label="本月金额" width="130" align="right">
                  <template #default="d">{{ formatMoney(d.row.monthAmount) }}</template>
                </el-table-column>
              </el-table>
            </template>
          </el-table-column>
          <el-table-column prop="branchName" label="分公司" min-width="140" />
          <el-table-column label="已确认金额" width="140" align="right">
            <template #default="scope">{{ formatMoney(scope.row.confirmedAmount) }}</template>
          </el-table-column>
          <el-table-column label="待确认金额" width="140" align="right">
            <template #default="scope">
              <span :class="Number(scope.row.pendingAmount) > 0 ? 'amount-pending' : ''">
                {{ formatMoney(scope.row.pendingAmount) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="本月合计" width="130" align="right">
            <template #default="scope">{{ formatMoney(scope.row.totalAmount) }}</template>
          </el-table-column>
          <el-table-column label="差异数" width="80" align="right">
            <template #default="scope">
              <span :class="scope.row.diffCount > 0 ? 'count-diff' : ''">{{ scope.row.diffCount }}</span>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!loading && !(summary?.branches ?? []).length" class="empty-filter">暂无付款明细数据。</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.payment-page { width: 100%; max-width: 1400px; min-width: 0; margin: 0 auto; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin: 18px 0 12px; }
.header-info { display: flex; min-width: 0; flex-direction: column; gap: 5px; }
.page-title { margin: 0; font-size: var(--text-xl); font-weight: 600; }
.page-subtitle { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.header-actions { display: flex; align-items: center; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }

.amount-cards { display: flex; gap: 16px; margin-bottom: 16px; }
.amount-card { display: flex; flex-direction: column; gap: 4px; flex: 1; padding: 16px 20px; border: 1px solid var(--color-border-light); border-radius: 8px; background: var(--color-bg-card); }
.amount-label { color: var(--color-text-secondary); font-size: var(--text-xs); }
.amount-value { font-size: var(--text-xl); font-weight: 600; font-variant-numeric: tabular-nums; }
.amount-confirmed { color: var(--color-primary-600); }
.amount-pending { color: var(--color-warning); }
.amount-total { color: var(--color-text-primary); }

.table-wrap { min-width: 0; }
.payment-table { width: 100%; }
.payment-table :deep(th.el-table__cell) { background-color: var(--color-bg-table-header); color: var(--color-text-secondary); font-weight: 600; }
.detail-table { width: 100%; }
.detail-table :deep(th.el-table__cell) { background-color: var(--color-bg-elevated); color: var(--color-text-secondary); font-size: var(--text-xs); font-weight: 600; }
.count-diff { color: color-mix(in oklch, var(--color-warning) 80%, var(--color-text-primary)); font-weight: 600; }

.muted { color: var(--color-text-tertiary); }

.supplier-banner { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-4); background: var(--color-primary-50); border-bottom: 2px solid var(--color-primary-200); font-size: var(--text-sm); }
.supplier-banner-name { color: var(--color-primary-700); font-weight: 700; font-size: var(--text-md); }
.supplier-banner-sep { color: var(--color-text-tertiary); }
.supplier-banner-period { color: var(--color-text-secondary); font-weight: 500; }
.supplier-banner-version { margin-left: var(--space-1); padding: 2px var(--space-2); border-radius: var(--radius-sm); background: var(--color-primary-100); color: var(--color-primary-700); font-size: var(--text-xs); font-weight: 500; white-space: nowrap; }
.link { color: var(--color-primary-600); cursor: pointer; }
.link:hover { text-decoration: underline; }
.empty-start { max-width: 560px; padding: 64px 0; }
.empty-start h2 { margin: 0 0 8px; font-size: var(--text-md); }
.empty-start p { margin: 0 0 18px; color: var(--color-text-secondary); line-height: 1.5; }
.empty-filter { display: flex; min-height: 80px; align-items: center; justify-content: center; gap: 6px; padding: 20px; color: var(--color-text-secondary); text-align: center; }

@media (max-width: 760px) {
  .page-header { align-items: flex-start; flex-direction: column; }
  .header-actions { width: 100%; justify-content: flex-start; }
  .amount-cards { flex-wrap: wrap; }
  .amount-card { min-width: calc(50% - 8px); }
}
</style>
