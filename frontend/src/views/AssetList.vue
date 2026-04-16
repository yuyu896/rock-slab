<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { getAssets, createAsset, exportAssets, importAssets } from '@/api/assets'
import { getCategories } from '@/api/categories'
import { getBranches } from '@/api/branches'
import { getTransfers } from '@/api/transfers'
import { handleApiError } from '@/utils/request'
import { formatMoney, formatDate } from '@/utils/format'
import { ASSET_STATUS_OPTIONS, ASSET_STATUS_COLORS } from '@/constants'
import { ElMessage } from 'element-plus'
import type { Asset, Category, Transfer } from '@/types'
import JsBarcode from 'jsbarcode'

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
    // 库存不足的筛选需要后端支持，暂时用关键词过滤
  } else if (type === 'repair') {
    filters.value.status = '维修中'
  } else if (type === 'newMonth') {
    filters.value.status = ''
    // 本月新增需要后端支持
  } else {
    filters.value.status = ''
  }
}

// 分页
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
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

// ===== 新增资产弹窗 =====
const showCreateModal = ref(false)
const creating = ref(false)
const newAsset = ref<Partial<Asset>>({
  分公司: '',
  资产编号: '',
  资产类目: '',
  物品分类: '',
  资产名称: '',
  规格: '',
  数量: 1,
  单价: 0,
  供应商: '',
  是否租用: false,
  所属部门: '',
  使用人: '',
  备注: '',
})

// 当前选中分类的属性模板
const currentCategoryAttrs = computed(() => {
  if (!newAsset.value.物品分类) return []
  const cat = allCategories.value.find(c => c.物品分类 === newAsset.value.物品分类)
  if (!cat || !(cat as any).attributes) return []
  return (cat as any).attributes
})

// 动态属性值
const dynamicAttrValues = ref<Record<string, string>>({})

function openCreateModal() {
  newAsset.value = {
    分公司: '',
    资产编号: '',
    资产类目: '',
    物品分类: '',
    资产名称: '',
    规格: '',
    数量: 1,
    单价: 0,
    供应商: '',
    是否租用: false,
    所属部门: '',
    使用人: '',
    备注: '',
  }
  dynamicAttrValues.value = {}
  showCreateModal.value = true
}

async function submitCreateAsset() {
  const a = newAsset.value
  if (!a.分公司 || !a.资产编号 || !a.资产名称 || !a.资产类目 || !a.物品分类 || !a.数量) {
    ElMessage.warning('请填写所有必填字段')
    return
  }
  creating.value = true
  try {
    const payload: Partial<Asset> = {
      ...a,
      购入金额: (a.数量 ?? 0) * (a.单价 ?? 0),
      当前状态: '在库',
      入库日期: new Date().toISOString().slice(0, 10),
    }
    // 合并动态属性到备注字段
    if (Object.keys(dynamicAttrValues.value).length > 0) {
      const attrParts = Object.entries(dynamicAttrValues.value).map(([k, v]) => `${k}:${v}`)
      payload.备注 = (a.备注 ? a.备注 + '\n' : '') + '[属性]' + attrParts.join('; ')
    }
    await createAsset(payload)
    ElMessage.success('资产创建成功')
    showCreateModal.value = false
    await fetchAssets()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    creating.value = false
  }
}

// ===== 批量导入 =====
const showImportModal = ref(false)
const importLoading = ref(false)
const importResult = ref<{ imported: number; errors: string[] } | null>(null)

function openImportModal() {
  importResult.value = null
  importLoading.value = false
  showImportModal.value = true
}

async function handleDownloadTemplate() {
  try {
    const { data } = await exportAssets()
    const blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '资产导入模板.xlsx'
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

async function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  // 校验文件格式
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext !== 'xlsx' && ext !== 'xls') {
    ElMessage.warning('请上传 Excel 文件（.xlsx 或 .xls）')
    input.value = ''
    return
  }

  importLoading.value = true
  importResult.value = null
  try {
    const { data } = await importAssets(file)
    importResult.value = data

    if (data.errors.length === 0) {
      ElMessage.success(`成功导入 ${data.imported} 条资产`)
      setTimeout(() => {
        showImportModal.value = false
        fetchAssets()
      }, 1200)
    }
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    importLoading.value = false
    input.value = ''
  }
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
  nextTick(() => renderBarcodes())
}

