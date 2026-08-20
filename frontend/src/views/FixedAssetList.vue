<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getFixedAssets, updateFixedAsset, deleteFixedAsset, batchDeleteFixedAssets, importFixedAssets, exportFixedAssets, downloadFixedAssetTemplate } from '@/api/assets'
import type { FixedAsset } from '@/types'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import BasePagination from '@/components/BasePagination.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import AssetPrintDialog from './assets/AssetPrintDialog.vue'
import RecoveryDialog from './assets/RecoveryDialog.vue'

const { canManageAssets } = usePermission()

const filters = ref({
  branch: '',
  status: '',
  keyword: '',
  资产名称: ''
})

const pagination = ref({ page: 1, pageSize: 50, total: 0 })
const loading = ref(false)
const assets = ref<FixedAsset[]>([])

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: '在库', label: '在库' },
  { value: '在用', label: '在用' },
  { value: '空闲', label: '空闲' },
]
const branchOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部分公司' }])

// ── 导出 ──
const exporting = ref(false)

async function handleExport() {
  exporting.value = true
  try {
    const params: Record<string, string> = {}
    if (filters.value.branch) params.branch = filters.value.branch
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.资产名称) params.资产名称 = filters.value.资产名称
    const { data } = await exportFixedAssets(params)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = `固定资产表_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    exporting.value = false
  }
}

// ── 批量导入（两步弹窗） ──
const showImportModal = ref(false)
const importing = ref(false)
const importResult = ref<{ imported: number; errors: string[] } | null>(null)

async function handleDownloadTemplate() {
  try {
    const { data } = await downloadFixedAssetTemplate()
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = '固定资产导入模板.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

async function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  importing.value = true
  importResult.value = null
  try {
    const { data } = await importFixedAssets(file)
    importResult.value = data
    await fetchAssets()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    importing.value = false
    input.value = ''
  }
}

function openImportModal() {
  importResult.value = null
  showImportModal.value = true
}

// ── 新增（跳转独立页面）──
const router = useRouter()

function openCreatePage() {
  router.push('/fixed-assets/create')
}

// ── 编辑 ──
const editingAsset = ref<FixedAsset | null>(null)
const showEditModal = ref(false)
const saving = ref(false)

function openEdit(asset: FixedAsset) {
  editingAsset.value = { ...asset }
  showEditModal.value = true
}

async function handleUpdate() {
  if (!editingAsset.value) return
  saving.value = true
  try {
    await updateFixedAsset(editingAsset.value.id, {
      序列号: editingAsset.value.序列号,
      供应商: editingAsset.value.供应商,
      使用人: editingAsset.value.使用人,
      所属部门: editingAsset.value.所属部门,
      当前状态: editingAsset.value.当前状态,
      备注: editingAsset.value.备注,
    })
    ElMessage.success('更新成功')
    showEditModal.value = false
    await fetchAssets()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

// ── 行内回收（即时生效，联动资产汇总库存并删除该实例记录）──
const showRecoveryDialog = ref(false)
const recoveringAsset = ref<FixedAsset | null>(null)

function openRecovery(asset: FixedAsset) {
  recoveringAsset.value = asset
  showRecoveryDialog.value = true
}

// ── 删除 ──
async function handleDelete(asset: FixedAsset) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${asset.内部编号}」？此操作不可恢复`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await deleteFixedAsset(asset.id)
    ElMessage.success('删除成功')
    await fetchAssets()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(handleApiError(e))
  }
}

// ── 多选与批量删除 ──
const selectedIds = ref<string[]>([])
const isAllSelected = computed(() => assets.value.length > 0 && selectedIds.value.length === assets.value.length)
function toggleAll() {
  selectedIds.value = isAllSelected.value ? [] : assets.value.map(a => a.id)
}
function toggleSelect(id: string) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的固定资产')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedIds.value.length} 项固定资产？此操作不可恢复`,
      '批量删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await batchDeleteFixedAssets(selectedIds.value)
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    await fetchAssets()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(handleApiError(e))
  }
}

// ── 标签打印 ──
const showPrintDialog = ref(false)
const printItems = ref<any[]>([])

function printSingleLabel(item: any) {
  printItems.value = [item]
  showPrintDialog.value = true
}

function handlePrintLabels() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要打印的固定资产')
    return
  }
  printItems.value = assets.value.filter(a => selectedIds.value.includes(a.id))
  showPrintDialog.value = true
}

// ── 列表 ──
async function fetchAssets() {
  loading.value = true
  try {
    const { data } = await getFixedAssets({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      branch: filters.value.branch || undefined,
      status: filters.value.status || undefined,
      keyword: filters.value.keyword || undefined,
      资产名称: filters.value.资产名称 || undefined,
    })
    assets.value = data.results
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
      ...data.map((b: any) => ({ value: b.name, label: b.name }))
    ]
  } catch {}
}

