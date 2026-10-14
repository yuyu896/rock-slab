<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useQueryFilters } from '@/composables/useQueryFilters'
import { getRecoveryLedger, exportRecoveryLedger, type RecoveryLedgerRow } from '@/api/transfers'
import { getFixedAsset, getFixedAssetTimeline } from '@/api/assets'
import type { FixedAsset, FixedAssetTimeline } from '@/types'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import { View } from '@element-plus/icons-vue'
import BasePagination from '@/components/BasePagination.vue'
import BranchFilterSelect from '@/components/BranchFilterSelect.vue'
import { TRANSFER_TYPES } from '@/constants'

/** 物资处置台账：直接处置的物资明细流水（实例逐台一行；单据派生只读） */

const filters = ref({ branch: [] as string[], dateFrom: '', dateTo: '', keyword: '' })
const branchOptions = ref<{ value: string; label: string }[]>([])
const pagination = ref({ page: 1, pageSize: 50, total: 0 })
// 筛选与页码持久化到路由 query（详情页往返保留；恢复须先于下方 fetch-watch）
useQueryFilters(filters, pagination, { arrayKeys: ['branch'] })
const disposalIncome = ref<number | null>(null)
const loading = ref(false)
const rows = ref<RecoveryLedgerRow[]>([])
const exporting = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailAsset = ref<FixedAsset | null>(null)
const detailTimeline = ref<FixedAssetTimeline | null>(null)
const detailError = ref('')

