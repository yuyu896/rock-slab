<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { getTransfers, getTransfer, approveTransfer, rejectTransfer, exportTransfers, purchaseAsset } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { formatMoney } from '@/utils/format'
import { ElMessage, ElMessageBox } from 'element-plus'
import PurchaseDetail from './purchases/PurchaseDetail.vue'
import PurchaseCreateForm from './purchases/PurchaseCreateForm.vue'
import PurchaseImportDialog from './purchases/PurchaseImportDialog.vue'

// 视图状态
const currentView = ref('list')
const showImportModal = ref(false)

// 筛选
const filters = ref({
  status: '',
  branch: '',
  keyword: ''
})

// 采购入库单列表
const purchaseOrders = ref<any[]>([])

// ===== 详情弹窗 =====
const showDetailModal = ref(false)
const detailOrder = ref<any>(null)
const detailLoading = ref(false)

// 状态选项
const statusOptions = [
  { value: '', label: '全部状态' },
  { value: '待审批', label: '待审批' },
  { value: '已通过', label: '已通过' },
  { value: '已入库', label: '已入库' },
  { value: '已驳回', label: '已驳回' }
]

// 分公司选项
const branchOptions = ref([{ value: '', label: '全部分公司' }])

// 状态样式
const getStatusStyle = (status: string) => {
  const styles = {
    '待审批': { bg: 'oklch(0.94 0.06 85)', color: 'oklch(0.55 0.14 85)' },
    '已通过': { bg: 'var(--color-primary-50)', color: 'var(--color-primary-600)' },
    '已入库': { bg: 'oklch(0.92 0.08 145)', color: 'var(--color-success)' },
    '已驳回': { bg: 'oklch(0.92 0.10 25)', color: 'var(--color-danger)' }
  }
  return styles[status as keyof typeof styles] || { bg: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }
}

async function submitPurchaseItems(order: any) {
  for (const item of order.items) {
    await purchaseAsset({
      调拨日期: order.purchaseDate,
      资产编号: item.code,
      资产名称: item.name,
      调拨数量: item.qty,
      toBranch: order.branch || undefined,
      调拨原因: order.supplier || '',
      备注: order.remark || '',
    })
  }
}