function printSingleLabel(asset: Asset) {
  printAssets.value = [asset]
  showPrintModal.value = true
  nextTick(() => renderBarcodes())
}

function renderBarcodes() {
  nextTick(() => {
    printAssets.value.forEach(asset => {
      const el = document.getElementById(`barcode-${asset.id}`)
      if (el) {
        try {
          JsBarcode(el, asset.资产编号 || '', {
            format: 'CODE128',
            width: 2,
            height: 60,
            displayValue: true,
            fontSize: 14,
            margin: 5,
          })
        } catch {
          // barcode generation failed silently
        }
      }
    })
  })
}

function executePrint() {
  window.print()
}

// 获取状态样式
const getStatusStyle = (status: string) => {
  return ASSET_STATUS_COLORS[status as keyof typeof ASSET_STATUS_COLORS] || { bg: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }
}

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
const handlePageChange = (page: number) => {
  pagination.value.page = page
  fetchAssets()
}

// 获取物品分类选项（根据已选资产类目过滤，去重）
const itemCategoryOptions = computed(() => {
  if (!newAsset.value.资产类目) return []
  const seen = new Set<string>()
  return allCategories.value
    .filter(c => c.资产类目 === newAsset.value.资产类目)
    .filter(c => {
      if (seen.has(c.物品分类)) return false
      seen.add(c.物品分类)
      return true
    })
})

