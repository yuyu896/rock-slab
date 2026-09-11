<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getRecoveryLedger, exportRecoveryLedger } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import BasePagination from '@/components/BasePagination.vue'
import BranchFilterSelect from '@/components/BranchFilterSelect.vue'

/** 回收台账：直接处置的物资明细流水（实例逐台一行；单据派生只读，管理层查账） */

type LedgerRow = Record<string, string | number | null>

const filters = ref({ branch: '', dateFrom: '', dateTo: '', keyword: '' })
const branchOptions = ref<{ value: string; label: string }[]>([])
const pagination = ref({ page: 1, pageSize: 50, total: 0 })
const loading = ref(false)
const rows = ref<LedgerRow[]>([])
const exporting = ref(false)

async function fetchRows() {
  loading.value = true
  try {
    const { data } = await getRecoveryLedger({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      fromBranch: filters.value.branch || undefined,
      keyword: filters.value.keyword || undefined,
      dateFrom: filters.value.dateFrom || undefined,
      dateTo: filters.value.dateTo || undefined,
    })
    rows.value = data.results as LedgerRow[]
    pagination.value.total = data.count
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

async function fetchBranches() {
  try {
    const { data } = await getBranches()
    branchOptions.value = data.map((b: any) => ({ value: b.name, label: b.name }))
  } catch { /* 静默 */ }
}

async function handleExport() {
  exporting.value = true
  try {
    const params: Record<string, string> = {}
    if (filters.value.branch) params.fromBranch = filters.value.branch
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.dateFrom) params.dateFrom = filters.value.dateFrom
    if (filters.value.dateTo) params.dateTo = filters.value.dateTo
    const { data } = await exportRecoveryLedger(params)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = `回收台账_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    exporting.value = false
  }
}

function resetFilters() {
  filters.value = { branch: '', dateFrom: '', dateTo: '', keyword: '' }
  pagination.value.page = 1
  fetchRows()
}

const handlePaginationChange = (page: number, pageSize: number) => {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchRows()
}

watch(filters, () => { pagination.value.page = 1; fetchRows() }, { deep: true })
onMounted(() => { fetchRows(); fetchBranches() })
</script>

<template>
  <div class="transfer-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">回收台账</h1>
        <p class="page-desc">直接处置物资明细 · 共{{ pagination.total }}条 · 供管理层查账</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" :disabled="exporting" @click="handleExport">
          {{ exporting ? '导出中...' : '导出' }}
        </button>
      </div>
    </div>

    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item search">
          <svg class="filter-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <input v-model="filters.keyword" type="text" placeholder="搜索品目编号、名称、单号..." class="filter-input" />
        </div>
        <div class="filter-item">
          <BranchFilterSelect v-model="filters.branch" :options="branchOptions" />
        </div>
        <div class="filter-item">
          <input v-model="filters.dateFrom" type="date" class="filter-input date-input" aria-label="开始日期" />
          <span class="date-sep">至</span>
          <input v-model="filters.dateTo" type="date" class="filter-input date-input" aria-label="结束日期" />
        </div>
        <button class="filter-reset" @click="resetFilters">重置</button>
      </div>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>日期</th><th>单据编号</th><th>分公司</th><th>品目编号</th><th>品目名称</th>
            <th>规格</th><th class="col-num">数量</th><th>内部编号</th><th>处置方式</th>
            <th class="col-num">处置金额</th><th>经办人</th><th>备注</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="12" class="empty-cell">加载中...</td></tr>
          <tr v-else-if="rows.length === 0"><td colspan="12" class="empty-cell">暂无处置记录</td></tr>
          <tr v-for="(row, index) in rows" :key="index">
            <td><span class="date-text">{{ row.日期 || '-' }}</span></td>
            <td><span class="doc-number">{{ row.单据编号 || '-' }}</span></td>
            <td>{{ row.分公司 || '-' }}</td>
            <td>{{ row.品目编号 }}</td>
            <td>{{ row.品目名称 || '-' }}</td>
            <td>{{ row.规格 || '-' }}</td>
            <td class="col-num">{{ row.数量 }}</td>
            <td><span v-if="row.内部编号" class="asset-code">{{ row.内部编号 }}</span><span v-else>-</span></td>
            <td>{{ row.处置方式 || '-' }}</td>
            <td class="col-num"><span v-if="row.处置金额 != null" class="date-text">{{ row.处置金额 }}</span><span v-else>-</span></td>
            <td>{{ row.经办人 || '-' }}</td>
            <td>{{ row.备注 || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination :total="pagination.total" :current-page="pagination.page" :page-size="pagination.pageSize" @change="handlePaginationChange" />
  </div>
</template>

<style scoped>
.transfer-page { max-width: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-6); flex-shrink: 0; }
.header-info { display: flex; align-items: baseline; gap: var(--space-3); }
.page-title { font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.page-desc { font-size: var(--text-sm); color: var(--color-text-tertiary); margin: 0; }
.header-actions { display: flex; gap: var(--space-3); }
.btn-secondary { display: flex; align-items: center; gap: var(--space-2); height: 38px; padding: 0 var(--space-4); border-radius: 8px; font-size: var(--text-sm); font-weight: 500; cursor: pointer; background: var(--color-bg-card); border: 1px solid var(--color-border); color: var(--color-text-primary); }
.btn-secondary:hover { border-color: var(--color-primary-300); }
.btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }
.filter-section { background: var(--color-bg-card); border-radius: 12px; padding: var(--space-4); margin-bottom: var(--space-4); border: 1px solid var(--color-border); flex-shrink: 0; }
.filter-row { display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap; }
.filter-item { position: relative; display: flex; align-items: center; gap: 6px; }
.filter-item.search { flex: 1; min-width: 220px; }
.filter-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; color: var(--color-text-tertiary); }
.filter-input { height: 38px; padding: 0 var(--space-4) 0 38px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); color: var(--color-text-primary); }
.filter-item.search .filter-input { width: 100%; }
.date-input { padding: 0 var(--space-2); }
.date-sep { color: var(--color-text-tertiary); font-size: var(--text-sm); }
.filter-reset { height: 38px; padding: 0 var(--space-4); background: transparent; border: none; color: var(--color-text-secondary); font-size: var(--text-sm); cursor: pointer; }
.filter-reset:hover { color: var(--color-primary-500); }
.table-container { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); overflow-x: auto; flex: 1; min-height: 200px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table thead th { position: sticky; top: 0; z-index: 1; background: var(--color-bg-elevated); }
.data-table th { padding: var(--space-3) var(--space-4); text-align: left; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); white-space: nowrap; }
.data-table td { padding: var(--space-3) var(--space-4); font-size: var(--text-sm); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border-light); }
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.col-num { text-align: right; }
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-8) var(--space-4) !important; }
.doc-number { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-text-secondary); }
.date-text { font-family: var(--font-mono); color: var(--color-text-secondary); font-size: var(--text-xs); white-space: nowrap; }
.asset-code { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-primary-600); background: var(--color-primary-50); padding: 2px 8px; border-radius: 4px; }
</style>
