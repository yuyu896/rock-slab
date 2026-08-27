<script setup lang="ts">
import { MANAGEMENT_TYPE_LABELS } from '@/constants'
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getAssetStocks, exportAssetStocks, getFixedAssets } from '@/api/assets'
import { getBranches } from '@/api/branches'
import { getCategories } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import type { AssetStock } from '@/types'
import BasePagination from '@/components/BasePagination.vue'
import SummaryImportDialog from './SummaryImportDialog.vue'
import AdjustDialog from './AdjustDialog.vue'
import AdjustRecordsDialog from './AdjustRecordsDialog.vue'
import type { FixedAsset } from '@/types'

// ── 台账调整（P3：行内开调整单 + 调整记录；数量变动唯一合规出口之一） ──
const adjustVisible = ref(false)
const adjustStock = ref<AssetStock | null>(null)
const recordsVisible = ref(false)

function openAdjust(stock: (typeof stocks.value)[number]) {
  adjustStock.value = stock
  adjustVisible.value = true
}

// ── 实例下钻（实例管理品目行：该分公司×品目的实例档案，P2 第三刀） ──
const drillStock = ref<(typeof stocks.value)[number] | null>(null)
const drillInstances = ref<FixedAsset[]>([])
const drillLoading = ref(false)
const drillVisible = computed({
  get: () => drillStock.value !== null,
  set: (v: boolean) => { if (!v) drillStock.value = null },
})

async function openDrill(stock: (typeof stocks.value)[number]) {
  drillStock.value = stock
  drillInstances.value = []
  drillLoading.value = true
  try {
    const { data } = await getFixedAssets({
      asset_code: stock.资产编号,
      branch: stock.branchName || undefined,
      pageSize: 100,
    })
    drillInstances.value = data.results || []
  } finally {
    drillLoading.value = false
  }
}

function goTimeline(code: string) {
  drillVisible.value = false
  window.open(`/fixed-assets?keyword=${encodeURIComponent(code)}`, '_self')
}

const { can } = usePermission()
const canImport = can('adjust_ledger') || can('manage_assets')
const canAdjust = can('adjust_ledger')

// 报表"库存不足"下钻：/assets/summary?sufficient=0 预置仅不足
const route = useRoute()
const filters = ref({
  branch: '',
  category: '',
  keyword: '',
  sufficient: route.query.sufficient === '0' ? '0' : '',
})

const pagination = ref({ page: 1, pageSize: 50, total: 0 })
const loading = ref(false)
const stocks = ref<AssetStock[]>([])

const branchOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部分公司' }])
const categoryOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部类目' }])

async function fetchStocks() {
  loading.value = true
  try {
    const { data } = await getAssetStocks({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      branch: filters.value.branch || undefined,
      category: filters.value.category || undefined,
      keyword: filters.value.keyword || undefined,
      sufficient: filters.value.sufficient || undefined,
    })
    stocks.value = data.results
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
    branchOptions.value = [
      { value: '', label: '全部分司' },
      ...data.map((b: any) => ({ value: b.name, label: b.name })),
    ]
    branchOptions.value[0] = { value: '', label: '全部分公司' }
  } catch (error) {
    console.error('Failed to fetch branches:', error)
  }
}

async function fetchCategories() {
  try {
    let allResults: any[] = []
    let page = 1
    let hasMore = true
    while (hasMore) {
      const { data } = await getCategories({ pageSize: 100, page })
      const results = data.results ?? data
      allResults = allResults.concat(results)
      const total = data.count ?? results.length
      hasMore = allResults.length < total
      page++
    }
    const mainCats = Array.from(new Set(allResults.map((c: any) => c.资产类目)))
    categoryOptions.value = [
      { value: '', label: '全部类目' },
      ...mainCats.map((cat: string) => ({ value: cat, label: cat })),
    ]
  } catch (error) {
    console.error('Failed to fetch categories:', error)
  }
}

// ── 批量导入（两段式增量：预览 → 确认生成调整单） ──
const showImportModal = ref(false)

