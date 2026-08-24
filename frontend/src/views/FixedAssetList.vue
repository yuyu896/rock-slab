<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getFixedAssets, exportFixedAssets, supplementFixedAsset, getFixedAssetTimeline } from '@/api/assets'
import type { FixedAsset, FixedAssetTimeline } from '@/types'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import BasePagination from '@/components/BasePagination.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import AssetPrintDialog from './assets/AssetPrintDialog.vue'
import RecoveryDialog from './assets/RecoveryDialog.vue'
import { INSTANCE_STATUS_OPTIONS } from '@/constants'

const { canManageAssets, can } = usePermission()
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

// ── 序列号补录（仅 序列号/备注，manage_instances） ──
const supplementing = ref<FixedAsset | null>(null)
const supplementForm = ref({ 序列号: '', 备注: '' })
const supplementSaving = ref(false)
const supplementVisibleProxy = computed({
  get: () => supplementing.value !== null,
  set: (v: boolean) => { if (!v) supplementing.value = null },
})

function openSupplement(asset: FixedAsset) {
  supplementing.value = asset
  supplementForm.value = { 序列号: asset.序列号 || '', 备注: asset.备注 || '' }
}

async function handleSupplement() {
  if (!supplementing.value) return
  supplementSaving.value = true
  try {
    await supplementFixedAsset(supplementing.value.id, supplementForm.value)
    ElMessage.success('补录成功')
    supplementing.value = null
    await fetchAssets()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    supplementSaving.value = false
  }
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

// ── 行内回收（即时生效：入回收库/直接处置 → 实例转回收库/退役，档案保留） ──
const showRecoveryDialog = ref(false)
const recoveringAsset = ref<FixedAsset | null>(null)

function openRecovery(asset: FixedAsset) {
  recoveringAsset.value = asset
  showRecoveryDialog.value = true
}

// ── 标签打印 ──
const showPrintDialog = ref(false)
const printItems = ref<any[]>([])

function printSingleLabel(item: FixedAsset) {
  printItems.value = [toPrintShape(item)]
  showPrintDialog.value = true
}

/** 打印弹窗沿用旧字段形状（品目信息自联字典列映射） */
function toPrintShape(item: FixedAsset) {
  return {
    id: item.id,
    资产编号: item.itemCode,
    资产名称: item.itemName,
    分公司: item.branchName || '',
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
    branchOptions.value = [
      { value: '', label: '全部分公司' },
      ...data.map((b: any) => ({ value: b.name, label: b.name })),
    ]
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

watch(filters, () => { pagination.value.page = 1; fetchAssets() }, { deep: true })

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
          <select v-model="filters.branch" class="filter-select">
            <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
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
            <th>序号</th>
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
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="14" class="empty-cell">加载中...</td></tr>
          <tr v-else-if="assets.length === 0"><td colspan="14" class="empty-cell">暂无实例数据</td></tr>
          <tr v-for="(item, index) in assets" :key="item.id" v-else>
            <td>{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
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
            <td class="action-col">
              <button v-if="canSupplement" class="action-btn" title="补录序列号" @click="openSupplement(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <button class="action-btn" title="生平" @click="openTimeline(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
              </button>
              <button class="action-btn" title="打印标签" @click="printSingleLabel(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 6 2 18 2 18 9"/>
                  <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                  <rect x="6" y="14" width="12" height="8"/>
                </svg>
              </button>
              <button v-if="canManageAssets && item.当前状态 === '在用'" class="action-btn" title="回收" @click="openRecovery(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="1 4 1 10 7 10"/>
                  <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BasePagination :total="pagination.total" :current-page="pagination.page" :page-size="pagination.pageSize" @change="handlePaginationChange" />

    <!-- 补录弹窗（仅 序列号/备注） -->
    <el-dialog v-model="supplementVisibleProxy" title="序列号补录" width="460px" :close-on-click-modal="false">
      <el-form label-width="72px" v-if="supplementing">
        <el-form-item label="内部编号"><span class="asset-code">{{ supplementing.内部编号 }}</span></el-form-item>
        <el-form-item label="序列号"><el-input v-model="supplementForm.序列号" placeholder="扫码或手工录入" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="supplementForm.备注" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="supplementing = null">取消</el-button>
        <el-button type="primary" :loading="supplementSaving" @click="handleSupplement">保存</el-button>
      </template>
    </el-dialog>

    <!-- 生平抽屉 -->
    <el-drawer v-model="timelineVisibleProxy" title="实例生平" size="560px">
      <div v-if="timelineLoading" class="timeline-empty">加载中...</div>
      <div v-else-if="!timeline" class="timeline-empty">暂无数据</div>
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
    </el-drawer>

    <!-- 标签打印弹窗 -->
    <AssetPrintDialog :visible="showPrintDialog" :assets="printItems" @close="showPrintDialog = false" />

    <!-- 行内回收（即时生效 → 实例转回收库/退役） -->
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
.action-col { display: flex; gap: var(--space-1); }
.action-btn { width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; background: transparent; border: 1px solid var(--color-border); border-radius: 6px; cursor: pointer; color: var(--color-text-secondary); }
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
