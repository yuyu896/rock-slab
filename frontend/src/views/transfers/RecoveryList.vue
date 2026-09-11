<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useTransferList } from '@/composables/useTransferList'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import { transferDocSummary } from '@/types'
import BasePagination from '@/components/BasePagination.vue'

const {
  typeLabel, typeColor,
  filters, pagination, loading, transfers, branchOptions, statusOptions,
  stats, getStatusStyle, fetchTransfers, resetFilters,
  handleApprove, handleReject,
  handleExport,
} = useTransferList('recovery')

const router = useRouter()

/** 去向展示（存量 recycle_bin 为历史档案：当时入过回收库） */
const DEST_LABELS: Record<string, string> = {
  restock: '重新入库',
  dispose: '直接处置',
  recycle_bin: '入回收库',
}

function openCreatePage() {
  router.push('/transfers/recovery/create')
}
</script>

<template>
  <div class="transfer-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">{{ typeLabel }}</h1>
        <p class="page-desc">管理资产回收记录</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="handleExport">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          导出
        </button>
        <button class="btn-primary" @click="openCreatePage">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新建回收
        </button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card"><div class="stat-content"><span class="stat-value">{{ stats.total }}</span><span class="stat-label">回收总数</span></div></div>
      <div class="stat-card pending"><div class="stat-content"><span class="stat-value">{{ stats.pending }}</span><span class="stat-label">待审批</span></div></div>
      <div class="stat-card success"><div class="stat-content"><span class="stat-value">{{ stats.approved }}</span><span class="stat-label">已通过</span></div></div>
      <div class="stat-card danger"><div class="stat-content"><span class="stat-value">{{ stats.rejected }}</span><span class="stat-label">已驳回</span></div></div>
    </div>

    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item search">
          <svg class="filter-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input v-model="filters.keyword" type="text" placeholder="搜索单号、品目编号、名称..." class="filter-input" />
        </div>
        <div class="filter-item">
          <BranchFilterSelect v-model="filters.fromBranch" :options="branchOptions" />
        </div>
        <div class="filter-item">
          <select v-model="filters.status" class="filter-select">
            <option value="">全部状态</option>
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <button class="filter-reset" @click="resetFilters">重置</button>
      </div>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>单号</th><th>入库日期</th><th>分公司</th><th>回收分类</th><th>去向</th>
            <th>品项</th><th class="col-num">品项数</th><th class="col-num">总数量</th>
            <th>出库日期</th><th>所属部门</th><th>状态</th><th>经办人</th><th>备注</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in transfers" :key="item.id">
            <td><span class="doc-number">{{ item.单据编号 || item.id.slice(0, 8) }}</span></td>
            <td><span class="date-text">{{ item.调拨日期 || '-' }}</span></td>
            <td>{{ item.调出分公司 || '-' }}</td>
            <td>{{ item.回收分类 || '-' }}</td>
            <td>{{ DEST_LABELS[item.回收去向 ?? ''] || item.回收去向 || '-' }}</td>
            <td><span class="asset-name">{{ transferDocSummary(item).name }}</span></td>
            <td class="col-num">{{ item.品项数 ?? item.lines?.length ?? '-' }}</td>
            <td><span class="qty-value">{{ item.总数量 ?? '-' }}</span></td>
            <td><span class="date-text">{{ item.出库日期 || '-' }}</span></td>
            <td>{{ item.调出部门 || '-' }}</td>
            <td><span class="status-badge" :style="getStatusStyle(item.审批状态)">{{ item.审批状态 }}</span></td>
            <td>{{ item.采购经办人 || '-' }}</td>
            <td>{{ item.备注 || '-' }}</td>
            <td>
              <div class="action-buttons">
                <button class="action-btn" @click="router.push('/transfers/recovery/' + item.id)">详情</button>
                <button v-if="item.审批状态 === '待审批'" class="action-btn approve" @click="handleApprove(item)">通过</button>
                <button v-if="item.审批状态 === '待审批'" class="action-btn reject" @click="handleReject(item)">驳回</button>
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
      @change="(page, pageSize) => { pagination.page = page; pagination.pageSize = pageSize; fetchTransfers() }"
    />


  </div>
</template>