// ── 导出 ──
async function handleExport() {
  try {
    const { data } = await exportAssetStocks({
      branch: filters.value.branch || undefined,
      category: filters.value.category || undefined,
      keyword: filters.value.keyword || undefined,
    } as Record<string, string>)
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = `资产汇总_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

function resetFilters() {
  filters.value = { branch: '', category: '', keyword: '', sufficient: '' }
  pagination.value.page = 1
  fetchStocks()
}

function handlePaginationChange(page: number, pageSize: number) {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchStocks()
}

watch(filters, () => {
  pagination.value.page = 1
  fetchStocks()
}, { deep: true })

onMounted(() => {
  fetchStocks()
  fetchBranches()
  fetchCategories()
})
</script>

<template>
  <div class="asset-summary-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">资产汇总台账</h1>
        <p class="page-desc">库存唯一事实源（共{{ pagination.total }}行）——数量变动经流转单/调整单</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="handleExport">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导出
        </button>
        <button v-if="canImport" class="btn-secondary" @click="showImportModal = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          增量导入
        </button>
        <button class="btn-secondary" @click="recordsVisible = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          调整记录
        </button>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item search">
          <svg class="filter-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="搜索资产编号、名称、规格、分公司..."
            class="filter-input"
            aria-label="搜索台账"
          />
        </div>
        <div class="filter-item">
          <select v-model="filters.branch" class="filter-select" aria-label="筛选分公司">
            <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div class="filter-item">
          <select v-model="filters.category" class="filter-select" aria-label="筛选类目">
            <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div class="filter-item">
          <select v-model="filters.sufficient" class="filter-select" aria-label="筛选是否充足">
            <option value="">全部充足状态</option>
            <option value="0">仅不足</option>
            <option value="1">仅充足</option>
          </select>
        </div>
        <button class="filter-reset" @click="resetFilters">重置</button>
      </div>
    </div>

    <!-- 数据表格（行级写唯一出口是调整单——铁律 2 的合规载体） -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-index">序号</th>
            <th>分公司</th>
            <th>资产编号</th>
            <th>资产名称</th>
            <th>规格</th>
            <th>资产类目</th>
            <th>管理方式</th>
            <th>在库</th>
            <th>在用</th>
            <th>回收库</th>
            <th>总量</th>
            <th>警戒线</th>
            <th>是否充足</th>
            <th>实例</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && stocks.length === 0">
            <td colspan="15" class="empty-cell">加载中...</td>
          </tr>
          <tr v-else-if="stocks.length === 0">
            <td colspan="15" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-for="(stock, index) in stocks" :key="stock.id">
            <td class="col-index">{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
            <td class="branch-name">{{ stock.branchName }}</td>
            <td><span class="asset-code">{{ stock.资产编号 }}</span></td>
            <td class="asset-name">{{ stock.资产名称 || '-' }}</td>
            <td>{{ stock.规格 || '-' }}</td>
            <td>{{ stock.资产类目 || '-' }}</td>
            <td>{{ MANAGEMENT_TYPE_LABELS[stock.管理方式 ?? ''] || stock.管理方式 }}</td>
            <td class="col-qty">{{ stock.在库数量 }}</td>
            <td class="col-qty">{{ stock.在用数量 }}</td>
            <td class="col-qty">{{ stock.回收库数量 }}</td>
            <td class="col-qty">{{ stock.总量 ?? (stock.在库数量 + stock.在用数量 + stock.回收库数量) }}</td>
            <td>{{ stock.生效警戒线 ?? stock.警戒线 ?? '-' }}</td>
            <td>
              <span class="sufficient-badge" :class="stock.是否充足 ? 'ok' : 'low'">
                {{ stock.是否充足 ? '是' : '否' }}
              </span>
            </td>
            <td>
              <button
                v-if="stock.管理方式 === 'instance'"
                class="drill-btn"
                type="button"
                @click="openDrill(stock)"
              >下钻实例</button>
              <span v-else class="dim">—</span>
            </td>
            <td>
              <button
                v-if="canAdjust"
                class="drill-btn"
                type="button"
                @click="openAdjust(stock)"
                >调整</button>
              <span v-else class="dim">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination
      :total="pagination.total"
      :current-page="pagination.page"
      :page-size="pagination.pageSize"
      @change="handlePaginationChange"
    />

    <SummaryImportDialog
      :visible="showImportModal"
      @close="showImportModal = false"
      @success="fetchStocks"
    />

    <AdjustDialog
      :visible="adjustVisible"
      :stock="adjustStock"
      @close="adjustVisible = false"
      @success="fetchStocks"
    />

    <AdjustRecordsDialog
      :visible="recordsVisible"
      @close="recordsVisible = false"
    />

    <!-- 实例下钻抽屉：该（分公司×品目）实例档案 -->
    <el-drawer v-model="drillVisible" title="实例下钻" size="620px">
      <div v-if="drillLoading" class="drill-empty">加载中...</div>
      <template v-else-if="drillStock">
        <div class="drill-head">
          <div class="drill-code">{{ drillStock.资产编号 }}</div>
          <div class="drill-meta">{{ drillStock.资产名称 }} · {{ drillStock.branchName }} · 在库 {{ drillStock.在库数量 }} / 在用 {{ drillStock.在用数量 }} / 回收库 {{ drillStock.回收库数量 }}</div>
        </div>
        <table class="data-table drill-table">
          <thead>
            <tr><th>内部编号</th><th>序列号</th><th>状态</th><th>使用人</th><th>生平</th></tr>
          </thead>
          <tbody>
            <tr v-for="inst in drillInstances" :key="inst.id">
              <td><span class="asset-code">{{ inst.内部编号 }}</span></td>
              <td>{{ inst.序列号 || '待补录' }}</td>
              <td>{{ inst.当前状态 }}</td>
              <td>{{ inst.使用人 || '-' }}</td>
              <td><a class="drill-link" @click.prevent="goTimeline(inst.内部编号)">查看</a></td>
            </tr>
            <tr v-if="drillInstances.length === 0">
              <td colspan="5" class="empty-cell">暂无实例档案（新采购入库后自动生成）</td>
            </tr>
          </tbody>
        </table>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.asset-summary-page {
  max-width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
  flex-shrink: 0;
}

.header-info {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.page-desc {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: var(--space-3);
}

.btn-secondary,
.btn-primary {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 38px;
  padding: 0 var(--space-4);
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-secondary {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn-secondary:hover {
  border-color: var(--color-primary-300);
}

.btn-primary {
  background: var(--color-primary-500);
  border: 1px solid var(--color-primary-500);
  color: white;
}

.btn-primary:hover {
  background: var(--color-primary-600);
}

.btn-secondary svg,
.btn-primary svg {
  width: 16px;
  height: 16px;
}

/* 筛选区 */
.filter-section {
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.filter-row {
  display: flex;
  gap: var(--space-3);
}

.filter-item.search {
  flex: 1;
  position: relative;
}

.filter-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
}

.filter-input {
  width: 100%;
  height: 38px;
  padding: 0 var(--space-4) 0 38px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
}

.filter-select {
  height: 38px;
  padding: 0 var(--space-3);
  min-width: 140px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
}

.filter-reset {
  height: 38px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
  cursor: pointer;
}

/* 表格 */
.table-container {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  overflow: auto;
  flex: 1;
  min-height: 200px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table th {
  background: var(--color-bg-elevated);
  padding: var(--space-3) var(--space-3);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.data-table td {
  padding: var(--space-3) var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-light);
  white-space: nowrap;
}

.data-table tbody tr:hover {
  background: var(--color-bg-elevated);
}

.col-index {
  width: 56px;
  text-align: center;
  color: var(--color-text-tertiary);
}

.col-qty {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.branch-name {
  color: var(--color-text-secondary);
}

.asset-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  padding: 2px 8px;
  border-radius: 4px;
}

.asset-name {
  font-weight: 500;
}

.sufficient-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: var(--text-xs);
  font-weight: 500;
}

.sufficient-badge.ok {
  background: var(--color-primary-100);
  color: var(--color-success);
}

.sufficient-badge.low {
  background: oklch(0.92 0.1 25);
  color: var(--color-danger);
}

.empty-cell {
  text-align: center;
  padding: var(--space-8) 0;
  color: var(--color-text-tertiary);
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-3);
  }
}
</style>

<style scoped>
.drill-btn { padding: 4px 10px; background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 6px; color: var(--color-primary-600); font-size: 12px; cursor: pointer; }
.drill-btn:hover { background: var(--color-primary-100); }
.dim { color: var(--color-text-tertiary); }
.drill-head { display: flex; flex-direction: column; gap: 4px; margin-bottom: var(--space-4); }
.drill-code { font-family: var(--font-mono); font-size: 16px; font-weight: 600; color: var(--color-primary-600); }
.drill-meta { font-size: 13px; color: var(--color-text-secondary); }
.drill-table th, .drill-table td { padding: var(--space-2) var(--space-3); }
.drill-empty { text-align: center; color: var(--color-text-tertiary); padding: var(--space-8); }
.drill-link { color: var(--color-primary-600); cursor: pointer; font-size: 13px; }
.drill-link:hover { text-decoration: underline; }
</style>