// 新增弹窗 - 资产类目选项（从数据库动态获取）
const createMainCategoryOptions = computed(() => {
  return categoryOptions.value.filter(o => o.value !== '')
})

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
        <button class="btn-primary" @click="openCreateModal">
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
        <button class="quick-filter-tag" :class="{ active: quickFilter === 'repair' }" @click="applyQuickFilter('repair')">待维修</button>
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
        <button class="batch-btn danger">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          批量报废
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
              <span
                class="status-badge"
                :style="{
                  background: getStatusStyle(asset.当前状态).bg,
                  color: getStatusStyle(asset.当前状态).color
                }"
              >
                {{ asset.当前状态 }}
              </span>
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
                <button class="action-btn" title="更多">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="1"/>
                    <circle cx="19" cy="12" r="1"/>
                    <circle cx="5" cy="12" r="1"/>
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination-section">
      <div class="pagination-info">
        显示 1-20 条，共 {{ pagination.total }} 条
      </div>
      <div class="pagination-controls">
        <button class="page-btn" :disabled="pagination.page === 1">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <button class="page-btn active">1</button>
        <button class="page-btn">2</button>
        <button class="page-btn">3</button>
        <span class="page-ellipsis">...</span>
        <button class="page-btn">18</button>
        <button class="page-btn" :disabled="pagination.page === 18">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>
      <div class="pagination-size">
        <select class="size-select">
          <option value="20">20条/页</option>
          <option value="50">50条/页</option>
          <option value="100">100条/页</option>
        </select>
      </div>
    </div>

    <!-- 资产详情抽屉 -->
    <div v-if="showDetailDrawer" class="drawer-overlay" @click.self="showDetailDrawer = false">
      <div class="drawer-panel">
        <div class="drawer-header">
          <h3>资产详情</h3>
          <button class="drawer-close" @click="showDetailDrawer = false">&times;</button>
        </div>
        <div v-if="detailAsset" class="drawer-body">
          <!-- 基本信息 -->
          <div class="detail-section">
            <h4 class="detail-section-title">基本信息</h4>
            <div class="detail-grid">
              <div class="detail-field"><span class="detail-label">资产编号</span><span class="detail-value code">{{ detailAsset.资产编号 }}</span></div>
              <div class="detail-field"><span class="detail-label">资产名称</span><span class="detail-value">{{ detailAsset.资产名称 }}</span></div>
              <div class="detail-field"><span class="detail-label">资产类目</span><span class="detail-value">{{ detailAsset.资产类目 }}</span></div>
              <div class="detail-field"><span class="detail-label">物品分类</span><span class="detail-value">{{ detailAsset.物品分类 }}</span></div>
              <div class="detail-field"><span class="detail-label">规格</span><span class="detail-value">{{ detailAsset.规格 || '-' }}</span></div>
              <div class="detail-field"><span class="detail-label">供应商</span><span class="detail-value">{{ detailAsset.供应商 || '-' }}</span></div>
              <div class="detail-field"><span class="detail-label">采购方式</span><span class="detail-value">{{ detailAsset.是否租用 ? '租用' : '自购' }}</span></div>
              <div class="detail-field"><span class="detail-label">分公司</span><span class="detail-value">{{ detailAsset.分公司 }}</span></div>
              <div class="detail-field"><span class="detail-label">所属部门</span><span class="detail-value">{{ detailAsset.所属部门 || '-' }}</span></div>
              <div class="detail-field"><span class="detail-label">使用人</span><span class="detail-value">{{ detailAsset.使用人 || '-' }}</span></div>
              <div class="detail-field"><span class="detail-label">当前状态</span><span class="detail-value"><span class="status-badge" :style="getStatusStyle(detailAsset.当前状态)">{{ detailAsset.当前状态 }}</span></span></div>
              <div class="detail-field"><span class="detail-label">是否充足</span><span class="detail-value">{{ detailAsset.是否充足 ? '充足' : '不足' }}</span></div>
            </div>
          </div>
          <!-- 数量与价值 -->
          <div class="detail-section">
            <h4 class="detail-section-title">数量与价值</h4>
            <div class="detail-grid">
              <div class="detail-field"><span class="detail-label">数量</span><span class="detail-value">{{ detailAsset.数量 }}</span></div>
              <div class="detail-field"><span class="detail-label">警戒线</span><span class="detail-value">{{ detailAsset.警戒线 ?? '-' }}</span></div>
              <div class="detail-field"><span class="detail-label">单价</span><span class="detail-value">{{ formatMoney(detailAsset.单价 ?? 0) }}</span></div>
              <div class="detail-field"><span class="detail-label">购入金额</span><span class="detail-value">{{ formatMoney(detailAsset.购入金额 ?? 0) }}</span></div>
            </div>
          </div>
          <!-- 日期信息 -->
          <div class="detail-section">
            <h4 class="detail-section-title">日期信息</h4>
            <div class="detail-grid">
              <div class="detail-field"><span class="detail-label">入库日期</span><span class="detail-value">{{ detailAsset.入库日期 || '-' }}</span></div>
              <div class="detail-field"><span class="detail-label">出库日期</span><span class="detail-value">{{ detailAsset.出库日期 || '-' }}</span></div>
            </div>
          </div>
          <!-- 图片 -->
          <div v-if="detailAsset.图片" class="detail-section">
            <h4 class="detail-section-title">资产图片</h4>
            <img :src="detailAsset.图片" alt="资产图片" class="detail-image" />
          </div>
          <!-- 备注 -->
          <div v-if="detailAsset.备注" class="detail-section">
            <h4 class="detail-section-title">备注</h4>
            <p class="detail-remarks">{{ detailAsset.备注 }}</p>
          </div>
          <!-- 流转历史 -->
          <div class="detail-section">
            <h4 class="detail-section-title">流转历史</h4>
            <div v-if="detailLoading" class="detail-loading">加载中...</div>
            <div v-else-if="detailTransfers.length === 0" class="detail-empty">暂无流转记录</div>
            <div v-else class="transfer-timeline">
              <div v-for="t in detailTransfers" :key="t.id" class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                  <div class="timeline-header">
                    <span class="timeline-type">{{ t.action_type === 'assign' ? '领用' : t.action_type === 'return' ? '归还' : t.action_type === 'transfer' ? '调拨' : t.action_type === 'repair' ? '维修' : '报废' }}</span>
                    <span class="timeline-date">{{ t.createdAt }}</span>
                  </div>
                  <div class="timeline-detail">{{ t.资产名称 }} × {{ t.调拨数量 }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增资产弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>新增资产</h3>
          <button class="modal-close" @click="showCreateModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <div class="form-item">
              <label class="form-label">分公司 <span class="required">*</span></label>
              <select v-model="newAsset.分公司" class="form-select">
                <option value="">请选择</option>
                <option v-for="b in branchOptions.filter(b => b.value)" :key="b.value" :value="b.value">{{ b.label }}</option>
              </select>
            </div>
            <div class="form-item">
              <label class="form-label">资产编号 <span class="required">*</span></label>
              <input v-model="newAsset.资产编号" type="text" class="form-input" placeholder="如：A-a00001" />
            </div>
            <div class="form-item">
              <label class="form-label">资产类目 <span class="required">*</span></label>
              <select v-model="newAsset.资产类目" class="form-select" @change="newAsset.物品分类 = ''">
                <option value="">请选择</option>
                <option v-for="opt in createMainCategoryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="form-item">
              <label class="form-label">物品分类 <span class="required">*</span></label>
              <select v-model="newAsset.物品分类" class="form-select">
                <option value="">请选择</option>
                <option v-for="c in itemCategoryOptions" :key="c.id" :value="c.物品分类">{{ c.物品分类 }}</option>
              </select>
            </div>
            <div class="form-item">
              <label class="form-label">资产名称 <span class="required">*</span></label>
              <input v-model="newAsset.资产名称" type="text" class="form-input" placeholder="请输入资产名称" />
            </div>
            <div class="form-item">
              <label class="form-label">规格</label>
              <input v-model="newAsset.规格" type="text" class="form-input" placeholder="规格型号" />
            </div>
            <div class="form-item">
              <label class="form-label">数量 <span class="required">*</span></label>
              <input v-model.number="newAsset.数量" type="number" class="form-input" min="1" />
            </div>
            <div class="form-item">
              <label class="form-label">单价</label>
              <input v-model.number="newAsset.单价" type="number" class="form-input" min="0" step="0.01" />
            </div>
            <div class="form-item">
              <label class="form-label">供应商</label>
              <input v-model="newAsset.供应商" type="text" class="form-input" />
            </div>
            <div class="form-item">
              <label class="form-label">所属部门</label>
              <input v-model="newAsset.所属部门" type="text" class="form-input" />
            </div>
            <div class="form-item">
              <label class="form-label">使用人</label>
              <input v-model="newAsset.使用人" type="text" class="form-input" />
            </div>
            <div class="form-item">
              <label class="form-label">采购方式</label>
              <div class="form-toggle">
                <label><input type="radio" :value="false" v-model="newAsset.是否租用" /> 自购</label>
                <label><input type="radio" :value="true" v-model="newAsset.是否租用" /> 租用</label>
              </div>
            </div>
            <!-- 动态分类属性 -->
            <template v-if="currentCategoryAttrs.length > 0">
              <div v-for="attr in currentCategoryAttrs" :key="attr.name" class="form-item">
                <label class="form-label">{{ attr.name }} <span v-if="attr.required" class="required">*</span></label>
                <input v-if="attr.type === 'text'" v-model="dynamicAttrValues[attr.name]" type="text" class="form-input" :placeholder="'请输入' + attr.name" />
                <input v-else-if="attr.type === 'number'" v-model.number="dynamicAttrValues[attr.name]" type="number" class="form-input" :placeholder="'请输入' + attr.name" />
                <select v-else-if="attr.type === 'select'" v-model="dynamicAttrValues[attr.name]" class="form-select">
                  <option value="">请选择</option>
                  <option v-for="opt in (attr.options || '').split(',')" :key="opt" :value="opt.trim()">{{ opt.trim() }}</option>
                </select>
              </div>
            </template>
            <div class="form-item full">
              <label class="form-label">备注</label>
              <textarea v-model="newAsset.备注" class="form-textarea" rows="3" placeholder="备注信息"></textarea>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showCreateModal = false">取消</button>
          <button class="btn-confirm" @click="submitCreateAsset" :disabled="creating">{{ creating ? '创建中...' : '确定创建' }}</button>
        </div>
      </div>
    </div>

    <!-- 标签打印弹窗 -->
    <div v-if="showPrintModal" class="modal-overlay" @click.self="showPrintModal = false">
      <div class="modal-content print-modal">
        <div class="modal-header">
          <h3>打印标签 ({{ printAssets.length }} 项)</h3>
          <button class="modal-close" @click="showPrintModal = false">&times;</button>
        </div>
        <div class="modal-body print-body">
          <div id="print-area" class="print-labels">
            <div v-for="asset in printAssets" :key="asset.id" class="print-label">
              <div class="label-barcode">
                <svg :id="'barcode-' + asset.id"></svg>
              </div>
              <div class="label-info">
                <div class="label-name">{{ asset.资产名称 }}</div>
                <div class="label-code">{{ asset.资产编号 }}</div>
                <div class="label-branch">{{ asset.分公司 }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showPrintModal = false">关闭</button>
          <button class="btn-confirm" @click="executePrint">打印</button>
        </div>
      </div>
    </div>

    <!-- 批量导入弹窗 -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="showImportModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>批量导入资产</h3>
          <button class="modal-close" @click="showImportModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <!-- 下载模板 -->
          <div class="import-step">
            <div class="import-step-header">
              <span class="import-step-num">1</span>
              <span class="import-step-title">下载导入模板</span>
            </div>
            <p class="import-step-desc">请先下载模板文件，按格式填写资产数据后上传</p>
            <button class="btn-secondary import-template-btn" @click="handleDownloadTemplate">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              下载模板
            </button>
          </div>

          <!-- 上传文件 -->
          <div class="import-step">
            <div class="import-step-header">
              <span class="import-step-num">2</span>
              <span class="import-step-title">上传填写好的 Excel 文件</span>
            </div>
            <label class="import-upload-area" :class="{ 'upload-loading': importLoading }">
              <input type="file" accept=".xlsx,.xls" class="import-file-input" @change="handleImportFile" :disabled="importLoading" />
              <template v-if="importLoading">
                <div class="import-spinner"></div>
                <span>正在导入...</span>
              </template>
              <template v-else>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <span>点击选择文件或拖拽到此处</span>
                <span class="import-upload-hint">支持 .xlsx / .xls 格式</span>
              </template>
            </label>
          </div>

          <!-- 导入结果 -->
          <div v-if="importResult" class="import-result">
            <div class="import-result-header">
              <span :class="importResult.errors.length === 0 ? 'result-success' : 'result-partial'">
                成功导入 {{ importResult.imported }} 条
              </span>
              <span v-if="importResult.errors.length > 0" class="result-fail-count">
                失败 {{ importResult.errors.length }} 条
              </span>
            </div>
            <div v-if="importResult.errors.length > 0" class="import-errors">
              <div v-for="(err, idx) in importResult.errors" :key="idx" class="import-error-item">
                {{ err }}
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showImportModal = false">关闭</button>
        </div>
      </div>
    </div>
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

/* 抽屉 */
.drawer-overlay {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: 520px;
  background: var(--color-bg-card);
  height: 100vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.drawer-header h3 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0;
}

.drawer-close {
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  font-size: 20px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  border-radius: 6px;
}

.drawer-close:hover {
  background: var(--color-bg-elevated);
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-5);
}

.detail-section {
  margin-bottom: var(--space-6);
}

.detail-section-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3) 0;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border-light);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

