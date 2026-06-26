<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useTransferList } from '@/composables/useTransferList'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import BasePagination from '@/components/BasePagination.vue'

const {
  typeLabel, typeColor,
  filters, pagination, loading, transfers, branchOptions, statusOptions,
  stats, getStatusStyle, fetchTransfers, resetFilters,
  showDetailModal, detailItem, detailLoading, viewDetail,
  handleApprove, handleReject,
  showImportModal, importLoading, importResult, openImportModal, handleDownloadTemplate, handleImportFile,
  handleExport,
} = useTransferList('assign')

const router = useRouter()

function openCreatePage() {
  router.push('/transfers/assign/create')
}
</script>

<template>
  <div class="transfer-page">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">{{ typeLabel }}</h1>
        <p class="page-desc">管理资产领用出库流程</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="handleExport">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          导出
        </button>
        <button class="btn-secondary" @click="openImportModal">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          批量导入
        </button>
        <button class="btn-primary" @click="openCreatePage">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新建领用
        </button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-card"><div class="stat-content"><span class="stat-value">{{ stats.total }}</span><span class="stat-label">流转总数</span></div></div>
      <div class="stat-card pending"><div class="stat-content"><span class="stat-value">{{ stats.pending }}</span><span class="stat-label">待审批</span></div></div>
      <div class="stat-card success"><div class="stat-content"><span class="stat-value">{{ stats.approved }}</span><span class="stat-label">已通过</span></div></div>
      <div class="stat-card danger"><div class="stat-content"><span class="stat-value">{{ stats.rejected }}</span><span class="stat-label">已驳回</span></div></div>
    </div>

    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item search">
          <svg class="filter-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input v-model="filters.keyword" type="text" placeholder="搜索资产编号、名称..." class="filter-input" />
        </div>
        <div class="filter-item">
          <select v-model="filters.fromBranch" class="filter-select">
            <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">{{ opt.value ? opt.label : '调出分公司' }}</option>
          </select>
        </div>
        <div class="filter-item">
          <select v-model="filters.toBranch" class="filter-select">
            <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">{{ opt.value ? opt.label : '调入分公司' }}</option>
          </select>
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
            <th>日期</th>
            <th>资产编号</th>
            <th>资产名称</th>
            <th>数量</th>
            <th>所属分公司</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in transfers" :key="item.id">
            <td><span class="date-text">{{ $options.filters?.formatDate?.(item.createdAt) || item.createdAt?.slice(0, 10) }}</span></td>
            <td><span class="asset-code">{{ item.资产编号 }}</span></td>
            <td><span class="asset-name">{{ item.资产名称 }}</span></td>
            <td><span class="qty-value">{{ item.调拨数量 || '-' }}</span></td>
            <td><span class="flow-text">{{ item.fromBranchName || item.调出分公司 || '-' }}</span></td>
            <td><span class="status-badge" :style="getStatusStyle(item.审批状态)">{{ item.审批状态 }}</span></td>
            <td>
              <div class="action-buttons">
                <button class="action-btn" @click="viewDetail(item)">详情</button>
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

    <!-- 详情弹窗 -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>流转详情</h3>
          <button class="modal-close" @click="showDetailModal = false">&times;</button>
        </div>
        <div v-if="detailItem" class="modal-body">
          <div class="detail-grid">
            <div class="detail-field"><span class="detail-label">流转类型</span><span class="detail-value"><span class="type-badge" :style="typeColor">{{ typeLabel }}</span></span></div>
            <div class="detail-field"><span class="detail-label">审批状态</span><span class="detail-value"><span class="status-badge" :style="getStatusStyle(detailItem.审批状态)">{{ detailItem.审批状态 }}</span></span></div>
            <div class="detail-field"><span class="detail-label">资产编号</span><span class="detail-value code">{{ detailItem.资产编号 }}</span></div>
            <div class="detail-field"><span class="detail-label">资产名称</span><span class="detail-value">{{ detailItem.资产名称 }}</span></div>
            <div class="detail-field"><span class="detail-label">数量</span><span class="detail-value">{{ detailItem.调拨数量 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">规格型号</span><span class="detail-value">{{ detailItem.规格型号 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">调出分公司</span><span class="detail-value">{{ detailItem.调出分公司 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">调入分公司</span><span class="detail-value">{{ detailItem.调入分公司 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">使用人</span><span class="detail-value">{{ detailItem.使用人 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">所属部门</span><span class="detail-value">{{ detailItem.所属部门 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">备注</span><span class="detail-value">{{ detailItem.备注 || '-' }}</span></div>
            <div v-if="detailItem.审批人" class="detail-field"><span class="detail-label">审批人</span><span class="detail-value">{{ detailItem.审批人 }}</span></div>
            <div v-if="detailItem.审批时间" class="detail-field"><span class="detail-label">审批时间</span><span class="detail-value">{{ detailItem.审批时间 }}</span></div>
            <div class="detail-field"><span class="detail-label">创建时间</span><span class="detail-value">{{ detailItem.createdAt?.slice(0, 10) }}</span></div>
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="detailItem?.审批状态 === '待审批'" class="btn-reject" @click="handleReject(detailItem); showDetailModal = false">驳回</button>
          <button v-if="detailItem?.审批状态 === '待审批'" class="btn-confirm" @click="handleApprove(detailItem); showDetailModal = false">通过</button>
          <button class="btn-cancel" @click="showDetailModal = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 批量导入弹窗 -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="showImportModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>批量导入流转记录</h3>
          <button class="modal-close" @click="showImportModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="import-step">
            <div class="import-step-header"><span class="import-step-num">1</span><span class="import-step-title">下载导入模板</span></div>
            <p class="import-step-desc">请先下载模板文件，按格式填写流转数据后上传</p>
            <button class="btn-secondary import-template-btn" @click="handleDownloadTemplate">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              下载模板
            </button>
          </div>
          <div class="import-step">
            <div class="import-step-header"><span class="import-step-num">2</span><span class="import-step-title">上传填写好的 Excel 文件</span></div>
            <label class="import-upload-area" :class="{ 'upload-loading': importLoading }">
              <input type="file" accept=".xlsx,.xls" class="import-file-input" @change="handleImportFile" :disabled="importLoading" />
              <template v-if="importLoading"><div class="import-spinner"></div><span>正在导入...</span></template>
              <template v-else>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
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
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showImportModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.transfer-page { max-width: 1400px; margin: 0 auto; min-width: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-6); }
.header-info { display: flex; flex-direction: column; gap: var(--space-1); }
.page-title { font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.page-desc { font-size: var(--text-sm); color: var(--color-text-tertiary); margin: 0; }
.header-actions { display: flex; gap: var(--space-3); }
.btn-secondary, .btn-primary { display: flex; align-items: center; gap: var(--space-2); height: 40px; padding: 0 var(--space-5); border-radius: 10px; font-size: var(--text-sm); font-weight: 500; cursor: pointer; }
.btn-secondary { background: var(--color-bg-card); border: 1px solid var(--color-border); color: var(--color-text-primary); }
.btn-primary { background: var(--color-primary-500); border: 1px solid var(--color-primary-500); color: white; }
.btn-secondary svg, .btn-primary svg { width: 18px; height: 18px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); margin-bottom: var(--space-5); }
.stat-card { background: var(--color-bg-card); border-radius: 12px; padding: var(--space-4); border: 1px solid var(--color-border); }
.stat-card.pending { border-left: 4px solid oklch(0.60 0.14 85); }
.stat-card.success { border-left: 4px solid var(--color-success); }
.stat-card.danger { border-left: 4px solid var(--color-danger); }
.stat-content { display: flex; flex-direction: column; }
.stat-value { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); }
.stat-label { font-size: var(--text-sm); color: var(--color-text-tertiary); margin-top: var(--space-1); }
.filter-section { margin-bottom: var(--space-4); }
.filter-row { display: flex; gap: var(--space-3); }
.filter-item.search { flex: 1; position: relative; }
.filter-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; color: var(--color-text-tertiary); }
.filter-input, .filter-select { height: 38px; padding: 0 var(--space-4); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); font-size: var(--text-sm); }
.filter-item.search .filter-input { width: 100%; padding-left: 38px; }
.filter-select { min-width: 140px; }
.filter-reset { height: 38px; padding: 0 var(--space-4); background: transparent; border: none; color: var(--color-text-secondary); font-size: var(--text-sm); cursor: pointer; }
.filter-reset:hover { color: var(--color-primary-500); }
.table-container { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); overflow: hidden; margin-bottom: var(--space-4); }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { background: var(--color-bg-elevated); padding: var(--space-3) var(--space-4); text-align: left; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); }
.data-table td { padding: var(--space-3) var(--space-4); font-size: var(--text-sm); color: var(--color-text-primary); border-bottom: 1px solid var(--color-border-light); vertical-align: middle; }
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.type-badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: var(--text-xs); font-weight: 500; }
.date-text { font-family: var(--font-mono); color: var(--color-text-secondary); }
.asset-code { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-primary-600); background: var(--color-primary-50); padding: 2px 6px; border-radius: 4px; }
.asset-name { font-weight: 500; }
.flow-text { font-size: var(--text-sm); color: var(--color-text-secondary); }
.qty-value { font-weight: 600; font-size: var(--text-base); }
.status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: var(--text-xs); font-weight: 500; }
@import '@/styles/action-buttons.css';

