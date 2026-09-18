<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getFixedAssets, exportFixedAssets, getFixedAssetTimeline, uploadFixedAssetImage, deleteFixedAssetImage, batchUpdateFixedAssets } from '@/api/assets'
import type { FixedAsset, FixedAssetTimeline } from '@/types'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import BasePagination from '@/components/BasePagination.vue'
import BranchFilterSelect from '@/components/BranchFilterSelect.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import AssetPrintDialog from './assets/AssetPrintDialog.vue'
import { INSTANCE_STATUS_OPTIONS } from '@/constants'

const { can } = usePermission()
const canSupplement = computed(() => can('manage_instances'))
const route = useRoute()

const filters = ref({
  branch: '',
  status: '',
  pendingSerial: false,
  keyword: (route.query.keyword as string) || '',
})

const pagination = ref({ page: 1, pageSize: 50, total: 0 })
const loading = ref(false)
const assets = ref<FixedAsset[]>([])

const statusOptions = [{ value: '', label: '全部状态' }, ...INSTANCE_STATUS_OPTIONS.map(o => ({ value: o.value, label: o.label }))]
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
    if (filters.value.pendingSerial) params.pending_serial = '1'
    const { data } = await exportFixedAssets(params)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = `固定资产实例_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    exporting.value = false
  }
}

// ── 行编辑（归一弹窗：序列号/备注/规格/供应商/图片，manage_instances） ──
const editing = ref<FixedAsset | null>(null)
const editForm = ref<{ 序列号: string; 备注: string; 规格: string; 供应商: string; 采购日期: string | null }>({ 序列号: '', 备注: '', 规格: '', 供应商: '', 采购日期: null })
const editSaving = ref(false)
const editVisibleProxy = computed({
  get: () => editing.value !== null,
  set: (v: boolean) => { if (!v) editing.value = null },
})

function openEdit(asset: FixedAsset) {
  editing.value = asset
  editForm.value = {
    序列号: asset.序列号 || '',
    备注: asset.备注 || '',
    规格: asset.itemSpec || '',
    供应商: asset.供应商 || '',
    采购日期: asset.采购日期 || null,
  }
  openTimeline(asset)  // 右栏生平并行拉取（不阻塞左栏编辑）
}

async function handleEditSave() {
  if (!editing.value) return
  editSaving.value = true
  try {
    const hadDate = !!editing.value.采购日期  // 原有个体日期：清空即清除覆盖
    const { data } = await batchUpdateFixedAssets({
      ids: [editing.value.id],
      序列号列表: [editForm.value.序列号],
      备注: editForm.value.备注,
      规格: editForm.value.规格,
      供应商: editForm.value.供应商,
      ...(editForm.value.采购日期 || hadDate ? { 采购日期: editForm.value.采购日期 || '' } : {}),
    })
    const errs = data.errors || []
    if (errs.length) {
      ElMessage.warning(`保存部分失败：${errs[0]}${errs.length > 1 ? ' 等' : ''}`)
      return  // 弹窗保留，供修正重试
    }
    ElMessage.success('已保存')
    editing.value = null
    await fetchAssets()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    editSaving.value = false
  }
}

// ── 物品图片（编辑弹窗内即时上传/更换/删除，manage_instances，覆盖即清旧图） ──
const imageSaving = ref(false)

async function uploadImage(file: File) {
  if (!editing.value) return
  imageSaving.value = true
  try {
    const { data } = await uploadFixedAssetImage(editing.value.id, file)
    applyImageUpdate(data)
    ElMessage.success('图片已更新')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    imageSaving.value = false
  }
}

async function handleDeleteImage() {
  if (!editing.value?.图片) return
  try {
    await ElMessageBox.confirm('确定删除该物品图片？', '删除图片', { type: 'warning' })
  } catch { return }
  imageSaving.value = true
  try {
    const { data } = await deleteFixedAssetImage(editing.value.id)
    applyImageUpdate(data)
    ElMessage.success('图片已删除')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    imageSaving.value = false
  }
}

/** 编辑弹窗图片预览来源：行数据实时值 */
function imagePreviewFor(asset: FixedAsset): string {
  return asset.图片 || ''
}

const editImageInput = ref<HTMLInputElement | null>(null)
function handleEditImageSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !editing.value) return
  const allowed = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowed.includes(file.type)) {
    ElMessage.error('仅支持 JPG、PNG、WebP 格式')
    input.value = ''
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 2MB')
    input.value = ''
    return
  }
  uploadImage(file)
  input.value = ''
}

async function handleEditImageDelete() {
  if (!editing.value?.图片) return
  try {
    await ElMessageBox.confirm('确定删除该物品图片？', '删除图片', { type: 'warning' })
  } catch { return }
  await handleDeleteImage()
}

/** 响应即最新档案：就地更新列表行，免整页刷新 */
function applyImageUpdate(updated: FixedAsset) {
  const row = assets.value.find(a => a.id === updated.id)
  if (row) row.图片 = updated.图片
  if (editing.value) editing.value = { ...editing.value, 图片: updated.图片 }
}

// ── 生平（出生信息 + 关联全部明细行倒序） ──
const timeline = ref<FixedAssetTimeline | null>(null)
const timelineLoading = ref(false)
const timelineVisibleProxy = computed({
  get: () => timeline.value !== null || timelineLoading.value,
  set: (v: boolean) => { if (!v) timeline.value = null },
})

async function openTimeline(asset: FixedAsset) {
  timeline.value = null
  timelineLoading.value = true
  try {
    const { data } = await getFixedAssetTimeline(asset.id)
    timeline.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    timelineLoading.value = false
  }
}

// ── 标签打印（单行 + 勾选批量） ──
const showPrintDialog = ref(false)
const printItems = ref<any[]>([])
const selectedIds = ref<Set<string>>(new Set())

function printSingleLabel(item: FixedAsset) {
  printItems.value = [toPrintShape(item)]
  showPrintDialog.value = true
}

const pageAllSelected = computed(() =>
  assets.value.length > 0 && assets.value.every((a) => selectedIds.value.has(a.id)),
)

function toggleSelectAll() {
  if (pageAllSelected.value) {
    assets.value.forEach((a) => selectedIds.value.delete(a.id))
  } else {
    assets.value.forEach((a) => selectedIds.value.add(a.id))
  }
  selectedIds.value = new Set(selectedIds.value)
}

function toggleSelect(item: FixedAsset) {
  if (selectedIds.value.has(item.id)) selectedIds.value.delete(item.id)
  else selectedIds.value.add(item.id)
  selectedIds.value = new Set(selectedIds.value)
}

/** 批量打印仅取勾选且仍在当前页的实例（翻页后失效项自动过滤） */
function printSelected() {
  const picked = assets.value.filter((a) => selectedIds.value.has(a.id))
  if (!picked.length) {
    ElMessage.warning('请先勾选要打印的实例')
    return
  }
  printItems.value = picked.map(toPrintShape)
  showPrintDialog.value = true
}

// ── 批量操作（manage_instances）：供应商/备注/序列号 ──
const batchMenuOpen = ref(false)
const batchDialog = ref<'supplier' | 'spec' | 'remark' | 'serial' | null>(null)
const batchValue = ref('')
const batchSerials = ref<string[]>([])
const batchSaving = ref(false)

function openBatch(dialog: 'supplier' | 'spec' | 'remark' | 'serial') {
  batchMenuOpen.value = false
  batchDialog.value = dialog
  batchValue.value = ''
  batchSerials.value = selectedIds.value.size ? Array.from({ length: countSelected() }, () => '') : []
}

const countSelected = () => assets.value.filter((a) => selectedIds.value.has(a.id)).length
const selectedIdList = () => assets.value.filter((a) => selectedIds.value.has(a.id)).map((a) => a.id)

async function submitBatch() {
  const ids = selectedIdList()
  if (!ids.length) return
  const payload: { ids: string[]; 供应商?: string; 规格?: string; 备注?: string; 序列号列表?: string[] } = { ids }
  if (batchDialog.value === 'supplier') payload.供应商 = batchValue.value.trim()
  if (batchDialog.value === 'spec') payload.规格 = batchValue.value.trim()
  if (batchDialog.value === 'remark') payload.备注 = batchValue.value.trim()
  if (batchDialog.value === 'serial') payload.序列号列表 = batchSerials.value.map((s) => s.trim())
  batchSaving.value = true
  try {
    const { data } = await batchUpdateFixedAssets(payload)
    const errs = data.errors || []
    if (errs.length) {
      ElMessage.warning(`成功 ${data.updated} 台，失败 ${errs.length} 台：${errs[0]}${errs.length > 1 ? ' 等' : ''}`)
    } else {
      ElMessage.success(`已更新 ${data.updated} 台`)
    }
    batchDialog.value = null
    await fetchAssets()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    batchSaving.value = false
  }
}

const batchVisibleProxy = computed({
  get: () => batchDialog.value !== null,
  set: (v: boolean) => { if (!v) batchDialog.value = null },
})
const batchTitle = computed(() =>
  batchDialog.value === 'supplier' ? '批量修改供应商'
    : batchDialog.value === 'spec' ? '批量修改规格'
    : batchDialog.value === 'remark' ? '批量修改备注' : '批量补录序列号',
)
const selectedRows = computed(() => assets.value.filter((a) => selectedIds.value.has(a.id)))
function focusNextSerial(i: number) {
  const els = document.querySelectorAll<HTMLInputElement>('.serial-input')
  els[i + 1]?.focus()
}

/** 打印标签 V2 形状：QR 编码内部编号，SN/品目/供应商/采购日期随签（品目信息自联字典列映射） */
function toPrintShape(item: FixedAsset) {
  return {
    id: item.id,
    内部编号: item.内部编号,
    序列号: item.序列号 || '',
    资产名称: item.itemName || '',
    品目编号: item.itemCode || '',
    分公司: item.branchName || '',
    供应商: item.供应商 || '',
    采购日期: item.采购日期 || '',
  }
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
      pending_serial: filters.value.pendingSerial ? '1' : undefined,
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
    branchOptions.value = data.map((b: any) => ({ value: b.name, label: b.name }))
  } catch { /* 静默 */ }
}

const resetFilters = () => {
  filters.value = { branch: '', status: '', pendingSerial: false, keyword: '' }
  pagination.value.page = 1
  fetchAssets()
}

const handlePaginationChange = (page: number, pageSize: number) => {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchAssets()
}

watch(filters, () => { selectedIds.value = new Set(); pagination.value.page = 1; fetchAssets() }, { deep: true })

onMounted(() => { fetchAssets(); fetchBranches() })
</script>

<template>
  <div class="fixed-asset-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">固定资产实例</h1>
        <p class="page-desc">一物一档 · 共{{ pagination.total }}台 · 变动经流转单</p>
      </div>
      <div class="header-actions">
        <div v-if="canSupplement" class="batch-wrap">
          <button class="btn-secondary" @click="batchMenuOpen = !batchMenuOpen">
            批量操作{{ selectedIds.size ? `（${selectedIds.size}）` : '' }} ▾
          </button>
          <div v-if="batchMenuOpen" class="batch-menu" @mouseleave="batchMenuOpen = false">
            <button :disabled="!selectedIds.size" @click="printSelected">打印标签</button>
            <button :disabled="!selectedIds.size" @click="openBatch('supplier')">修改供应商</button>
            <button :disabled="!selectedIds.size" @click="openBatch('spec')">修改规格</button>
            <button :disabled="!selectedIds.size" @click="openBatch('remark')">修改备注</button>
            <button :disabled="!selectedIds.size" @click="openBatch('serial')">补录序列号</button>
          </div>
        </div>
        <button class="btn-secondary" @click="handleExport" :disabled="exporting">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {{ exporting ? '导出中...' : '导出' }}
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
          <input v-model="filters.keyword" type="text" placeholder="搜索内部编号、品目、序列号、使用人..." class="filter-input" />
        </div>
        <div class="filter-item">
          <BranchFilterSelect v-model="filters.branch" :options="branchOptions" />
        </div>
        <div class="filter-item">
          <select v-model="filters.status" class="filter-select">
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <label class="pending-filter">
          <input v-model="filters.pendingSerial" type="checkbox" />
          仅看待补录
        </label>
        <button class="filter-reset" @click="resetFilters">重置</button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th class="check-col"><input type="checkbox" :checked="pageAllSelected" @change="toggleSelectAll" title="全选本页" /></th>
            <th>序号</th>
            <th>图片</th>
            <th>分公司</th>
            <th>内部编号</th>
            <th>品目编号</th>
            <th>品目名称</th>
            <th>规格</th>
            <th>序列号</th>
            <th>当前状态</th>
            <th>使用人</th>
            <th>部门</th>
            <th>入库日期</th>
            <th>供应商</th>
            <th>采购日期</th>
            <th>备注</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="17" class="empty-cell">加载中...</td></tr>
          <tr v-else-if="assets.length === 0"><td colspan="17" class="empty-cell">暂无实例数据</td></tr>
          <tr v-for="(item, index) in assets" :key="item.id" v-else>
            <td class="check-col"><input type="checkbox" :checked="selectedIds.has(item.id)" @change="toggleSelect(item)" /></td>
            <td>{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
            <td class="image-cell">
              <el-image
                v-if="item.图片"
                :src="item.图片"
                :preview-src-list="[item.图片]"
                preview-teleported
                fit="cover"
                class="row-thumb"
              />
              <span v-else class="thumb-empty">—</span>
            </td>
            <td>{{ item.branchName || '-' }}</td>
            <td><span class="asset-code">{{ item.内部编号 }}</span></td>
            <td>{{ item.itemCode }}</td>
            <td>{{ item.itemName || '-' }}</td>
            <td>{{ item.itemSpec || '-' }}</td>
            <td>
              <span v-if="item.序列号">{{ item.序列号 }}</span>
              <span v-else class="pending-tag">待补录</span>
            </td>
            <td><StatusBadge :status="item.当前状态 || ''" /></td>
            <td>{{ item.使用人 || '-' }}</td>
            <td>{{ item.departmentName || '-' }}</td>
            <td><span class="date-text">{{ item.入库日期 || '-' }}</span></td>
            <td>{{ item.供应商 || '-' }}</td>
            <td><span class="date-text">{{ item.采购日期 || '-' }}</span></td>
            <td>{{ item.备注 || '-' }}</td>
            <td class="action-col">
              <button v-if="canSupplement" class="action-btn" title="编辑" @click="openEdit(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button class="action-btn" title="打印标签" @click="printSingleLabel(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 6 2 18 2 18 9"/>
                  <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                  <rect x="6" y="14" width="12" height="8"/>
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination :total="pagination.total" :current-page="pagination.page" :page-size="pagination.pageSize" @change="handlePaginationChange" />

    <!-- 行编辑弹窗（双栏：左编辑 右生平） -->
    <el-dialog v-model="editVisibleProxy" title="编辑实例" width="920px" :close-on-click-modal="false" top="6vh">
      <div v-if="editing" class="edit-dual">
        <!-- 左栏：编辑表单 -->
        <div class="edit-pane">
          <el-form label-width="72px">
            <el-form-item label="内部编号"><span class="asset-code">{{ editing.内部编号 }}</span></el-form-item>
            <el-form-item label="品目名称">{{ editing.itemName || '-' }}</el-form-item>
            <el-form-item label="使用人">{{ editing.使用人 || '-' }}</el-form-item>
            <el-form-item label="部门">{{ editing.departmentName || '-' }}</el-form-item>
            <el-form-item label="序列号"><el-input v-model="editForm.序列号" placeholder="扫码或手工录入" /></el-form-item>
            <el-form-item label="备注"><el-input v-model="editForm.备注" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="规格"><el-input v-model="editForm.规格" placeholder="修改后实例档案显示此规格" /></el-form-item>
            <el-form-item label="供应商"><el-input v-model="editForm.供应商" placeholder="修改后实例档案显示此供应商" /></el-form-item>
            <el-form-item label="采购日期">
              <el-date-picker v-model="editForm.采购日期" type="date" value-format="YYYY-MM-DD" placeholder="空=沿用出生单日期" style="width: 100%" clearable />
            </el-form-item>
            <el-form-item label="物品图片">
              <div class="edit-image-block">
                <el-image v-if="imagePreviewFor(editing)" :src="imagePreviewFor(editing)" fit="cover" class="edit-image-large" :preview-src-list="[imagePreviewFor(editing)!]" preview-teleported />
                <div v-else class="edit-image-empty">暂无图片</div>
                <input ref="editImageInput" type="file" accept="image/jpeg,image/png,image/webp" style="display:none" @change="handleEditImageSelect" />
                <div class="edit-image-actions">
                  <el-button size="small" @click="editImageInput?.click()">{{ imagePreviewFor(editing) ? '更换图片' : '上传图片' }}</el-button>
                  <el-button v-if="imagePreviewFor(editing)" size="small" @click="handleEditImageDelete">删除</el-button>
                </div>
              </div>
            </el-form-item>
          </el-form>
        </div>
        <!-- 右栏：实例生平 -->
        <div class="edit-pane timeline-pane">
          <div v-if="timelineLoading" class="timeline-empty">生平加载中...</div>
          <div v-else-if="!timeline" class="timeline-empty">暂无生平数据</div>
          <template v-else>
            <div class="timeline-head">
              <div class="timeline-code">{{ timeline.instance.内部编号 }}</div>
              <div class="timeline-meta">
                {{ timeline.instance.itemCode }} · {{ timeline.instance.itemName }} ·
                <StatusBadge :status="timeline.instance.当前状态" />
              </div>
              <div class="timeline-meta dim">
                供应商：{{ timeline.birth?.供应商 || '（存量档案）' }}
                <template v-if="timeline.birth?.采购日期"> · 采购日期：{{ timeline.birth.采购日期 }}</template>
              </div>
            </div>
            <table class="data-table timeline-table">
              <thead>
                <tr><th>日期</th><th>单据</th><th>类型</th><th>使用人</th><th>状态</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in timeline.timeline" :key="row.transferId + '-' + row.行号">
                  <td><span class="date-text">{{ row.日期 }}</span></td>
                  <td>{{ row.单据编号 || '-' }}</td>
                  <td>{{ row.actionType }}</td>
                  <td>{{ row.使用人 || '-' }}</td>
                  <td>{{ row.审批状态 }}</td>
                </tr>
                <tr v-if="timeline.timeline.length === 0"><td colspan="5" class="empty-cell">暂无流转记录</td></tr>
              </tbody>
            </table>
          </template>
        </div>
      </div>
      <template #footer>
        <el-button @click="editing = null">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="handleEditSave">保存</el-button>
      </template>
    </el-dialog>



    <!-- 批量操作弹窗 -->
    <el-dialog v-model="batchVisibleProxy" :title="batchTitle" width="460px" :close-on-click-modal="false">
      <div v-if="batchDialog === 'serial'" class="serial-list">
        <p class="serial-hint">逐台输入序列号（扫码后回车自动跳下一行），与勾选顺序一一对应：</p>
        <div v-for="(a, i) in selectedRows" :key="a.id" class="serial-row">
          <span class="serial-code">{{ a.内部编号 }}</span>
          <input
            v-model="batchSerials[i]"
            type="text"
            class="serial-input"
            placeholder="扫码或输入"
            @keydown.enter.prevent="focusNextSerial(i)"
          />
        </div>
      </div>
      <el-input v-else v-model="batchValue" :placeholder="batchDialog === 'supplier' ? '统一设置的供应商名称' : batchDialog === 'spec' ? '统一设置的规格' : '统一设置的备注内容'" />
      <template #footer>
        <el-button @click="batchDialog = null">取消</el-button>
        <el-button type="primary" :loading="batchSaving" @click="submitBatch">应用（{{ countSelected() }} 台）</el-button>
      </template>
    </el-dialog>

    <!-- 标签打印弹窗 -->
    <AssetPrintDialog :visible="showPrintDialog" :assets="printItems" @close="showPrintDialog = false" />
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
.filter-section { background: var(--color-bg-card); border-radius: 12px; padding: var(--space-4); margin-bottom: var(--space-4); border: 1px solid var(--color-border); flex-shrink: 0; }
.filter-row { display: flex; gap: var(--space-3); align-items: center; }
.filter-item { position: relative; }
.filter-item.search { flex: 1; position: relative; }
.filter-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; color: var(--color-text-tertiary); }
.filter-input { width: 100%; height: 38px; padding: 0 var(--space-4) 0 38px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); color: var(--color-text-primary); }
.filter-input:focus { outline: none; border-color: var(--color-primary-400); box-shadow: 0 0 0 3px var(--color-primary-100); }
.filter-select { height: 38px; padding: 0 var(--space-4); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; min-width: 120px; }
.pending-filter { display: flex; align-items: center; gap: 6px; font-size: var(--text-sm); color: var(--color-text-secondary); white-space: nowrap; cursor: pointer; }
.pending-filter input { width: 15px; height: 15px; cursor: pointer; }
.filter-reset { height: 38px; padding: 0 var(--space-4); background: transparent; border: none; color: var(--color-text-secondary); font-size: var(--text-sm); cursor: pointer; }
.filter-reset:hover { color: var(--color-primary-500); }
.table-container { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); overflow-x: auto; overflow-y: auto; flex: 1; min-height: 200px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table thead th { position: sticky; top: 0; z-index: 1; background: var(--color-bg-elevated); }
.data-table th { padding: var(--space-3) var(--space-4); text-align: left; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); white-space: nowrap; }
.data-table td { padding: var(--space-3) var(--space-4); font-size: var(--text-sm); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border-light); vertical-align: middle; }
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.empty-cell { text-align: center; color: var(--color-text-tertiary); padding: var(--space-8) var(--space-4) !important; }
.asset-code { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-primary-600); background: var(--color-primary-50); padding: 2px 8px; border-radius: 4px; }
.date-text { font-family: var(--font-mono); color: var(--color-text-secondary); font-size: var(--text-xs); white-space: nowrap; }
.pending-tag { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: var(--text-xs); color: var(--color-warning, #b45309); background: var(--color-warning-bg, #fef3c7); }
/* 编辑弹窗双栏 */
.edit-dual { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start; }
.edit-pane { min-width: 0; }
.timeline-pane { max-height: 62vh; overflow-y: auto; padding-left: 16px; border-left: 1px solid var(--color-border); }
.timeline-head { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.timeline-code { font-family: var(--font-mono); font-size: 15px; font-weight: 600; color: var(--color-primary-600); }
.timeline-meta { font-size: var(--text-sm); color: var(--color-text-secondary); }
.timeline-meta.dim { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.edit-image-block { display: flex; flex-direction: column; gap: 8px; }
.edit-image-large { width: 160px; height: 120px; border-radius: 8px; display: block; }
.edit-image-empty { width: 160px; height: 120px; border-radius: 8px; border: 1px dashed var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-text-tertiary); font-size: var(--text-sm); }
.edit-image-actions { display: flex; gap: 8px; }
@media (max-width: 768px) { .edit-dual { grid-template-columns: 1fr; } .timeline-pane { border-left: none; padding-left: 0; border-top: 1px solid var(--color-border); padding-top: 12px; } }
.image-cell { width: 56px; }
.check-col { width: 36px; text-align: center; }
.batch-wrap { position: relative; }
.batch-menu { position: absolute; right: 0; top: calc(100% + 6px); z-index: 20; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.12); padding: 6px; min-width: 148px; }
.batch-menu button { display: block; width: 100%; text-align: left; padding: 9px 12px; background: transparent; border: none; border-radius: 6px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.batch-menu button:hover { background: var(--color-primary-50); }
.batch-menu button:disabled { color: var(--color-text-tertiary); cursor: not-allowed; }
.serial-list { display: flex; flex-direction: column; gap: 8px; max-height: 340px; overflow-y: auto; }
.serial-hint { font-size: var(--text-sm); color: var(--color-text-tertiary); margin: 0 0 4px; }
.serial-row { display: flex; align-items: center; gap: 10px; }
.serial-code { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-primary-600); min-width: 150px; }
.serial-input { flex: 1; height: 34px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-bg-page); font-size: var(--text-sm); color: var(--color-text-primary); }
.check-col input { width: 15px; height: 15px; cursor: pointer; }
.row-thumb { width: 40px; height: 40px; border-radius: 4px; display: block; }
.thumb-empty { color: var(--color-text-tertiary); }
.image-view { display: flex; align-items: center; justify-content: center; height: 220px; background: var(--color-bg-page); border-radius: 8px; overflow: hidden; }
.image-full { width: 100%; height: 100%; }
.image-empty { color: var(--color-text-tertiary); font-size: var(--text-sm); }
.image-meta { display: flex; align-items: center; gap: var(--space-2); margin-top: var(--space-3); font-size: var(--text-sm); color: var(--color-text-secondary); }
.action-col { white-space: nowrap; }
.action-btn { width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; vertical-align: middle; margin-right: var(--space-1); background: transparent; border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer; color: var(--color-text-secondary); }
.action-btn:hover { border-color: var(--color-primary-300); color: var(--color-primary-600); }
.action-btn svg { width: 15px; height: 15px; }
.timeline-head { display: flex; flex-direction: column; gap: var(--space-1); margin-bottom: var(--space-4); }
.timeline-code { font-family: var(--font-mono); font-size: 16px; font-weight: 600; color: var(--color-primary-600); }
.timeline-meta { font-size: var(--text-sm); color: var(--color-text-secondary); }
.timeline-meta.dim { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.timeline-table th, .timeline-table td { padding: var(--space-2) var(--space-3); }
.timeline-empty { text-align: center; color: var(--color-text-tertiary); padding: var(--space-8); }
@media (max-width: 768px) { .page-header { flex-direction: column; align-items: flex-start; gap: var(--space-4); } .filter-row { flex-wrap: wrap; } .filter-item.search { flex: 1 1 100%; } }
</style>