.detail-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.detail-value {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-weight: 500;
}

.detail-value.code {
  font-family: var(--font-mono);
  color: var(--color-primary-600);
}

.detail-image {
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.detail-remarks {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.detail-loading, .detail-empty {
  text-align: center;
  padding: var(--space-4);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

/* 流转时间线 */
.transfer-timeline {
  padding-left: var(--space-4);
  border-left: 2px solid var(--color-border);
}

.timeline-item {
  position: relative;
  padding-bottom: var(--space-4);
  padding-left: var(--space-4);
}

.timeline-dot {
  position: absolute;
  left: calc(-1 * var(--space-4) - 5px);
  top: 4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary-500);
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timeline-type {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.timeline-date {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.timeline-detail {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-top: 2px;
}

/* 弹窗通用 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 640px;
  max-height: 85vh;
  background: var(--color-bg-card);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
}

.modal-content.print-modal {
  width: 800px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  font-size: 18px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  border-radius: 8px;
}

.modal-close:hover {
  background: var(--color-bg-elevated);
}

.modal-body {
  padding: var(--space-5);
  overflow-y: auto;
}

.print-body {
  max-height: 60vh;
  overflow-y: auto;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-item.full {
  grid-column: span 2;
}

.form-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.required {
  color: var(--color-danger);
}

.form-input, .form-select, .form-textarea {
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.form-textarea {
  height: auto;
  padding: var(--space-3);
  resize: vertical;
}

.form-toggle {
  display: flex;
  gap: var(--space-4);
  height: 40px;
  align-items: center;
}

.form-toggle label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  cursor: pointer;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-5);
  border-top: 1px solid var(--color-border);
}

.btn-cancel, .btn-confirm {
  height: 40px;
  padding: 0 var(--space-5);
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn-confirm {
  background: var(--color-primary-500);
  border: none;
  color: white;
}

.btn-confirm:disabled {
  opacity: 0.6;
}

/* 打印标签 */
.print-labels {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.print-label {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.label-barcode {
  display: flex;
  justify-content: center;
}

.label-info {
  text-align: center;
}

.label-name {
  font-weight: 600;
  font-size: var(--text-sm);
}

.label-code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.label-branch {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 批量导入弹窗 */
.import-step {
  margin-bottom: var(--space-5);
}

.import-step-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.import-step-num {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-500);
  color: white;
  border-radius: 50%;
  font-size: var(--text-xs);
  font-weight: 600;
}

.import-step-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.import-step-desc {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin: 0 0 var(--space-3) 32px;
}

.import-template-btn {
  margin-left: 32px;
}

.import-template-btn svg {
  width: 16px;
  height: 16px;
}

.import-upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8) var(--space-4);
  border: 2px dashed var(--color-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  margin-left: 32px;
}

.import-upload-area:hover {
  border-color: var(--color-primary-300);
  background: var(--color-primary-50);
  color: var(--color-primary-500);
}

.import-upload-area.upload-loading {
  cursor: not-allowed;
  opacity: 0.7;
}

.import-upload-area svg {
  width: 32px;
  height: 32px;
  color: var(--color-text-tertiary);
}

.import-upload-area:hover svg {
  color: var(--color-primary-500);
}

.import-upload-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.import-file-input {
  display: none;
}

.import-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary-500);
  border-radius: 50%;
  animation: import-spin 0.8s linear infinite;
}

@keyframes import-spin {
  to { transform: rotate(360deg); }
}

.import-result {
  margin-left: 32px;
  padding: var(--space-4);
  background: var(--color-bg-page);
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.import-result-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
  font-weight: 600;
}

.result-success {
  color: var(--color-primary-600);
}

.result-partial {
  color: var(--color-text-primary);
}

.result-fail-count {
  color: var(--color-danger);
  font-weight: 500;
}

.import-errors {
  margin-top: var(--space-3);
  max-height: 200px;
  overflow-y: auto;
}

.import-error-item {
  font-size: var(--text-xs);
  color: var(--color-danger);
  padding: var(--space-1) 0;
  border-bottom: 1px solid var(--color-border-light);
}

.import-error-item:last-child {
  border-bottom: none;
}

@media print {
  body * { visibility: hidden; }
  #print-area, #print-area * { visibility: visible; }
  #print-area { position: absolute; left: 0; top: 0; }
  .modal-header, .modal-footer { display: none !important; }
  .print-labels { grid-template-columns: repeat(3, 1fr); }
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