const resetFilters = () => {
  filters.value = { branch: '', status: '', keyword: '', 资产名称: '' }
  pagination.value.page = 1
  fetchAssets()
}

const handlePaginationChange = (page: number, pageSize: number) => {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchAssets()
}

watch(filters, () => { pagination.value.page = 1; fetchAssets() }, { deep: true })

onMounted(() => { fetchAssets(); fetchBranches() })
</script>

<template>
  <div class="fixed-asset-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">固定资产表</h1>
        <p class="page-desc">共{{ pagination.total }}台固定资产</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="handleExport" :disabled="exporting">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {{ exporting ? '导出中...' : '导出' }}
        </button>
        <button class="btn-secondary" @click="openImportModal" v-if="canManageAssets">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          批量导入
        </button>
        <button class="btn-primary" @click="openCreatePage" v-if="canManageAssets">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新增
        </button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item search">
          <svg class="filter-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <input v-model="filters.keyword" type="text" placeholder="搜索资产编号、资产名称、序列号、使用人..." class="filter-input" />
        </div>
        <div class="filter-item">
          <select v-model="filters.branch" class="filter-select">
            <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div class="filter-item">
          <select v-model="filters.status" class="filter-select">
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <div class="filter-item">
          <input v-model="filters.资产名称" type="text" placeholder="资产名称" class="filter-input" />
        </div>
        <button class="filter-reset" @click="resetFilters">重置</button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.length > 0" class="fa-batch-actions">
      <span class="fa-batch-info">已选择 {{ selectedIds.length }} 项</span>
      <button class="fa-batch-btn" @click="handlePrintLabels">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 6 2 18 2 18 9"/>
          <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
          <rect x="6" y="14" width="12" height="8"/>
        </svg>
        打印标签
      </button>
      <button v-if="canManageAssets" class="fa-batch-btn danger" @click="handleBatchDelete">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6"/>
        </svg>
        批量删除
      </button>
    </div>

    <!-- 表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th v-if="canManageAssets" class="col-check"><input type="checkbox" :checked="isAllSelected" @change="toggleAll" /></th>
            <th>序号</th>
            <th>分公司编号</th>
            <th>分公司</th>
            <th>资产编号</th>
            <th>资产类目</th>
            <th>物品分类</th>
            <th>资产名称</th>
            <th>电脑序列号</th>
            <th>供应商</th>
            <th>入库日期</th>
            <th>是否租用</th>
            <th>数量</th>
            <th>规格</th>
            <th>单价</th>
            <th>购入金额</th>
            <th>出库日期</th>
            <th>所属部门</th>
            <th>使用人</th>
            <th>当前状态</th>
            <th v-if="canManageAssets">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td :colspan="canManageAssets ? 21 : 19" class="empty-cell">加载中...</td></tr>
          <tr v-else-if="assets.length === 0"><td :colspan="canManageAssets ? 21 : 19" class="empty-cell">暂无固定资产数据</td></tr>
          <tr v-for="(item, index) in assets" :key="item.id" v-else>
            <td v-if="canManageAssets" class="col-check"><input type="checkbox" :checked="selectedIds.includes(item.id)" @change="toggleSelect(item.id)" /></td>
            <td>{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
            <td>{{ item.分公司编号 || '-' }}</td>
            <td>{{ item.分公司 || '-' }}</td>
            <td><span class="asset-code">{{ item.资产编号 }}</span></td>
            <td>{{ item.资产类目 || '-' }}</td>
            <td>{{ item.物品分类 || '-' }}</td>
            <td>{{ item.资产名称 || '-' }}</td>
            <td>{{ item.序列号 || '-' }}</td>
            <td>{{ item.供应商 || '-' }}</td>
            <td><span class="date-text">{{ item.入库日期 || '-' }}</span></td>
            <td>{{ item.是否租用 ? '是' : '否' }}</td>
            <td>{{ item.数量 ?? '-' }}</td>
            <td>{{ item.规格 || '-' }}</td>
            <td>{{ item.单价 ?? '-' }}</td>
            <td>{{ item.购入金额 ?? '-' }}</td>
            <td><span class="date-text">{{ item.出库日期 || '-' }}</span></td>
            <td>{{ item.所属部门 || '-' }}</td>
            <td>{{ item.使用人 || '-' }}</td>
            <td><StatusBadge :status="item.当前状态 || ''" /></td>
            <td class="action-col">
              <button class="action-btn" title="打印标签" @click="printSingleLabel(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 6 2 18 2 18 9"/>
                  <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                  <rect x="6" y="14" width="12" height="8"/>
                </svg>
              </button>
              <button v-if="canManageAssets" class="action-btn" title="回收" @click="openRecovery(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="1 4 1 10 7 10"/>
                  <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
                </svg>
              </button>
              <button v-if="canManageAssets" class="action-btn" title="编辑" @click="openEdit(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button class="action-btn danger" title="删除" @click="handleDelete(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination :total="pagination.total" :current-page="pagination.page" :page-size="pagination.pageSize" @change="handlePaginationChange" />

    <!-- 编辑弹窗 -->
    <el-dialog v-model="showEditModal" title="编辑固定资产" width="500px" :close-on-click-modal="false">
      <el-form label-width="80px" v-if="editingAsset">
        <el-form-item label="序列号"><el-input v-model="editingAsset.序列号" /></el-form-item>
        <el-form-item label="供应商"><el-input v-model="editingAsset.供应商" /></el-form-item>
        <el-form-item label="使用人"><el-input v-model="editingAsset.使用人" /></el-form-item>
        <el-form-item label="所属部门"><el-input v-model="editingAsset.所属部门" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editingAsset.当前状态">
            <el-option label="在库" value="在库" />
            <el-option label="在用" value="在用" />
            <el-option label="空闲" value="空闲" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="editingAsset.备注" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditModal = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增弹窗 -->
    <!-- 批量导入弹窗（两步流程） -->
    <el-dialog v-model="showImportModal" title="批量导入固定资产" width="560px">
      <div class="import-step">
        <div class="import-step-header">
          <span class="import-step-num">1</span>
          <span class="import-step-title">下载导入模板</span>
        </div>
        <p class="import-step-desc">请先下载模板文件，按格式填写固定资产数据后上传</p>
        <button class="btn-secondary import-template-btn" @click="handleDownloadTemplate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          下载模板
        </button>
      </div>
      <div class="import-step">
        <div class="import-step-header">
          <span class="import-step-num">2</span>
          <span class="import-step-title">上传填写好的 Excel 文件</span>
        </div>
        <label class="import-upload-area" :class="{ 'upload-loading': importing }">
          <input type="file" accept=".xlsx,.xls" class="import-file-input" @change="handleImportFile" :disabled="importing" />
          <template v-if="importing">
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
      <div v-if="importResult" class="import-result">
        <div class="import-result-header">
          <span :class="importResult.errors.length === 0 ? 'result-success' : 'result-partial'">成功导入 {{ importResult.imported }} 条</span>
          <span v-if="importResult.errors.length > 0" class="result-fail-count">失败 {{ importResult.errors.length }} 条</span>
        </div>
        <div v-if="importResult.errors.length > 0" class="import-errors">
          <div v-for="(err, idx) in importResult.errors" :key="idx" class="import-error-item">{{ err }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showImportModal = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 标签打印弹窗 -->
    <AssetPrintDialog :visible="showPrintDialog" :assets="printItems" @close="showPrintDialog = false" />

    <!-- 行内回收弹窗 -->
    <RecoveryDialog
      v-if="showRecoveryDialog"
      :visible="showRecoveryDialog"
      mode="fixed"
      :item="recoveringAsset"
      @close="showRecoveryDialog = false"
      @success="fetchAssets"
    />
  </div>
</template>

<style scoped>
.fixed-asset-page { max-width: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-6); flex-shrink: 0; }
.header-info { display: flex; align-items: baseline; gap: var(--space-3); }
.page-title { font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.page-desc { font-size: var(--text-sm); color: var(--color-text-tertiary); margin: 0; }
.header-actions { display: flex; gap: var(--space-3); }
.btn-secondary { display: flex; align-items: center; gap: var(--space-2); height: 38px; padding: 0 var(--space-4); border-radius: 8px; font-size: var(--text-sm); font-weight: 500; cursor: pointer; background: var(--color-bg-card); border: 1px solid var(--color-border); color: var(--color-text-primary); transition: all var(--transition-fast); }
.btn-secondary:hover { border-color: var(--color-primary-300); background: var(--color-bg-elevated); }
.btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary svg { width: 16px; height: 16px; }
.btn-primary { display: flex; align-items: center; gap: var(--space-2); height: 38px; padding: 0 var(--space-4); border-radius: 8px; font-size: var(--text-sm); font-weight: 500; cursor: pointer; background: var(--color-primary-500); border: 1px solid var(--color-primary-500); color: white; transition: all var(--transition-fast); }
.btn-primary:hover { background: var(--color-primary-600); }
.btn-primary svg { width: 16px; height: 16px; }
.filter-section { background: var(--color-bg-card); border-radius: 12px; padding: var(--space-4); margin-bottom: var(--space-4); border: 1px solid var(--color-border); flex-shrink: 0; }
.filter-row { display: flex; gap: var(--space-3); }
.filter-item { position: relative; }
.filter-item.search { flex: 1; position: relative; }
.filter-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; color: var(--color-text-tertiary); }
.filter-input { width: 100%; height: 38px; padding: 0 var(--space-4) 0 38px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); color: var(--color-text-primary); }
.filter-input:focus { outline: none; border-color: var(--color-primary-400); box-shadow: 0 0 0 3px var(--color-primary-100); }
.filter-select { height: 38px; padding: 0 var(--space-4); padding-right: var(--space-8); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; min-width: 140px; }
.filter-reset { height: 38px; padding: 0 var(--space-4); background: transparent; border: none; color: var(--color-text-secondary); font-size: var(--text-sm); cursor: pointer; }
.filter-reset:hover { color: var(--color-primary-500); }
.table-container { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); overflow-x: auto; overflow-y: auto; flex: 1; min-height: 200px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table thead th { position: sticky; top: 0; z-index: 1; background: var(--color-bg-elevated); }
.data-table th { padding: var(--space-3) var(--space-4); text-align: left; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); white-space: nowrap; }
.data-table td { padding: var(--space-3) var(--space-4); font-size: var(--text-sm); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border-light); vertical-align: middle; }
.data-table tbody tr { transition: background var(--transition-fast); }
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-8) var(--space-4) !important; }
.asset-code { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-primary-600); background: var(--color-primary-50); padding: 2px 8px; border-radius: 4px; }
.date-text { font-family: var(--font-mono); color: var(--color-text-secondary); font-size: var(--text-xs); white-space: nowrap; }
.action-col { display: flex; gap: var(--space-1); }
.action-btn svg { width: 18px; height: 18px; }
/* 导入弹窗 */
.import-step { margin-bottom: 16px; }
.import-step-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.import-step-num { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; background: var(--color-primary-500); color: white; border-radius: 50%; font-size: var(--text-xs); font-weight: 600; }
.import-step-title { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.import-step-desc { font-size: var(--text-xs); color: var(--color-text-tertiary); margin: 0 0 var(--space-2); }
.import-template-btn svg { width: 16px; height: 16px; }
.import-upload-area { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 20px; border: 2px dashed var(--color-border); border-radius: 12px; cursor: pointer; color: var(--color-text-secondary); font-size: var(--text-sm); transition: all var(--transition-fast); }
.import-upload-area:hover { border-color: var(--color-primary-300); background: var(--color-primary-50); }
.import-upload-area.upload-loading { cursor: not-allowed; opacity: 0.7; }
.import-upload-area svg { width: 24px; height: 24px; }
.import-upload-hint { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.import-file-input { display: none; }
.import-spinner { width: 20px; height: 20px; border: 2px solid var(--color-border); border-top-color: var(--color-primary-500); border-radius: 50%; animation: import-spin 0.8s linear infinite; }
@keyframes import-spin { to { transform: rotate(360deg); } }
.import-result { padding: var(--space-3); background: var(--color-bg-page); border-radius: 8px; border: 1px solid var(--color-border); }
.import-result-header { display: flex; align-items: center; gap: var(--space-3); font-size: var(--text-sm); font-weight: 600; }
.result-success { color: var(--color-primary-600); }
.result-partial { color: var(--color-text-primary); }
.result-fail-count { color: var(--color-danger); }
.import-errors { margin-top: var(--space-3); max-height: 200px; overflow-y: auto; }
.import-error-item { font-size: var(--text-xs); color: var(--color-danger); padding: var(--space-1) 0; border-bottom: 1px solid var(--color-border-light); }
.import-error-item:last-child { border-bottom: none; }
@media (max-width: 1200px) { .data-table { display: block; overflow-x: auto; } }
@media (max-width: 768px) { .page-header { flex-direction: column; align-items: flex-start; gap: var(--space-4); } .filter-row { flex-wrap: wrap; } .filter-item.search { flex: 1 1 100%; } .header-actions { flex-wrap: wrap; } }
/* 批量操作栏 */
.fa-batch-actions { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3) var(--space-4); background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 8px; margin-bottom: var(--space-4); }
.fa-batch-info { font-size: var(--text-sm); color: var(--color-primary-600); }
.fa-batch-btn { display: inline-flex; align-items: center; gap: var(--space-1); padding: var(--space-2) var(--space-3); background: white; border: 1px solid var(--color-border); border-radius: 6px; font-size: var(--text-sm); cursor: pointer; }
.fa-batch-btn svg { width: 16px; height: 16px; }
.fa-batch-btn.danger { color: var(--color-danger); border-color: var(--color-danger); }
.fa-batch-btn.danger:hover { background: var(--color-danger); color: white; }
.col-check { width: 44px; text-align: center; }
.col-check input { width: 16px; height: 16px; cursor: pointer; }
</style>