.pagination-section { display: flex; justify-content: space-between; align-items: center; }
.pagination-info { font-size: var(--text-sm); color: var(--color-text-tertiary); }
.pagination-controls { display: flex; gap: var(--space-1); }
.page-btn { min-width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 6px; font-size: var(--text-sm); cursor: pointer; }
.page-btn:hover:not(:disabled):not(.active) { border-color: var(--color-primary-300); }
.page-btn.active { background: var(--color-primary-500); border-color: var(--color-primary-500); color: white; }
.page-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.page-btn svg { width: 16px; height: 16px; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { width: 640px; background: var(--color-bg-card); border-radius: 16px; overflow: hidden; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { font-size: var(--text-lg); font-weight: 600; margin: 0; }
.modal-close { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; font-size: 20px; color: var(--color-text-tertiary); cursor: pointer; border-radius: 6px; }
.modal-close:hover { background: var(--color-bg-elevated); }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: var(--space-3); padding: 12px 20px; border-top: 1px solid var(--color-border); }
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
.btn-cancel { height: 40px; padding: 0 var(--space-5); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.btn-confirm { height: 40px; padding: 0 var(--space-5); background: var(--color-primary-500); border: none; border-radius: 8px; font-size: var(--text-sm); font-weight: 500; color: white; cursor: pointer; }
.btn-reject { height: 40px; padding: 0 var(--space-5); background: oklch(0.92 0.10 25); border: none; border-radius: 8px; font-size: var(--text-sm); font-weight: 500; color: var(--color-danger); cursor: pointer; }
.import-step { margin-bottom: 16px; }
.import-step-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.import-step-num { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; background: var(--color-primary-500); color: white; border-radius: 50%; font-size: var(--text-xs); font-weight: 600; }
.import-step-title { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.import-step-desc { font-size: var(--text-xs); color: var(--color-text-tertiary); margin: 0 0 var(--space-2); }
.import-template-btn svg { width: 16px; height: 16px; }
.import-upload-area { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 20px; border: 2px dashed var(--color-border); border-radius: 12px; cursor: pointer; transition: all var(--transition-fast); color: var(--color-text-secondary); font-size: var(--text-sm); }
.import-upload-area:hover { border-color: var(--color-primary-300); background: var(--color-primary-50); color: var(--color-primary-500); }
.import-upload-area.upload-loading { cursor: not-allowed; opacity: 0.7; }
.import-upload-area svg { width: 24px; height: 24px; color: var(--color-text-tertiary); }
.import-upload-area:hover svg { color: var(--color-primary-500); }
.import-upload-hint { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.import-file-input { display: none; }
.import-spinner { width: 20px; height: 20px; border: 2px solid var(--color-border); border-top-color: var(--color-primary-500); border-radius: 50%; animation: import-spin 0.8s linear infinite; }
@keyframes import-spin { to { transform: rotate(360deg); } }
.import-result { padding: var(--space-3); background: var(--color-bg-page); border-radius: 8px; border: 1px solid var(--color-border); }
.import-result-header { display: flex; align-items: center; gap: var(--space-3); font-size: var(--text-sm); font-weight: 600; }
.result-success { color: var(--color-primary-600); }
.result-partial { color: var(--color-text-primary); }
.result-fail-count { color: var(--color-danger); font-weight: 500; }
.import-errors { margin-top: var(--space-3); max-height: 200px; overflow-y: auto; }
.import-error-item { font-size: var(--text-xs); color: var(--color-danger); padding: var(--space-1) 0; border-bottom: 1px solid var(--color-border-light); }
.import-error-item:last-child { border-bottom: none; }
@media (max-width: 1200px) { .stats-row { grid-template-columns: repeat(2, 1fr); } .data-table { display: block; overflow-x: auto; } }
@media (max-width: 768px) { .page-header { flex-direction: column; align-items: flex-start; gap: var(--space-4); } .stats-row { grid-template-columns: 1fr; } }
</style>
