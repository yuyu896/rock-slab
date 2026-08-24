<script setup lang="ts">
import { ref, watch } from 'vue'
import { getLedgerAdjustments } from '@/api/assets'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { LedgerAdjustment } from '@/types'
import BasePagination from '@/components/BasePagination.vue'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const filters = ref({ branch: '', assetCode: '', dateFrom: '', dateTo: '' })
const branchOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部分公司' }])
const rows = ref<LedgerAdjustment[]>([])
const loading = ref(false)
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

watch(() => props.visible, (v) => {
  if (v) {
    pagination.value.page = 1
    fetchBranches()
    fetchRows()
  }
}, { immediate: true })

async function fetchBranches() {
  if (branchOptions.value.length > 1) return
  try {
    const { data } = await getBranches()
    branchOptions.value = [
      { value: '', label: '全部分公司' },
      ...data.map((b: any) => ({ value: String(b.id), label: b.name })),
    ]
  } catch (error) {
    console.error('Failed to fetch branches:', error)
  }
}

async function fetchRows() {
  loading.value = true
  try {
    const { data } = await getLedgerAdjustments({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      branch: filters.value.branch || undefined,
      assetCode: filters.value.assetCode.trim() || undefined,
      dateFrom: filters.value.dateFrom || undefined,
      dateTo: filters.value.dateTo || undefined,
    })
    rows.value = data.results
    pagination.value.total = data.count
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  pagination.value.page = 1
  fetchRows()
}

function resetFilters() {
  filters.value = { branch: '', assetCode: '', dateFrom: '', dateTo: '' }
  applyFilters()
}

function onPageChange(page: number, pageSize: number) {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchRows()
}

function fmtTime(value?: string) {
  return value ? value.replace('T', ' ').slice(0, 19) : '-'
}

function fmtColumn(value: string) {
  return value === '在库数量' ? '在库' : value === '在用数量' ? '在用' : '回收库'
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" role="dialog" aria-modal="true" @click.self="emit('close')">
    <div class="modal-content modal-lg">
      <div class="modal-header">
        <h3 class="modal-title">调整记录</h3>
        <button class="modal-close" aria-label="关闭" @click="emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div class="filter-row">
          <select v-model="filters.branch" class="filter-select" aria-label="筛选分公司">
            <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
          <input v-model="filters.assetCode" type="text" class="filter-input" placeholder="资产编号" @keyup.enter="applyFilters" />
          <input v-model="filters.dateFrom" type="date" class="filter-input date" aria-label="开始日期" />
          <span class="date-sep">至</span>
          <input v-model="filters.dateTo" type="date" class="filter-input date" aria-label="结束日期" />
          <button class="filter-apply" @click="applyFilters">查询</button>
          <button class="filter-apply" @click="resetFilters">重置</button>
        </div>

        <table class="data-table">
          <thead>
            <tr>
              <th>单据编号</th>
              <th>时间</th>
              <th>分公司</th>
              <th>资产编号</th>
              <th>目标列</th>
              <th>变动量</th>
              <th>事由</th>
              <th>经办人</th>
              <th>来源</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading && rows.length === 0">
              <td colspan="9" class="empty-cell">加载中...</td>
            </tr>
            <tr v-else-if="rows.length === 0">
              <td colspan="9" class="empty-cell">暂无调整单</td>
            </tr>
            <tr v-for="row in rows" :key="row.id">
              <td><span class="doc-no">{{ row.单据编号 }}</span></td>
              <td class="dim">{{ fmtTime(row.createdAt) }}</td>
              <td>{{ row.branchName }}</td>
              <td><span class="asset-code">{{ row.资产编号 }}</span></td>
              <td>{{ fmtColumn(row.目标列) }}</td>
              <td class="col-qty" :class="row.变动量 > 0 ? 'pos' : 'neg'">{{ row.变动量 > 0 ? '+' : '' }}{{ row.变动量 }}</td>
              <td class="reason-cell" :title="row.事由">{{ row.事由 }}</td>
              <td>{{ row.经办人姓名 || '-' }}</td>
              <td>{{ row.来源任务 || '手动' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="modal-footer">
        <BasePagination
          :total="pagination.total"
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          @change="onPageChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  display: flex; align-items: center; justify-content: center;
}
.modal-content {
  width: min(960px, calc(100vw - 32px));
  max-height: calc(100vh - 64px);
  background: var(--color-bg-card); border-radius: 12px;
  border: 1px solid var(--color-border);
  display: flex; flex-direction: column; overflow: hidden;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-4) var(--space-5); flex-shrink: 0;
  border-bottom: 1px solid var(--color-border);
}
.modal-title { margin: 0; font-size: var(--text-lg); font-weight: 600; }
.modal-close {
  border: none; background: none; font-size: 20px; cursor: pointer;
  color: var(--color-text-tertiary); line-height: 1;
}
.modal-body { padding: var(--space-4) var(--space-5); overflow: auto; display: flex; flex-direction: column; gap: var(--space-4); }
.filter-row { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; }
.filter-select, .filter-input {
  height: 34px; padding: 0 var(--space-3);
  border: 1px solid var(--color-border); border-radius: 8px;
  background: var(--color-bg-card); font-size: var(--text-sm);
}
.filter-select { min-width: 120px; }
.filter-input { width: 140px; }
.filter-input.date { width: 130px; }
.date-sep { font-size: var(--text-sm); color: var(--color-text-tertiary); }
.filter-apply {
  height: 34px; padding: 0 var(--space-3); border-radius: 8px;
  border: 1px solid var(--color-border); background: var(--color-bg-card);
  font-size: var(--text-sm); cursor: pointer;
}
.filter-apply:hover { border-color: var(--color-primary-300); }

.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  text-align: left; padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border); white-space: nowrap;
  position: sticky; top: 0; background: var(--color-bg-elevated); z-index: 1;
}
.data-table td {
  padding: var(--space-2) var(--space-3); font-size: var(--text-sm);
  color: var(--color-text-primary); border-bottom: 1px solid var(--color-border-light);
  white-space: nowrap;
}
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.doc-no { font-family: var(--font-mono); font-size: 12px; }
.asset-code { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-primary-600); }
.col-qty { text-align: right; font-variant-numeric: tabular-nums; }
.col-qty.pos { color: var(--color-success); }
.col-qty.neg { color: var(--color-danger); }
.reason-cell { max-width: 260px; overflow: hidden; text-overflow: ellipsis; }
.dim { color: var(--color-text-tertiary); font-size: 12px; }
.empty-cell { text-align: center; padding: var(--space-8) 0; color: var(--color-text-tertiary); }
.modal-footer {
  padding: var(--space-3) var(--space-5); border-top: 1px solid var(--color-border);
  display: flex; justify-content: flex-end; flex-shrink: 0;
}
</style>
