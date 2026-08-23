<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getAssetStocks, exportAssetStocks } from '@/api/assets'
import { getBranches } from '@/api/branches'
import { getCategories } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import type { AssetStock } from '@/types'
import BasePagination from '@/components/BasePagination.vue'
import SummaryImportDialog from './SummaryImportDialog.vue'

const { can } = usePermission()
const canImport = can('adjust_ledger') || can('manage_assets')

const filters = ref({
  branch: '',
  category: '',
  keyword: '',
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
  filters.value = { branch: '', category: '', keyword: '' }
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
        <button class="filter-reset" @click="resetFilters">重置</button>
      </div>
    </div>

    <!-- 数据表格（13 列，无行级写操作——铁律 2） -->
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
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && stocks.length === 0">
            <td colspan="13" class="empty-cell">加载中...</td>
          </tr>
          <tr v-else-if="stocks.length === 0">
            <td colspan="13" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-for="(stock, index) in stocks" :key="stock.id">
            <td class="col-index">{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
            <td class="branch-name">{{ stock.branchName }}</td>
            <td><span class="asset-code">{{ stock.资产编号 }}</span></td>
            <td class="asset-name">{{ stock.资产名称 || '-' }}</td>
            <td>{{ stock.规格 || '-' }}</td>
            <td>{{ stock.资产类目 || '-' }}</td>
            <td>{{ stock.管理方式 === 'instance' ? '实例管理' : '数量管理' }}</td>
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
