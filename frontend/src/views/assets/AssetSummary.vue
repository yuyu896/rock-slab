<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import {
  getAssetStocks, createAssetStock, updateAssetStock, deleteAssetStock,
  importAssetStocks, exportAssetStocks,
} from '@/api/assets'
import { getBranches } from '@/api/branches'
import { getCategories } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import type { AssetStock } from '@/types'
import BasePagination from '@/components/BasePagination.vue'
import SummaryEditDrawer from './SummaryEditDrawer.vue'
import SummaryImportDialog from './SummaryImportDialog.vue'
import SummaryFillDialog from './SummaryFillDialog.vue'

const { canManageAssets } = usePermission()

const filters = ref({
  branch: '',
  category: '',
  keyword: '',
})

const pagination = ref({ page: 1, pageSize: 20, total: 0 })
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
      { value: '', label: '全部分公司' },
      ...data.map((b: any) => ({ value: b.name, label: b.name })),
    ]
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

// ── 新增/编辑 ──
const showEditDrawer = ref(false)
const editingStock = ref<AssetStock | null>(null)

function openCreate() {
  editingStock.value = null
  showEditDrawer.value = true
}

function openEdit(stock: AssetStock) {
  editingStock.value = { ...stock }
  showEditDrawer.value = true
}

async function handleEditSubmit(payload: Partial<AssetStock>, id?: string) {
  try {
    if (id) {
      await updateAssetStock(id, payload)
      ElMessage.success('台账已更新')
    } else {
      await createAssetStock(payload)
      ElMessage.success('台账已新增')
    }
    showEditDrawer.value = false
    editingStock.value = null
    await fetchStocks()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// ── 删除 ──
async function handleDelete(stock: AssetStock) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${stock.分公司} / ${stock.资产编号}」这条台账？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await deleteAssetStock(stock.id)
    ElMessage.success('删除成功')
    await fetchStocks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// ── 批量导入 ──
const showImportModal = ref(false)

// ── 填入 ──
const showFillDialog = ref(false)
const fillingStock = ref<AssetStock | null>(null)

function openFill(stock: AssetStock) {
  fillingStock.value = stock
  showFillDialog.value = true
}

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
  <div class="asset-summary-page">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">资产汇总</h1>
        <p class="page-desc">共{{ pagination.total }}条库存记录</p>
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
        <button v-if="canManageAssets" class="btn-secondary" @click="showImportModal = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          批量导入
        </button>
        <button v-if="canManageAssets" class="btn-primary" @click="openCreate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新增
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
            placeholder="搜索资产编号、资产名称、分公司、规格..."
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

    <!-- 数据表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-index">序号</th>
            <th>分公司</th>
            <th>资产编号</th>
            <th>资产类目</th>
            <th>物品分类</th>
            <th>资产名称</th>
            <th>数量</th>
            <th>规格</th>
            <th>警戒线</th>
            <th>是否充足</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && stocks.length === 0">
            <td colspan="11" class="empty-cell">加载中...</td>
          </tr>
          <tr v-else-if="stocks.length === 0">
            <td colspan="11" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-for="(stock, index) in stocks" :key="stock.id">
            <td class="col-index">{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
            <td class="branch-name">{{ stock.分公司 }}</td>
            <td><span class="asset-code">{{ stock.资产编号 }}</span></td>
            <td>{{ stock.资产类目 || '-' }}</td>
            <td>{{ stock.物品分类 || '-' }}</td>
            <td class="asset-name">{{ stock.资产名称 || '-' }}</td>
            <td class="col-qty">{{ stock.数量 }}</td>
            <td>{{ stock.规格 || '-' }}</td>
            <td>{{ stock.警戒线 ?? '-' }}</td>
            <td>
              <span class="sufficient-badge" :class="stock.是否充足 ? 'ok' : 'low'">
                {{ stock.是否充足 ? '是' : '否' }}
              </span>
            </td>
            <td class="col-actions">
              <div class="action-buttons">
                <button class="action-btn" title="填入资产明细/固定资产" @click="openFill(stock)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </button>
                <button v-if="canManageAssets" class="action-btn" title="编辑" @click="openEdit(stock)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
                <button v-if="canManageAssets" class="action-btn danger" title="删除" @click="handleDelete(stock)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
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

    <SummaryEditDrawer
      v-if="showEditDrawer"
      :visible="showEditDrawer"
      :stock="editingStock"
      :branch-options="branchOptions"
      @close="showEditDrawer = false"
      @submit="handleEditSubmit"
    />

    <SummaryImportDialog
      :visible="showImportModal"
      @close="showImportModal = false"
      @success="fetchStocks"
    />

    <SummaryFillDialog
      :visible="showFillDialog"
      :stock="fillingStock"
      @close="showFillDialog = false"
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
  transition: all var(--transition-fast);
}

.btn-secondary {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn-secondary:hover {
  border-color: var(--color-primary-300);
  background: var(--color-bg-elevated);
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

.filter-section {
  background: var(--color-bg-card);
  border-radius: 12px;
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  border: 1px solid var(--color-border);
}

.filter-row {
  display: flex;
  gap: var(--space-3);
}

.filter-item {
  position: relative;
}

.filter-item.search {
  flex: 1;
}

.filter-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: var(--color-text-tertiary);
}

.filter-input {
  width: 100%;
  height: 38px;
  padding: 0 var(--space-4) 0 38px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.filter-input:focus {
  outline: none;
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}

.filter-select {
  height: 38px;
  padding: 0 var(--space-4);
  padding-right: var(--space-8);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  min-width: 140px;
}

.filter-reset {
  height: 38px;
  padding: 0 var(--space-4);
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
}

.filter-reset:hover {
  color: var(--color-primary-500);
}

.table-container {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  overflow-x: auto;
  overflow-y: auto;
  max-height: calc(100vh - 340px);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--color-bg-elevated);
}

.data-table th {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.data-table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: middle;
}

.data-table tbody tr {
  transition: background var(--transition-fast);
}

.data-table tbody tr:hover {
  background: var(--color-bg-elevated);
}

.empty-cell {
  text-align: center;
  color: var(--color-text-tertiary);
  padding: var(--space-8) 0 !important;
}

.col-index {
  width: 60px;
}

.col-qty {
  font-weight: 600;
}

.branch-name {
  font-weight: 500;
}

.asset-name {
  font-weight: 500;
}

.asset-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  padding: 2px 8px;
  border-radius: 4px;
}

.sufficient-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: 600;
}

.sufficient-badge.ok {
  background: var(--color-status-in-stock-bg);
  color: var(--color-status-in-stock-text);
}

.sufficient-badge.low {
  background: var(--color-danger);
  color: white;
}

.action-buttons {
  display: flex;
  gap: var(--space-1);
}

.action-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 4px;
  border-radius: 6px;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.action-btn.danger:hover {
  color: var(--color-danger);
  background: var(--color-bg-elevated);
}

.action-btn svg {
  width: 18px;
  height: 18px;
}

@media (max-width: 1200px) {
  .data-table {
    display: block;
    overflow-x: auto;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-4);
  }

  .filter-row {
    flex-wrap: wrap;
  }

  .filter-item.search {
    flex: 1 1 100%;
  }
}
</style>
