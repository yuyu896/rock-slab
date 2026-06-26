<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getAssets, updateAsset, deleteAsset, exportAssets } from '@/api/assets'
import { getCategories } from '@/api/categories'
import { getBranches } from '@/api/branches'
import { getTransfers } from '@/api/transfers'
import { handleApiError } from '@/utils/request'
import { formatMoney } from '@/utils/format'
import { ASSET_STATUS_OPTIONS } from '@/constants'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import type { Asset, Category, Transfer } from '@/types'
import BasePagination from '@/components/BasePagination.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import AssetDetailDrawer from './assets/AssetDetailDrawer.vue'
import AssetImportDialog from './assets/AssetImportDialog.vue'
import AssetPrintDialog from './assets/AssetPrintDialog.vue'
import AssetEditDrawer from './assets/AssetEditDrawer.vue'

const router = useRouter()
const { canManageAssets } = usePermission()

// 筛选条件
const filters = ref({
  branch: '',
  category: '',
  status: '',
  keyword: ''
})

// 快捷筛选
const quickFilter = ref('')

function applyQuickFilter(type: string) {
  quickFilter.value = type
  if (type === 'lowStock') {
    filters.value.status = ''
  } else if (type === 'newMonth') {
    filters.value.status = ''
  } else {
    filters.value.status = ''
  }
}

// 分页
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 加载状态
const loading = ref(false)

// 选中的资产
const selectedAssets = ref<string[]>([])

// 资产数据
const assets = ref<Asset[]>([])

// 下拉选项
const statusOptions = ASSET_STATUS_OPTIONS
const categoryOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部分类' }])
const branchOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部分公司' }])
const allCategories = ref<Category[]>([])

// ===== 资产详情抽屉 =====
const showDetailDrawer = ref(false)
const detailAsset = ref<Asset | null>(null)
const detailTransfers = ref<Transfer[]>([])
const detailLoading = ref(false)

async function viewDetail(asset: Asset) {
  detailAsset.value = asset
  showDetailDrawer.value = true
  detailLoading.value = true
  try {
    // 获取流转历史
    const { data } = await getTransfers({ pageSize: 50 })
    detailTransfers.value = data.results || []
  } catch {
    detailTransfers.value = []
  } finally {
    detailLoading.value = false
  }
}

// ===== 编辑资产 =====
const showEditDrawer = ref(false)
const editingAsset = ref<Asset | null>(null)

function openEdit(asset: Asset) {
  editingAsset.value = { ...asset }
  showEditDrawer.value = true
}