// 提交采购单
const submitOrder = async (order: any) => {
  try {
    await submitPurchaseItems(order)
    ElMessage.success('采购单提交成功')
    currentView.value = 'list'
    fetchPurchaseOrders()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 查看详情
const viewDetail = async (order: any) => {
  detailOrder.value = order
  showDetailModal.value = true
  detailLoading.value = true
  try {
    const { data } = await getTransfer(order.id)
    detailOrder.value = {
      ...order,
      branch: data.调出分公司 || data.调入分公司 || order.branch,
      supplier: data.备注 || order.supplier,
      status: data.审批状态 || order.status,
      submitter: data.创建人 || order.submitter,
      submitTime: data.调拨日期 || order.submitTime,
      totalCount: data.调拨数量 || order.totalCount,
    }
  } catch {
    // use cached order data
  } finally {
    detailLoading.value = false
  }
}

// 审批通过
const approveOrder = async (order: any) => {
  try {
    await ElMessageBox.confirm('确定通过此采购申请？', '审批确认', { type: 'info' })
    await approveTransfer(order.id, { approved: true })
    ElMessage.success('审批通过')
    fetchPurchaseOrders()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// 审批驳回
const rejectOrder = async (order: any) => {
  try {
    const { value: reason } = await ElMessageBox.prompt('请输入驳回原因', '驳回审批', {
      confirmButtonText: '确定驳回',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '请说明驳回原因...',
      inputValidator: (val) => (val && val.trim() ? true : '请输入驳回原因'),
    })
    await rejectTransfer(order.id, { reason })
    ElMessage.success('已驳回')
    fetchPurchaseOrders()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// 保存草稿
const saveDraft = async (order: any) => {
  try {
    await submitPurchaseItems(order)
    ElMessage.success('草稿保存成功')
    currentView.value = 'list'
    fetchPurchaseOrders()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 导入成功回调
const handleImportSuccess = () => {
  showImportModal.value = false
  fetchPurchaseOrders()
}

// 统计数据
const stats = computed(() => ({
  total: purchaseOrders.value.length,
  pending: purchaseOrders.value.filter(o => o.status === '待审批').length,
  approved: purchaseOrders.value.filter(o => o.status === '已通过' || o.status === '已入库').length,
  rejected: purchaseOrders.value.filter(o => o.status === '已驳回').length
}))

// 获取采购单列表
async function fetchPurchaseOrders() {
  try {
    const params: Record<string, string> = { type: 'purchase' }
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.branch) {
      const branch = branchOptions.value.find(b => b.value === filters.value.branch)
      if (branch) params.fromBranch = branch.label
    }
    const { data } = await getTransfers(params)
    let results = data.results
    // Client-side keyword filter — backend lacks a search filter for this endpoint,
    // so pagination count won't reflect filtered results.
    if (filters.value.keyword) {
      const kw = filters.value.keyword.toLowerCase()
      results = results.filter((t: any) =>
        (t.资产编号 || '').toLowerCase().includes(kw) ||
        (t.资产名称 || '').toLowerCase().includes(kw) ||
        (t.调拨原因 || '').toLowerCase().includes(kw) ||
        (t.备注 || '').toLowerCase().includes(kw)
      )
    }
    purchaseOrders.value = results.map((t: any) => ({
      id: t.id,
      orderNo: t.id,
      branch: t.toBranchName || t.fromBranchName || t.调出分公司 || t.调入分公司 || '',
      supplier: t.调拨原因 || '',
      totalCount: t.调拨数量 || 0,
      totalAmount: t.备注 || 0,
      status: t.审批状态,
      submitter: t.创建人,
      submitTime: t.调拨日期,
    }))
  } catch (error) {
    console.error('Failed to fetch purchase orders:', error)
  }
}

// 获取分公司选项
async function fetchBranches() {
  try {
    const { data } = await getBranches()
    branchOptions.value = [
      { value: '', label: '全部分公司' },
      ...data.map((b: any) => ({ value: b.id, label: b.name }))
    ]
  } catch (error) {
    console.error('Failed to fetch branches:', error)
  }
}

// 导出
async function handleExport() {
  try {
    const { data } = await exportTransfers({ type: 'purchase' })
    const blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `采购入库_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 筛选变化时重新请求
watch(filters, () => {
  fetchPurchaseOrders()
}, { deep: true })

// 初始化
onMounted(() => {
  fetchBranches()
  fetchPurchaseOrders()
})
</script>

<template>
  <div class="purchase-page">
    <!-- 列表视图 -->
    <template v-if="currentView === 'list'">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-info">
          <h1 class="page-title">采购入库</h1>
          <p class="page-desc">管理资产采购入库流程</p>
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
          <button class="btn-secondary" @click="showImportModal = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            模板导入
          </button>
          <button class="btn-primary" @click="currentView = 'create'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新建入库单
          </button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-num">{{ stats.total }}</span>
          <span class="stat-label">全部入库单</span>
        </div>
        <div class="stat-item pending">
          <span class="stat-num">{{ stats.pending }}</span>
          <span class="stat-label">待审批</span>
        </div>
        <div class="stat-item success">
          <span class="stat-num">{{ stats.approved }}</span>
          <span class="stat-label">已通过</span>
        </div>
        <div class="stat-item danger">
          <span class="stat-num">{{ stats.rejected }}</span>
          <span class="stat-label">已驳回</span>
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
              placeholder="搜索单号、供应商..."
              class="filter-input"
            />
          </div>
          <div class="filter-item">
            <select v-model="filters.branch" class="filter-select">
              <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="filter-item">
            <select v-model="filters.status" class="filter-select">
              <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- 数据表格 -->
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>入库单号</th>
              <th>分公司</th>
              <th>供应商</th>
              <th>物品数量</th>
              <th>入库金额</th>
              <th>状态</th>
              <th>提交人</th>
              <th>提交时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in purchaseOrders" :key="order.id">
              <td>
                <span class="order-no">{{ order.orderNo }}</span>
              </td>
              <td>{{ order.branch }}</td>
              <td>{{ order.supplier }}</td>
              <td>{{ order.totalCount }}件</td>
              <td class="amount">{{ formatMoney(order.totalAmount) }}</td>
              <td>
                <span
                  class="status-badge"
                  :style="getStatusStyle(order.status)"
                >
                  {{ order.status }}
                </span>
              </td>
              <td>{{ order.submitter }}</td>
              <td>{{ order.submitTime }}</td>
              <td>
                <div class="action-buttons">
                  <button class="action-btn" @click="viewDetail(order)">详情</button>
                  <button
                    v-if="order.status === '待审批'"
                    class="action-btn approve"
                    @click="approveOrder(order)"
                  >
                    通过
                  </button>
                  <button
                    v-if="order.status === '待审批'"
                    class="action-btn reject"
                    @click="rejectOrder(order)"
                  >
                    驳回
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 新建视图 -->
    <PurchaseCreateForm
      v-else-if="currentView === 'create'"
      :branch-options="branchOptions"
      @back="currentView = 'list'"
      @submit="submitOrder"
      @save-draft="saveDraft"
    />

    <!-- 导入弹窗 -->
    <PurchaseImportDialog
      :visible="showImportModal"
      @close="showImportModal = false"
      @success="handleImportSuccess"
    />

    <!-- 详情弹窗 -->
    <PurchaseDetail
      :visible="showDetailModal"
      :order="detailOrder"
      :loading="detailLoading"
      @close="showDetailModal = false"
      @approve="(order) => { approveOrder(order); showDetailModal = false }"
      @reject="(order) => { rejectOrder(order); showDetailModal = false }"
    />
  </div>
</template>

<style scoped>
.purchase-page {
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
}

.btn-secondary {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn-primary {
  background: var(--color-primary-500);
  border: 1px solid var(--color-primary-500);
  color: white;
}

.btn-secondary svg,
.btn-primary svg {
  width: 18px;
  height: 18px;
}

/* 统计 */
.stats-row {
  display: flex;
  gap: var(--space-8);
  margin-bottom: var(--space-5);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--color-border-light);
}

.stat-item {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.stat-num {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-item.pending .stat-num {
  color: oklch(0.55 0.14 85);
}

.stat-item.success .stat-num {
  color: var(--color-success);
}

.stat-item.danger .stat-num {
  color: var(--color-danger);
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 筛选 */
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

.filter-input,
.filter-select {
  height: 38px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
}

.filter-item.search .filter-input {
  width: 100%;
  padding-left: 38px;
}

.filter-select {
  min-width: 140px;
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

.order-no {
  font-family: var(--font-mono);
  color: var(--color-primary-600);
  font-weight: 500;
}

.amount {
  font-weight: 600;
  color: var(--color-text-primary);
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: 500;
}

@import '@/styles/action-buttons.css';

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-4);
  }
}
</style>
