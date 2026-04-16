<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { getCategories, createCategory, updateCategory, deleteCategory as deleteCategoryApi, importCategories, downloadCategoryTemplate, exportCategories } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Category, CategoryRequest } from '@/types'
import { useFocusTrap } from '@/composables/useFocusTrap'

// 当前选中的分类
const selectedCategory = ref<any>(null)
const modalRef = ref<HTMLElement | null>(null)
const triggerElement = ref<HTMLElement | null>(null)

// 使用焦点陷阱
const { activateTrap, deactivateTrap } = useFocusTrap(modalRef)

// 监听模态框状态，管理焦点陷阱
watch(selectedCategory, (newVal) => {
  nextTick(() => {
    if (newVal) {
      activateTrap()
    } else {
      deactivateTrap()
    }
  })
})
const viewMode = ref<'table' | 'card'>('table')
const loading = ref(false)
const saving = ref(false)

// 筛选
const filterCategory = ref('')
const filterKeyword = ref('')
const filterItemCategory = ref('')

// 分类数据
const categories = ref<Category[]>([])
// 全量数据（用于统计和筛选器，不分页）
const allCategories = ref<Category[]>([])

// 分页
const pagination = ref({ page: 1, pageSize: 20, total: 0 })
const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.pageSize))

// 计算显示的页码（超过7页时省略中间部分）
const pageNumbers = computed(() => {
  const total = totalPages.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const current = pagination.value.page
  const pages: number[] = [1]
  if (current > 3) pages.push(-1) // 省略号
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i)
  }
  if (current < total - 2) pages.push(-1) // 省略号
  pages.push(total)
  return pages
})
// 资产类目选项（一级分类）- 基于全量数据
const mainCategories = computed(() => {
  const set = new Set(allCategories.value.map(c => c.资产类目))
  return Array.from(set)
})

// 物品分类选项（二级分类）- 基于全量数据，联动一级分类
const itemCategories = computed(() => {
  const source = filterCategory.value
    ? allCategories.value.filter(c => c.资产类目 === filterCategory.value)
    : allCategories.value
  const set = new Set(source.map(c => c.物品分类))
  return Array.from(set)
})

// 筛选后的数据（分页后后端已筛选，直接使用）
const filteredCategories = computed(() => categories.value)

// 统计信息 - 基于全量数据
const stats = computed(() => {
  const mainCatCount = mainCategories.value.length
  const subCatCount = new Set(allCategories.value.map(c => `${c.资产类目}-${c.物品分类}`)).size
  const totalItems = allCategories.value.length
  const lowStock = allCategories.value.filter(c => (c.在库数量 ?? 0) < (c.警戒线 ?? 0)).length
  return { mainCatCount, subCatCount, totalItems, lowStock }
})

// 获取库存状态
const getStockStatus = (item: Category) => {
  const stock = item.在库数量 ?? 0
  const warning = item.警戒线 ?? 1
  const ratio = stock / warning
  if (ratio < 1) return 'danger'
  if (ratio < 1.5) return 'warning'
  return 'normal'
}