async function fetchRows() {
  loading.value = true
  try {
    const { data } = await getRecoveryLedger({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      fromBranch: filters.value.branch.length ? filters.value.branch.join(',') : undefined,
      keyword: filters.value.keyword || undefined,
      dateFrom: filters.value.dateFrom || undefined,
      dateTo: filters.value.dateTo || undefined,
    })
    rows.value = data.results
    pagination.value.total = data.count
    disposalIncome.value = Number(data.disposal_income ?? data.disposalIncome ?? 0) || 0
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

async function openInstanceDetail(row: RecoveryLedgerRow) {
  if (!row.实例ID) return
  detailVisible.value = true
  detailLoading.value = true
  detailAsset.value = null
  detailTimeline.value = null
  detailError.value = ''
  const [assetResult, timelineResult] = await Promise.allSettled([
    getFixedAsset(row.实例ID),
    getFixedAssetTimeline(row.实例ID),
  ])
  if (assetResult.status === 'fulfilled') {
    detailAsset.value = assetResult.value.data
  }
  if (timelineResult.status === 'fulfilled') {
    detailTimeline.value = timelineResult.value.data
  }
  const errors = [assetResult, timelineResult]
    .filter((result): result is PromiseRejectedResult => result.status === 'rejected')
    .map((result) => handleApiError(result.reason))
  if (errors.length) detailError.value = `部分信息读取失败：${errors.join('；')}`
  detailLoading.value = false
}

function closeInstanceDetail() {
  detailVisible.value = false
  detailAsset.value = null
  detailTimeline.value = null
  detailError.value = ''
}

function transferTypeLabel(actionType: string) {
  return TRANSFER_TYPES[actionType as keyof typeof TRANSFER_TYPES]?.label || actionType || '-'
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
    if (filters.value.branch.length) params.fromBranch = filters.value.branch.join(',')
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.dateFrom) params.dateFrom = filters.value.dateFrom
    if (filters.value.dateTo) params.dateTo = filters.value.dateTo
    const { data } = await exportRecoveryLedger(params)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = `物资处置台账_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    exporting.value = false
  }
}

function resetFilters() {
  filters.value = { branch: [], dateFrom: '', dateTo: '', keyword: '' }
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
        <h1 class="page-title">物资处置台账</h1>
        <p class="page-desc">
          直接处置物资明细 · 共{{ pagination.total }}条 · 处置收入合计 ¥{{ disposalIncome ?? 0 }} · 供管理层查账
        </p>
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
        <div class="filter-item grow">
          <BranchFilterSelect v-model="filters.branch" :options="branchOptions" />
        </div>
        <div class="filter-item">
          <input v-model="filters.dateFrom" type="date" class="filter-input date-input" aria-label="开始日期" />
          <span class="date-sep">至</span>
          <input v-model="filters.dateTo" type="date" class="filter-input date-input" aria-label="结束日期" />
        </div>
        <button class="filter-reset" @click="resetFilters"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>重置</button>
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
          <tr v-for="(row, index) in rows" :key="`${row.单据ID}-${row.内部编号 || row.品目编号}-${index}`">
            <td><span class="date-text">{{ row.日期 || '-' }}</span></td>
            <td><span class="doc-number">{{ row.单据编号 || '-' }}</span></td>
            <td>{{ row.分公司 || '-' }}</td>
            <td>{{ row.品目编号 }}</td>
            <td>{{ row.品目名称 || '-' }}</td>
            <td>{{ row.规格 || '-' }}</td>
            <td class="col-num">{{ row.数量 }}</td>
            <td>
              <button
                v-if="row.实例ID"
                type="button"
                class="asset-link"
                :aria-label="`查看固定物资档案和生平：${row.内部编号}`"
                @click="openInstanceDetail(row)"
              >
                <View aria-hidden="true" />
                <span>查看</span>
                {{ row.内部编号 }}
              </button>
              <span v-else>-</span>
            </td>
            <td>{{ row.处置方式 || '-' }}</td>
            <td class="col-num"><span v-if="row.处置金额 != null" class="date-text">{{ row.处置金额 }}</span><span v-else>-</span></td>
            <td>{{ row.经办人 || '-' }}</td>
            <td>{{ row.备注 || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination :total="pagination.total" :current-page="pagination.page" :page-size="pagination.pageSize" @change="handlePaginationChange" />

    <div v-if="detailVisible" class="detail-backdrop" role="presentation" @click.self="closeInstanceDetail">
      <section class="detail-dialog" role="dialog" aria-modal="true" aria-labelledby="fixed-asset-detail-title">
        <div class="detail-header">
          <div>
            <h2 id="fixed-asset-detail-title">固定物资档案</h2>
            <p>直接处置历史记录（只读）</p>
          </div>
          <button type="button" class="detail-close" aria-label="关闭详情" @click="closeInstanceDetail">×</button>
        </div>
        <div v-if="detailLoading" class="detail-empty">加载中...</div>
        <template v-else>
          <div v-if="detailError" class="detail-error" role="alert">{{ detailError }}</div>
          <div v-if="detailAsset" class="detail-fields">
            <div><span>内部编号</span><strong>{{ detailAsset.内部编号 }}</strong></div>
            <div><span>品目编号</span><strong>{{ detailAsset.itemCode || detailAsset.item_code || '-' }}</strong></div>
            <div><span>品目名称</span><strong>{{ detailAsset.itemName || detailAsset.item_name || '-' }}</strong></div>
            <div><span>分公司</span><strong>{{ detailAsset.branchName || detailAsset.branch_name || '-' }}</strong></div>
            <div><span>当前状态</span><strong>{{ detailAsset.当前状态 }}</strong></div>
            <div><span>使用人</span><strong>{{ detailAsset.使用人 || '-' }}</strong></div>
            <div><span>部门</span><strong>{{ detailAsset.departmentName || detailAsset.department_name || '-' }}</strong></div>
            <div><span>序列号</span><strong>{{ detailAsset.序列号 || '待补录' }}</strong></div>
          </div>
          <div v-else class="detail-empty">档案详情未能加载</div>
          <p v-if="detailTimeline?.birth" class="detail-origin">
            出生单：{{ detailTimeline.birth.单据编号 || '-' }} · {{ detailTimeline.birth.日期 || '-' }}
            <span v-if="detailTimeline.birth.供应商">· 供应商：{{ detailTimeline.birth.供应商 }}</span>
          </p>
          <div v-if="detailTimeline" class="detail-timeline">
            <h3>完整流转日志</h3>
            <table class="data-table">
              <thead><tr><th>日期</th><th>单据</th><th>类型</th><th>使用人</th><th>审批状态</th></tr></thead>
              <tbody>
                <tr v-for="entry in detailTimeline.timeline" :key="`${entry.transferId || entry.transfer_id || ''}-${entry.行号}`">
                  <td>{{ entry.日期 || '-' }}</td>
                  <td>{{ entry.单据编号 || '-' }}</td>
                  <td>{{ transferTypeLabel(entry.actionType || entry.action_type || '') }}</td>
                  <td>{{ entry.使用人 || '-' }}</td>
                  <td>{{ entry.审批状态 || '-' }}</td>
                </tr>
                <tr v-if="detailTimeline.timeline.length === 0"><td colspan="5" class="detail-empty">暂无流转记录</td></tr>
              </tbody>
            </table>
          </div>
          <div v-else class="detail-empty">生平记录未能加载</div>
        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
.transfer-page { width: 100%; max-width: 1600px; margin: 0 auto; }
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
.filter-item.grow { flex: 1; }
.filter-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; color: var(--color-text-tertiary); }
.filter-input { height: 38px; padding: 0 var(--space-4) 0 38px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); color: var(--color-text-primary); }
.filter-item.search .filter-input { width: 100%; }
.date-input { padding: 0 var(--space-2); }
.date-sep { color: var(--color-text-tertiary); font-size: var(--text-sm); }
.filter-reset { height: 38px; padding: 0 var(--space-4); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; color: var(--color-text-secondary); font-size: var(--text-sm); cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.filter-reset svg { width: 14px; height: 14px; }
.filter-reset:hover { color: var(--color-primary-500); border-color: var(--color-primary-500); }
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
.asset-link { display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; border: 0; border-radius: 4px; color: var(--color-primary-700); background: var(--color-primary-50); font-family: var(--font-mono); font-size: var(--text-sm); cursor: pointer; white-space: nowrap; }
.asset-link svg { width: 14px; height: 14px; }
.asset-link:hover { text-decoration: underline; }
.detail-backdrop { position: fixed; inset: 0; z-index: 40; display: flex; align-items: center; justify-content: center; padding: 24px; background: rgba(15, 23, 42, .42); }
.detail-dialog { width: min(1440px, 100%); height: min(900px, 92vh); max-height: calc(100vh - 48px); overflow: auto; padding: 24px; border-radius: 10px; background: var(--color-bg-card); box-shadow: 0 18px 50px rgba(15, 23, 42, .2); }
.detail-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
.detail-header h2, .detail-header p, .detail-timeline h3 { margin: 0; }
.detail-header h2 { font-size: var(--text-lg); color: var(--color-text-primary); }
.detail-header p { margin-top: 4px; color: var(--color-text-tertiary); font-size: var(--text-sm); }
.detail-close { width: 32px; height: 32px; border: 1px solid var(--color-border); border-radius: 6px; background: transparent; color: var(--color-text-secondary); font-size: 22px; cursor: pointer; }
.detail-fields { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 24px; }
.detail-fields div { min-width: 0; padding: 12px; border: 1px solid var(--color-border-light); border-radius: 6px; }
.detail-fields span { display: block; margin-bottom: 4px; color: var(--color-text-tertiary); font-size: var(--text-xs); }
.detail-fields strong { display: block; overflow-wrap: anywhere; color: var(--color-text-primary); font-size: var(--text-sm); }
.detail-timeline h3 { margin-bottom: 10px; font-size: var(--text-md); color: var(--color-text-primary); }
.detail-origin { margin: 0 0 16px; color: var(--color-text-secondary); font-size: var(--text-sm); }
.detail-empty { padding: 32px; text-align: center; color: var(--color-text-tertiary); }
.detail-error { margin-bottom: 16px; padding: 10px 12px; border-left: 3px solid var(--color-warning, #b45309); background: var(--color-warning-bg, #fef3c7); color: var(--color-text-primary); font-size: var(--text-sm); overflow-wrap: anywhere; }
@media (max-width: 700px) { .detail-backdrop { padding: 12px; } .detail-dialog { height: 92vh; max-height: calc(100vh - 24px); padding: 16px; } .detail-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