<style scoped>
.transfer-page { width: 100%; max-width: 1600px; margin: 0 auto; min-width: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-6); flex-shrink: 0; }
.header-info { display: flex; flex-direction: column; gap: var(--space-1); }
.page-title { font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.page-desc { font-size: var(--text-sm); color: var(--color-text-tertiary); margin: 0; }
.header-actions { display: flex; gap: var(--space-3); }
.btn-secondary, .btn-primary { display: flex; align-items: center; gap: var(--space-2); height: 40px; padding: 0 var(--space-5); border-radius: 10px; font-size: var(--text-sm); font-weight: 500; cursor: pointer; }
.btn-secondary { background: var(--color-bg-card); border: 1px solid var(--color-border); color: var(--color-text-primary); }
.btn-primary { background: var(--color-primary-500); border: 1px solid var(--color-primary-500); color: white; }
.btn-secondary svg, .btn-primary svg { width: 18px; height: 18px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); margin-bottom: var(--space-5); flex-shrink: 0; }
.stat-card { background: var(--color-bg-card); border-radius: 12px; padding: var(--space-4); border: 1px solid var(--color-border); }
.stat-card.pending { border-left: 4px solid oklch(0.60 0.14 85); }
.stat-card.success { border-left: 4px solid var(--color-success); }
.stat-card.danger { border-left: 4px solid var(--color-danger); }
.stat-content { display: flex; flex-direction: column; }
.stat-value { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); }
.stat-label { font-size: var(--text-sm); color: var(--color-text-tertiary); margin-top: var(--space-1); }
.filter-section { margin-bottom: var(--space-4); flex-shrink: 0; }
.filter-row { display: flex; gap: var(--space-3); }
.filter-item.search { flex: 1; position: relative; }
.filter-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; color: var(--color-text-tertiary); }
.filter-input, .filter-select { height: 38px; padding: 0 var(--space-4); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); font-size: var(--text-sm); }
.filter-item.search .filter-input { width: 100%; padding-left: 38px; }
.filter-select { min-width: 140px; }
.filter-reset { height: 38px; padding: 0 var(--space-4); background: transparent; border: none; color: var(--color-text-secondary); font-size: var(--text-sm); cursor: pointer; }
.filter-reset:hover { color: var(--color-primary-500); }
.table-container { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); overflow: auto; margin-bottom: var(--space-4); flex: 1; min-height: 200px; }
.data-table { width: 100%; border-collapse: collapse; min-width: 1400px; }
.data-table thead th { position: sticky; top: 0; z-index: 1; }
.data-table th { background: var(--color-bg-elevated); padding: var(--space-3) var(--space-3); text-align: left; font-size: var(--text-xs); font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); white-space: nowrap; }
.data-table td { padding: var(--space-3); font-size: var(--text-sm); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border-light); vertical-align: middle; white-space: nowrap; }
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.date-text { font-family: var(--font-mono); color: var(--color-text-secondary); font-size: var(--text-xs); }
.asset-code { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-primary-600); background: var(--color-primary-50); padding: 2px 6px; border-radius: 4px; }
.asset-name { font-weight: 500; }
.qty-value { font-weight: 600; }
.status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: var(--text-xs); font-weight: 500; }
.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); }
.detail-field { display: flex; flex-direction: column; gap: 4px; }
.detail-label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.detail-value { font-size: var(--text-sm); color: var(--color-text-primary); font-weight: 500; }
.detail-value.code { font-family: var(--font-mono); color: var(--color-primary-600); }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); }
.form-item { display: flex; flex-direction: column; gap: var(--space-2); }
.form-item.full { grid-column: span 2; }
.form-label { font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
.required { color: var(--color-danger); }
.form-input, .form-select, .form-textarea { height: 40px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); }
.form-textarea { height: auto; padding: var(--space-3); resize: vertical; }
.btn-confirm { height: 40px; padding: 0 var(--space-5); background: var(--color-primary-500); border: none; border-radius: 8px; font-size: var(--text-sm); font-weight: 500; color: white; cursor: pointer; }
.btn-reject { height: 40px; padding: 0 var(--space-5); background: oklch(0.92 0.10 25); border: none; border-radius: 8px; font-size: var(--text-sm); font-weight: 500; color: var(--color-danger); cursor: pointer; }
@keyframes import-spin { to { transform: rotate(360deg); } }
@media (max-width: 1200px) { .stats-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .page-header { flex-direction: column; align-items: flex-start; gap: var(--space-4); } .stats-row { grid-template-columns: 1fr; } }
</style>