async function handleUpdateAsset(payload: Partial<Asset>) {
  if (!editingAsset.value) return
  try {
    await updateAsset(editingAsset.value.id, payload)
    ElMessage.success('资产更新成功')
    showEditDrawer.value = false
    editingAsset.value = null
    await fetchAssets()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// ===== 删除资产 =====
async function handleDelete(asset: Asset) {
  try {
    await ElMessageBox.confirm(
      '确定删除该资产？此操作不可恢复',
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' },
    )
    await deleteAsset(asset.id)
    ElMessage.success('资产已删除')
    await fetchAssets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// ===== 新增资产（跳转独立页面）=====
function openCreatePage() {
  router.push('/assets/list/create')
}

// ===== 批量导入 =====
const showImportModal = ref(false)

function openImportModal() {
  showImportModal.value = true
}

// ===== 条码打印 =====
const showPrintModal = ref(false)
const printAssets = ref<Asset[]>([])

function handlePrintLabels() {
  if (selectedAssets.value.length === 0) {
    ElMessage.warning('请先选择要打印的资产')
    return
  }
  printAssets.value = assets.value.filter(a => selectedAssets.value.includes(a.id))
  showPrintModal.value = true
}

function printSingleLabel(asset: Asset) {
  printAssets.value = [asset]
  showPrintModal.value = true
}

// 获取状态样式

// 全选/取消全选
const selectAll = computed({
  get: () => assets.value.length > 0 && selectedAssets.value.length === assets.value.length,
  set: (val: boolean) => {
    selectedAssets.value = val ? assets.value.map(a => a.id) : []
  }
})

// 切换选中
const toggleSelect = (id: string) => {
  const index = selectedAssets.value.indexOf(id)
  if (index > -1) {
    selectedAssets.value.splice(index, 1)
  } else {
    selectedAssets.value.push(id)
  }
}

// 获取资产列表
async function fetchAssets() {
  loading.value = true
  try {
    const { data } = await getAssets({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      branch: filters.value.branch || undefined,
      category: filters.value.category || undefined,
      status: filters.value.status || undefined,
      keyword: filters.value.keyword || undefined,
    })
    assets.value = data.results
    pagination.value.total = data.count
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

// 获取分类选项（加载全部分类数据）
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
    allCategories.value = allResults
    const mainCats = new Set(allResults.map((c: any) => c.资产类目))
    categoryOptions.value = [
      { value: '', label: '全部分类' },
      ...Array.from(mainCats).map((cat: string) => ({ value: cat, label: cat }))
    ]
  } catch (error) {
    console.error('Failed to fetch categories:', error)
  }
}

// 获取分公司选项
async function fetchBranches() {
  try {
    const { data } = await getBranches()
    branchOptions.value = [
      { value: '', label: '全部分公司' },
      ...data.map(b => ({ value: b.name, label: b.name }))
    ]
  } catch (error) {
    console.error('Failed to fetch branches:', error)
  }
}

// 导出数据
const handleExport = async () => {
  try {
    const { data } = await exportAssets({ branch: filters.value.branch || undefined })
    const blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `资产列表_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 重置筛选
const resetFilters = () => {
  filters.value = {
    branch: '',
    category: '',
    status: '',
    keyword: ''
  }
  quickFilter.value = ''
  pagination.value.page = 1
  fetchAssets()
}

// 翻页
const handlePaginationChange = (page: number, pageSize: number) => {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchAssets()
}

// 监听筛选条件变化
watch(filters, () => {
  pagination.value.page = 1
  fetchAssets()
}, { deep: true })

// 初始化
onMounted(() => {
  fetchAssets()
  fetchCategories()
  fetchBranches()
})
</script>

<template>
  <div class="asset-list-page">
    <!-- 页面标题区 -->
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">资产列表</h1>
        <p class="page-desc">共{{ pagination.total }}项资产</p>
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
        <button class="btn-secondary" @click="openImportModal">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          批量导入
        </button>
        <button class="btn-primary" @click="openCreatePage">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新增资产
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
            placeholder="搜索资产编号、名称、使用人..."
            class="filter-input"
            aria-label="搜索资产"
          />
        </div>

        <div class="filter-item">
          <select
            v-model="filters.branch"
            class="filter-select"
            aria-label="筛选分公司"
          >
            <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="filter-item">
          <select
            v-model="filters.category"
            class="filter-select"
            aria-label="筛选分类"
          >
            <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="filter-item">
          <select
            v-model="filters.status"
            class="filter-select"
            aria-label="筛选状态"
          >
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <button class="filter-reset" @click="resetFilters" aria-label="重置筛选条件">重置</button>
      </div>

      <!-- 快捷筛选标签 -->
      <div class="quick-filters">
        <span class="quick-filter-label">快捷筛选：</span>
        <button class="quick-filter-tag" :class="{ active: quickFilter === 'lowStock' }" @click="applyQuickFilter('lowStock')">库存不足</button>
        <button class="quick-filter-tag" :class="{ active: quickFilter === 'newMonth' }" @click="applyQuickFilter('newMonth')">本月新增</button>
        <button class="quick-filter-tag" :class="{ active: quickFilter === '' }" @click="applyQuickFilter('')">全部</button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedAssets.length > 0" class="batch-actions">
      <div class="batch-info">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 11 12 14 22 4"/>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
        </svg>
        <span>已选择 {{ selectedAssets.length }} 项</span>
      </div>
      <div class="batch-buttons">
        <button class="batch-btn" @click="handlePrintLabels">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 6 2 18 2 18 9"/>
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
            <rect x="6" y="14" width="12" height="8"/>
          </svg>
          打印标签
        </button>
        <button class="batch-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
            <line x1="1" y1="10" x2="23" y2="10"/>
          </svg>
          批量调拨
        </button>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-checkbox">
              <input
                type="checkbox"
                v-model="selectAll"
                class="checkbox"
              />
            </th>
            <th class="col-index">序号</th>
            <th class="col-branch">分公司</th>
            <th class="col-code">资产编号</th>
            <th class="col-category">资产类目</th>
            <th class="col-name">资产名称</th>
            <th class="col-spec">规格</th>
            <th class="col-qty">数量</th>
            <th class="col-amount">购入金额</th>
            <th class="col-dept">所属部门</th>
            <th class="col-user">使用人</th>
            <th class="col-status">状态</th>
            <th class="col-stock">库存</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="asset in assets"
            :key="asset.id"
            :class="{ selected: selectedAssets.includes(asset.id) }"
          >
            <td class="col-checkbox">
              <input
                type="checkbox"
                :checked="selectedAssets.includes(asset.id)"
                @change="toggleSelect(asset.id)"
                class="checkbox"
              />
            </td>
            <td class="col-index">{{ asset.序号 }}</td>
            <td class="col-branch">{{ asset.分公司 }}</td>
            <td class="col-code">
              <span class="asset-code">{{ asset.资产编号 }}</span>
            </td>
            <td class="col-category">
              <span class="category-tag">{{ asset.资产类目 }}</span>
              <span class="sub-category">{{ asset.物品分类 }}</span>
            </td>
            <td class="col-name">
              <div class="asset-name-cell">
                <span class="asset-name">{{ asset.资产名称 }}</span>
                <span v-if="asset.是否租用" class="rental-badge">租用</span>
              </div>
            </td>
            <td class="col-spec">{{ asset.规格 }}</td>
            <td class="col-qty">{{ asset.数量 }}</td>
            <td class="col-amount">{{ formatMoney(asset.购入金额 ?? 0) }}</td>
            <td class="col-dept">{{ asset.所属部门 || '-' }}</td>
            <td class="col-user">{{ asset.使用人 || '-' }}</td>
            <td class="col-status">
              <StatusBadge :status="asset.当前状态" />
            </td>
            <td class="col-stock">
              <div class="stock-cell">
                <span :class="{ 'low-stock': !asset.是否充足 }">{{ asset.数量 }}</span>
                <span class="stock-threshold">/ {{ asset.警戒线 }}</span>
              </div>
            </td>
            <td class="col-actions">
              <div class="action-buttons">
                <button class="action-btn" title="查看详情" @click="viewDetail(asset)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
                <button class="action-btn" title="打印标签" @click="printSingleLabel(asset)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 6 2 18 2 18 9"/>
                    <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                    <rect x="6" y="14" width="12" height="8"/>
                  </svg>
                </button>
                <button v-if="canManageAssets" class="action-btn" title="编辑" @click="openEdit(asset)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
                <button v-if="canManageAssets" class="action-btn danger" title="删除" @click="handleDelete(asset)">
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

    <!-- 分页 -->
    <BasePagination
      :total="pagination.total"
      :current-page="pagination.page"
      :page-size="pagination.pageSize"
      @change="handlePaginationChange"
    />

    <!-- 资产详情抽屉 -->
    <!-- 资产详情抽屉 -->
    <AssetDetailDrawer
      v-if="showDetailDrawer"
      :asset="detailAsset"
      :transfers="detailTransfers"
      :loading="detailLoading"
      @close="showDetailDrawer = false"
    />

    <!-- 编辑资产抽屉 -->
    <AssetEditDrawer
      v-if="showEditDrawer && editingAsset"
      :visible="showEditDrawer"
      :asset="editingAsset"
      :branch-options="branchOptions"
      @close="showEditDrawer = false"
      @update="handleUpdateAsset"
    />

    <!-- 标签打印弹窗 -->
    <AssetPrintDialog
      :visible="showPrintModal"
      :assets="printAssets"
      @close="showPrintModal = false"
    />

    <!-- 批量导入弹窗 -->
    <AssetImportDialog :visible="showImportModal" @close="showImportModal = false" @success="fetchAssets" />
  </div>
</template>

<style scoped>
.asset-list-page {
  max-width: 100%;
}

/* 页面头部 */
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

/* 筛选区 */
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
  margin-bottom: var(--space-3);
}

.filter-item {
  position: relative;
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
  transition: all var(--transition-fast);
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
  transition: color var(--transition-fast);
}

.filter-reset:hover {
  color: var(--color-primary-500);
}

/* 快捷筛选 */
.quick-filters {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.quick-filter-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.quick-filter-tag {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.quick-filter-tag:hover {
  border-color: var(--color-primary-300);
  color: var(--color-primary-500);
}

.quick-filter-tag.active {
  background: var(--color-primary-50);
  border-color: var(--color-primary-300);
  color: var(--color-primary-600);
}

/* 批量操作栏 */
.batch-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-primary-50);
  border: 1px solid var(--color-primary-200);
  border-radius: 8px;
  margin-bottom: var(--space-4);
}

.batch-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-primary-600);
}

.batch-info svg {
  width: 18px;
  height: 18px;
}

.batch-buttons {
  display: flex;
  gap: var(--space-2);
}

.batch-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.batch-btn:hover {
  border-color: var(--color-primary-300);
  color: var(--color-primary-500);
}

.batch-btn.danger:hover {
  border-color: oklch(0.85 0.10 25);
  color: var(--color-danger);
}

.batch-btn svg {
  width: 16px;
  height: 16px;
}

/* 表格 */
.table-container {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  background: var(--color-bg-elevated);
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

.data-table tbody tr.selected {
  background: var(--color-primary-50);
}

/* 复选框 */
.checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--color-primary-500);
}

/* 资产编号 */
.asset-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  padding: 2px 8px;
  border-radius: 4px;
}

/* 分类 */
.category-tag {
  display: inline-block;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-right: var(--space-2);
}

.sub-category {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 资产名称 */
.asset-name-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.asset-name {
  font-weight: 500;
}

.rental-badge {
  font-size: var(--text-xs);
  background: oklch(0.94 0.06 85);
  color: oklch(0.60 0.12 85);
  padding: 2px 6px;
  border-radius: 4px;
}

/* 状态 */
.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: 500;
}

/* 库存 */
.stock-cell {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
}

.low-stock {
  color: var(--color-danger);
  font-weight: 600;
}

.stock-threshold {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: var(--space-1);
}

.action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background: var(--color-bg-elevated);
  color: var(--color-primary-500);
}

.action-btn.danger:hover {
  background: oklch(0.97 0.02 25);
  color: var(--color-danger);
}

.action-btn:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
  background: var(--color-primary-50);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

/* 分页 */
.pagination-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) 0;
  margin-top: var(--space-4);
}

.pagination-info {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.page-btn {
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled):not(.active) {
  border-color: var(--color-primary-300);
  color: var(--color-primary-500);
}

.page-btn.active {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
  color: white;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-btn svg {
  width: 16px;
  height: 16px;
}

.page-ellipsis {
  color: var(--color-text-tertiary);
  padding: 0 var(--space-2);
}

.size-select {
  height: 32px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
}

/* 响应式 */
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