// 获取分类列表（分页）
async function fetchCategories() {
  loading.value = true
  try {
    const { data } = await getCategories({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      资产类目: filterCategory.value || undefined,
      物品分类: filterItemCategory.value || undefined,
      keyword: filterKeyword.value || undefined,
    })
    categories.value = data.results
    pagination.value.total = data.count
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

// 获取全量数据（用于统计卡片和筛选器）
async function fetchAllCategories() {
  try {
    const all: Category[] = []
    let page = 1
    let hasMore = true
    while (hasMore) {
      const { data } = await getCategories({ page, pageSize: 100 })
      all.push(...data.results)
      hasMore = all.length < data.count
      page++
    }
    allCategories.value = all
  } catch {
    // 静默失败，统计功能降级
  }
}

// 分页操作
const handlePageChange = (page: number) => {
  pagination.value.page = page
  fetchCategories()
}

const handlePageSizeChange = (e: Event) => {
  const select = e.target as HTMLSelectElement
  pagination.value.pageSize = Number(select.value)
  pagination.value.page = 1
  fetchCategories()
}

// 筛选条件变更时重置分页
watch([filterCategory, filterKeyword, filterItemCategory], () => {
  pagination.value.page = 1
  fetchCategories()
})

// 一级分类变更时清空物品分类选择
watch(filterCategory, () => {
  filterItemCategory.value = ''
})

// 编辑分类
const editCategory = (item: Category) => {
  triggerElement.value = document.activeElement as HTMLElement
  selectedCategory.value = { ...item }
}

// 删除分类
const deleteCategory = async (item: Category) => {
  try {
    await ElMessageBox.confirm(`确定删除分类"${item.资产名称}"？此操作不可恢复`, '删除确认', { type: 'warning' })
    if (item.id) {
      await deleteCategoryApi(item.id)
      ElMessage.success('删除成功')
      await fetchCategories()
      fetchAllCategories()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// 新增分类
const addCategory = () => {
  triggerElement.value = document.activeElement as HTMLElement
  selectedCategory.value = {
    id: '',
    资产类目: '',
    物品分类: '',
    资产名称: '',
    资产编号: '',
    计量单位: '',
    警戒线: 10,
    备注: ''
  }
}

// 关闭模态框
const closeModal = () => {
  deactivateTrap()
  selectedCategory.value = null
  // 恢复焦点到触发元素
  if (triggerElement.value) {
    triggerElement.value.focus()
    triggerElement.value = null
  }
}

// 保存分类
async function saveCategory() {
  if (!selectedCategory.value) return
  saving.value = true
  try {
    // 使用英文字段名发送给后端
    const payload: CategoryRequest = {
      asset_category: selectedCategory.value.资产类目,
      item_category: selectedCategory.value.物品分类,
      asset_name: selectedCategory.value.资产名称,
      asset_code: selectedCategory.value.资产编号,
      unit: selectedCategory.value.计量单位,
      warning_line: selectedCategory.value.警戒线,
      remarks: selectedCategory.value.备注,
    }
    if (selectedCategory.value.id) {
      await updateCategory(selectedCategory.value.id, payload)
      ElMessage.success('保存成功')
    } else {
      await createCategory(payload)
      ElMessage.success('创建成功')
    }
    closeModal()
    await fetchCategories()
    fetchAllCategories()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

// 导入分类
const showImportModal = ref(false)
const importFile = ref<File | null>(null)
const importing = ref(false)

const openImportModal = () => {
  importFile.value = null
  showImportModal.value = true
}

const handleFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    importFile.value = input.files[0]
  }
}

const handleImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  importing.value = true
  try {
    const { data } = await importCategories(importFile.value)
    ElMessage.success(`导入成功 ${data.imported} 条${data.errors.length > 0 ? `，失败 ${data.errors.length} 条` : ''}`)
    showImportModal.value = false
    await fetchCategories()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    importing.value = false
  }
}

const handleDownloadTemplate = async () => {
  try {
    const { data } = await downloadCategoryTemplate()
    const blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '分类导入模板.xlsx'
    link.click()
    URL.revokeObjectURL(url)
  } catch {
    const link = document.createElement('a')
    link.href = '/xx分公司行政资产盘点系统-模版.xlsx'
    link.download = '分类导入模板.xlsx'
    link.click()
  }
}

// 属性模板操作
const addAttribute = () => {
  if (!selectedCategory.value) return
  if (!selectedCategory.value.attributes) {
    selectedCategory.value.attributes = []
  }
  selectedCategory.value.attributes.push({
    name: '',
    type: 'text',
    required: false,
    options: ''
  })
}

const removeAttribute = (index: number) => {
  if (!selectedCategory.value?.attributes) return
  selectedCategory.value.attributes.splice(index, 1)
}

// 初始化
onMounted(() => {
  fetchCategories()
  fetchAllCategories()
})
</script>

<template>
  <div class="category-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">资产分类</h1>
        <p class="page-desc">管理资产分类体系，设置警戒线和编号规则</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="exportCategories({ 资产类目: filterCategory || undefined, keyword: filterKeyword || undefined })">
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
          导入
        </button>
        <button class="btn-primary" @click="addCategory">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新增分类
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon primary">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.mainCatCount }}</span>
          <span class="stat-label">资产类目</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon success">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"/>
            <rect x="14" y="3" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.subCatCount }}</span>
          <span class="stat-label">物品分类</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon info">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.totalItems }}</span>
          <span class="stat-label">资产种类</span>
        </div>
      </div>
      <div class="stat-card warning">
        <div class="stat-icon warning">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.lowStock }}</span>
          <span class="stat-label">库存不足</span>
        </div>
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
            v-model="filterKeyword"
            type="text"
            placeholder="搜索资产名称、编号..."
            class="filter-input"
          />
        </div>

        <div class="filter-item">
          <select v-model="filterCategory" class="filter-select">
            <option value="">全部类目</option>
            <option v-for="cat in mainCategories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>

        <div class="filter-item">
          <select v-model="filterItemCategory" class="filter-select">
            <option value="">全部物品</option>
            <option v-for="cat in itemCategories" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>

        <div class="view-toggle">
          <button
            class="toggle-btn"
            :class="{ active: viewMode === 'table' }"
            @click="viewMode = 'table'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="8" y1="6" x2="21" y2="6"/>
              <line x1="8" y1="12" x2="21" y2="12"/>
              <line x1="8" y1="18" x2="21" y2="18"/>
              <line x1="3" y1="6" x2="3.01" y2="6"/>
              <line x1="3" y1="12" x2="3.01" y2="12"/>
              <line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
          </button>
          <button
            class="toggle-btn"
            :class="{ active: viewMode === 'card' }"
            @click="viewMode = 'card'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7"/>
              <rect x="14" y="3" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/>
              <rect x="14" y="14" width="7" height="7"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 表格视图 -->
    <div v-if="viewMode === 'table'" class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>资产类目</th>
            <th>物品分类</th>
            <th>资产名称</th>
            <th>资产编号</th>
            <th>计量单位</th>
            <th>资产数量</th>
            <th>在库数量</th>
            <th>警戒线</th>
            <th>库存状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredCategories" :key="item.id">
            <td>
              <span class="category-tag primary">{{ item.资产类目 }}</span>
            </td>
            <td>{{ item.物品分类 }}</td>
            <td>
              <span class="asset-name">{{ item.资产名称 }}</span>
              <span v-if="item.备注" class="asset-remark">{{ item.备注 }}</span>
            </td>
            <td>
              <span class="asset-code">{{ item.资产编号 }}</span>
            </td>
            <td>{{ item.计量单位 }}</td>
            <td>{{ item.资产数量 }}</td>
            <td>{{ item.在库数量 }}</td>
            <td>{{ item.警戒线 }}</td>
            <td>
              <span
                class="stock-badge"
                :class="getStockStatus(item)"
              >
                {{ getStockStatus(item) === 'normal' ? '充足' : getStockStatus(item) === 'warning' ? '偏低' : '不足' }}
              </span>
            </td>
            <td>
              <div class="action-buttons">
                <button class="action-btn" title="编辑" @click="editCategory(item)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
                <button class="action-btn danger" title="删除" @click="deleteCategory(item)">
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

    <!-- 卡片视图 -->
    <div v-else class="card-grid">
      <div
        v-for="item in filteredCategories"
        :key="item.id"
        class="category-card"
        :class="getStockStatus(item)"
      >
        <div class="card-header">
          <span class="card-code">{{ item.资产编号 }}</span>
          <span
            class="stock-indicator"
            :class="getStockStatus(item)"
          />
        </div>
        <h4 class="card-title">{{ item.资产名称 }}</h4>
        <div class="card-category">
          <span class="main-cat">{{ item.资产类目 }}</span>
          <span class="separator">/</span>
          <span class="sub-cat">{{ item.物品分类 }}</span>
        </div>
        <div class="card-stats">
          <div class="stat-item">
            <span class="stat-num">{{ item.在库数量 }}</span>
            <span class="stat-label">在库</span>
          </div>
          <div class="stat-divider" />
          <div class="stat-item">
            <span class="stat-num">{{ item.资产数量 }}</span>
            <span class="stat-label">总数</span>
          </div>
          <div class="stat-divider" />
          <div class="stat-item warning">
            <span class="stat-num">{{ item.警戒线 }}</span>
            <span class="stat-label">警戒线</span>
          </div>
        </div>
        <div class="card-footer">
          <span class="card-unit">单位：{{ item.计量单位 }}</span>
          <div class="card-actions">
            <button class="card-btn" @click="editCategory(item)">编辑</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-section">
      <div class="pagination-info">
        共 {{ pagination.total }} 条
      </div>
      <div class="pagination-controls">
        <button class="page-btn" :disabled="pagination.page <= 1" @click="handlePageChange(pagination.page - 1)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <span v-for="p in pageNumbers" :key="p" class="page-btn" :class="{ active: p === pagination.page, ellipsis: p === -1 }" @click="p !== -1 && handlePageChange(p)">{{ p === -1 ? '...' : p }}</span>
        <button class="page-btn" :disabled="pagination.page >= totalPages" @click="handlePageChange(pagination.page + 1)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>
      <div class="pagination-size">
        <select class="size-select" :value="pagination.pageSize" @change="handlePageSizeChange">
          <option value="20">20条/页</option>
          <option value="50">50条/页</option>
          <option value="100">100条/页</option>
        </select>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <Teleport to="body">
      <div
        v-if="selectedCategory"
        ref="modalRef"
        class="modal-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="category-modal-title"
        @click.self="closeModal"
        @keydown.esc="closeModal"
      >
        <div class="modal-content">
          <div class="modal-header">
            <h3 id="category-modal-title" class="modal-title">
              {{ selectedCategory.id ? '编辑分类' : '新增分类' }}
            </h3>
            <button
              class="modal-close"
              aria-label="关闭"
              @click="closeModal"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="form-grid">
              <div class="form-item">
                <label class="form-label" for="category-asset-type">
                  资产类目 <span class="required">*</span>
                </label>
                <select
                  id="category-asset-type"
                  v-model="selectedCategory.资产类目"
                  class="form-select"
                  aria-required="true"
                >
                  <option value="">请选择</option>
                  <option value="固定资产类">固定资产类</option>
                  <option value="低值易耗品">低值易耗品</option>
                  <option value="无形资产类">无形资产类</option>
                  <option value="文档资料类">文档资料类</option>
                  <option value="特殊设备类">特殊设备类</option>
                  <option value="其他资产">其他资产</option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label" for="category-item-type">
                  物品分类 <span class="required">*</span>
                </label>
                <input
                  id="category-item-type"
                  v-model="selectedCategory.物品分类"
                  type="text"
                  class="form-input"
                  placeholder="请输入物品分类"
                  aria-required="true"
                />
              </div>
              <div class="form-item">
                <label class="form-label" for="category-asset-name">
                  资产名称 <span class="required">*</span>
                </label>
                <input
                  id="category-asset-name"
                  v-model="selectedCategory.资产名称"
                  type="text"
                  class="form-input"
                  placeholder="请输入资产名称"
                  aria-required="true"
                />
              </div>
              <div class="form-item">
                <label class="form-label" for="category-asset-code">
                  资产编号 <span class="required">*</span>
                </label>
                <input
                  id="category-asset-code"
                  v-model="selectedCategory.资产编号"
                  type="text"
                  class="form-input"
                  placeholder="如：A-a00001"
                  aria-required="true"
                />
              </div>
              <div class="form-item">
                <label class="form-label" for="category-unit">
                  计量单位 <span class="required">*</span>
                </label>
                <input
                  id="category-unit"
                  v-model="selectedCategory.计量单位"
                  type="text"
                  class="form-input"
                  placeholder="如：台、个、张"
                  aria-required="true"
                />
              </div>
              <div class="form-item">
                <label class="form-label" for="category-warning-line">
                  警戒线
                </label>
                <input
                  id="category-warning-line"
                  v-model="selectedCategory.警戒线"
                  type="number"
                  class="form-input"
                  placeholder="库存警戒数量"
                />
              </div>
              <div class="form-item full">
                <label class="form-label" for="category-remarks">
                  备注
                </label>
                <textarea
                  id="category-remarks"
                  v-model="selectedCategory.备注"
                  class="form-textarea"
                  placeholder="备注信息"
                  rows="3"
                />
              </div>
              <!-- 属性模板配置 -->
              <div class="form-item full">
                <div class="attr-template-header">
                  <label class="form-label">属性模板</label>
                  <button type="button" class="attr-add-btn" @click="addAttribute">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                      <line x1="12" y1="5" x2="12" y2="19"/>
                      <line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    添加属性
                  </button>
                </div>
                <div v-if="selectedCategory.attributes && selectedCategory.attributes.length > 0" class="attr-list">
                  <div v-for="(attr, idx) in selectedCategory.attributes" :key="idx" class="attr-item">
                    <input v-model="attr.name" type="text" class="form-input attr-input" placeholder="属性名称" />
                    <select v-model="attr.type" class="form-select attr-input">
                      <option value="text">文本</option>
                      <option value="number">数字</option>
                      <option value="select">下拉选择</option>
                    </select>
                    <label class="attr-required-label">
                      <input type="checkbox" v-model="attr.required" /> 必填
                    </label>
                    <input
                      v-if="attr.type === 'select'"
                      v-model="attr.options"
                      type="text"
                      class="form-input attr-input"
                      placeholder="选项（逗号分隔）"
                    />
                    <button type="button" class="attr-del-btn" @click="removeAttribute(idx)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                </div>
                <div v-else class="attr-empty">暂无自定义属性，点击"添加属性"配置</div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="closeModal">取消</button>
            <button class="btn-confirm" @click="saveCategory" :disabled="saving">
              {{ saving ? '保存中...' : '确定保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
    <!-- 导入弹窗 -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="showImportModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3 class="modal-title">导入分类</h3>
          <button class="modal-close" @click="showImportModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="import-area">
            <button class="btn-secondary" style="margin-bottom: 16px" @click="handleDownloadTemplate">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              下载模板
            </button>
            <div class="upload-zone">
              <input type="file" accept=".xlsx,.xls" @change="handleFileChange" class="file-input" />
              <p v-if="importFile" class="file-name">{{ importFile.name }}</p>
              <p v-else class="upload-hint">点击或拖拽上传 Excel 文件</p>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showImportModal = false">取消</button>
          <button class="btn-confirm" @click="handleImport" :disabled="importing || !importFile">{{ importing ? '导入中...' : '确认导入' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.category-page {
  max-width: 1400px;
  margin: 0 auto;
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
  flex-direction: column;
  gap: var(--space-1);
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
  height: 40px;
  padding: 0 var(--space-5);
  border-radius: 10px;
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
  width: 18px;
  height: 18px;
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.stat-card {
  background: var(--color-bg-card);
  border-radius: 12px;
  padding: var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  border: 1px solid var(--color-border);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon svg {
  width: 24px;
  height: 24px;
}

.stat-icon.primary {
  background: var(--color-primary-100);
  color: var(--color-primary-600);
}

.stat-icon.success {
  background: oklch(0.92 0.08 145);
  color: var(--color-success);
}

.stat-icon.info {
  background: oklch(0.92 0.06 240);
  color: var(--color-info);
}

.stat-icon.warning {
  background: oklch(0.94 0.06 85);
  color: var(--color-warning);
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 筛选区 */
.filter-section {
  margin-bottom: var(--space-4);
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
  background: var(--color-bg-card);
  font-size: var(--text-sm);
}

.filter-select {
  height: 38px;
  padding: 0 var(--space-4);
  min-width: 160px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
}

.view-toggle {
  display: flex;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.toggle-btn {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-card);
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toggle-btn:hover {
  color: var(--color-text-primary);
}

.toggle-btn.active {
  background: var(--color-primary-500);
  color: white;
}

.toggle-btn svg {
  width: 18px;
  height: 18px;
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
}

.data-table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-light);
}

.data-table tbody tr:hover {
  background: var(--color-bg-elevated);
}

.category-tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: var(--text-xs);
  font-weight: 500;
}

.category-tag.primary {
  background: var(--color-primary-50);
  color: var(--color-primary-600);
}

.asset-name {
  display: block;
  font-weight: 500;
}

.asset-remark {
  display: block;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.asset-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  padding: 2px 8px;
  border-radius: 4px;
}

.stock-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: 500;
}

.stock-badge.normal {
  background: oklch(0.92 0.08 145);
  color: var(--color-success);
}

.stock-badge.warning {
  background: oklch(0.94 0.06 85);
  color: var(--color-warning);
}

.stock-badge.danger {
  background: oklch(0.92 0.10 25);
  color: var(--color-danger);
}

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
  color: var(--color-danger);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

/* 卡片视图 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.category-card {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  padding: var(--space-4);
  transition: all var(--transition-fast);
}

.category-card:hover {
  box-shadow: var(--shadow-md);
}

.category-card.danger {
  border-color: oklch(0.88 0.12 25);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.card-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  padding: 4px 8px;
  border-radius: 4px;
}

.stock-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-success);
}

.stock-indicator.warning {
  background: var(--color-warning);
}

.stock-indicator.danger {
  background: var(--color-danger);
}

.card-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2) 0;
}

.card-category {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-4);
}

.separator {
  color: var(--color-border);
}

.card-stats {
  display: flex;
  align-items: center;
  padding: var(--space-3);
  background: var(--color-bg-page);
  border-radius: 8px;
  margin-bottom: var(--space-3);
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-item .stat-num {
  display: block;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.stat-item.warning .stat-num {
  color: var(--color-warning);
}

.stat-item .stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--color-border);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-unit {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.card-btn {
  padding: var(--space-1) var(--space-3);
  background: var(--color-primary-50);
  border: none;
  border-radius: 6px;
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  cursor: pointer;
}

.card-btn:hover {
  background: var(--color-primary-100);
}

/* 弹窗 */
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
  width: 560px;
  background: var(--color-bg-card);
  border-radius: 16px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
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
  border-radius: 8px;
  color: var(--color-text-tertiary);
  cursor: pointer;
}

.modal-close:hover {
  background: var(--color-bg-elevated);
}

.modal-close svg {
  width: 18px;
  height: 18px;
}

.modal-body {
  padding: var(--space-5);
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

.form-input,
.form-select,
.form-textarea {
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

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-5);
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-page);
}

.btn-cancel {
  height: 40px;
  padding: 0 var(--space-5);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
}

.btn-confirm {
  height: 40px;
  padding: 0 var(--space-5);
  background: var(--color-primary-500);
  border: none;
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  color: white;
  cursor: pointer;
}

/* 属性模板 */
.attr-template-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.attr-add-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 4px 12px;
  background: var(--color-primary-50);
  border: 1px solid var(--color-primary-200);
  border-radius: 6px;
  font-size: var(--text-xs);
  color: var(--color-primary-600);
  cursor: pointer;
}

.attr-add-btn:hover {
  background: var(--color-primary-100);
}

.attr-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.attr-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-page);
  border-radius: 8px;
}

.attr-input {
  flex: 1;
  min-width: 0;
}

.attr-required-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.attr-del-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
}

.attr-del-btn:hover {
  background: oklch(0.92 0.10 25);
  color: var(--color-danger);
}

.attr-empty {
  padding: var(--space-3);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  background: var(--color-bg-page);
  border-radius: 8px;
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

.page-btn:hover:not(.active):not(.ellipsis) {
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

.page-btn.ellipsis {
  border: none;
  background: transparent;
  cursor: default;
  color: var(--color-text-tertiary);
}

.page-btn svg {
  width: 16px;
  height: 16px;
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
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-4);
  }

  .stats-row {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-item.full {
    grid-column: span 1;
  }
}
</style>
