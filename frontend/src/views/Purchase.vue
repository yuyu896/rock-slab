<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { createAsset, importAssets } from '@/api/assets'
import { getTransfers, getTransfer, approveTransfer, rejectTransfer, exportTransfers } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { formatMoney } from '@/utils/format'
import { ElMessage, ElMessageBox } from 'element-plus'

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

// 新建表单
const newOrder = ref({
  branch: '',
  supplier: '',
  items: [
    { code: '', name: '', spec: '', qty: 1, price: 0 }
  ],
  purchaseDate: '',
  isRent: false,
  remark: ''
})

// 导入文件
const importFile = ref<File | null>(null)

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

// 计算总金额
const totalAmount = computed(() => {
  return newOrder.value.items.reduce((sum, item) => sum + item.qty * item.price, 0)
})

// 添加明细行
const addItem = () => {
  newOrder.value.items.push({ code: '', name: '', spec: '', qty: 1, price: 0 })
}

// 删除明细行
const removeItem = (index: number) => {
  if (newOrder.value.items.length > 1) {
    newOrder.value.items.splice(index, 1)
  }
}

// 提交采购单
const submitOrder = async () => {
  try {
    for (const item of newOrder.value.items) {
      await createAsset({
        资产编号: item.code,
        资产名称: item.name,
        规格: item.spec,
        数量: item.qty,
        单价: item.price,
        购入金额: item.qty * item.price,
        分公司: newOrder.value.branch,
        供应商: newOrder.value.supplier,
        入库日期: newOrder.value.purchaseDate,
        是否租用: newOrder.value.isRent,
        备注: newOrder.value.remark,
      })
    }
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

// 下载模板
const downloadTemplate = () => {
  const link = document.createElement('a')
  link.href = '/xx分公司行政资产盘点系统-模版.xlsx'
  link.download = 'xx分公司行政资产盘点系统-模版.xlsx'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 选择导入文件
const onFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0) {
    importFile.value = files[0]
  }
}

// 确认导入
const confirmImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请先选择要导入的文件')
    return
  }
  try {
    const { data } = await importAssets(importFile.value)
    ElMessage.success(`导入成功：${data.imported}条`)
    showImportModal.value = false
    importFile.value = null
    fetchPurchaseOrders()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 保存草稿
const saveDraft = async () => {
  try {
    for (const item of newOrder.value.items) {
      await createAsset({
        资产编号: item.code,
        资产名称: item.name,
        规格: item.spec,
        数量: item.qty,
        单价: item.price,
        购入金额: item.qty * item.price,
        分公司: newOrder.value.branch,
        供应商: newOrder.value.supplier,
        入库日期: newOrder.value.purchaseDate,
        是否租用: newOrder.value.isRent,
        备注: newOrder.value.remark,
        当前状态: '在库',
      })
    }
    ElMessage.success('草稿保存成功')
    currentView.value = 'list'
    fetchPurchaseOrders()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 导入处理（保留兼容旧的 handleImport）
const handleImport = async (file: File) => {
  try {
    const { data } = await importAssets(file)
    ElMessage.success(`导入成功：${data.imported}条`)
    showImportModal.value = false
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
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
    const { data } = await getTransfers({ type: 'purchase' })
    purchaseOrders.value = data.results.map((t: any) => ({
      id: t.id,
      orderNo: t.id,
      branch: t.调出分公司 || t.调入分公司 || '',
      supplier: t.备注 || '',
      totalCount: t.资产数量 || 0,
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
      ...data.map((b: any) => ({ value: b.name, label: b.name }))
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
                    class="action-btn primary"
                    @click="approveOrder(order)"
                  >
                    审批
                  </button>
                  <button
                    v-if="order.status === '待审批'"
                    class="action-btn danger"
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
    <template v-else-if="currentView === 'create'">
      <div class="create-view">
        <div class="create-header">
          <button class="back-btn" @click="currentView = 'list'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            返回列表
          </button>
          <h2 class="create-title">新建采购入库单</h2>
        </div>

        <div class="create-content">
          <!-- 基本信息 -->
          <div class="form-section">
            <h3 class="section-title">基本信息</h3>
            <div class="form-grid">
              <div class="form-item">
                <label class="form-label">入库分公司 <span class="required">*</span></label>
                <select v-model="newOrder.branch" class="form-select">
                  <option value="">请选择分公司</option>
                  <option v-for="opt in branchOptions.slice(1)" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
              <div class="form-item">
                <label class="form-label">供应商 <span class="required">*</span></label>
                <input v-model="newOrder.supplier" type="text" class="form-input" placeholder="请输入供应商名称" />
              </div>
              <div class="form-item">
                <label class="form-label">采购日期 <span class="required">*</span></label>
                <input v-model="newOrder.purchaseDate" type="date" class="form-input" />
              </div>
              <div class="form-item checkbox-item">
                <label class="checkbox-label">
                  <input v-model="newOrder.isRent" type="checkbox" />
                  <span>是否租用资产</span>
                </label>
              </div>
            </div>
          </div>

          <!-- 物品明细 -->
          <div class="form-section">
            <div class="section-header">
              <h3 class="section-title">物品明细</h3>
              <button class="add-row-btn" @click="addItem">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                添加物品
              </button>
            </div>

            <div class="items-table">
              <div class="items-header">
                <span class="col-code">资产编号</span>
                <span class="col-name">资产名称</span>
                <span class="col-spec">规格型号</span>
                <span class="col-qty">数量</span>
                <span class="col-price">单价</span>
                <span class="col-amount">金额</span>
                <span class="col-action"></span>
              </div>
              <div
                v-for="(item, index) in newOrder.items"
                :key="index"
                class="items-row"
              >
                <input v-model="item.code" type="text" class="item-input code" placeholder="资产编号" />
                <input v-model="item.name" type="text" class="item-input name" placeholder="资产名称" />
                <input v-model="item.spec" type="text" class="item-input spec" placeholder="规格型号" />
                <input v-model="item.qty" type="number" class="item-input qty" min="1" />
                <input v-model="item.price" type="number" class="item-input price" min="0" placeholder="0.00" />
                <span class="item-amount">{{ formatMoney(item.qty * item.price) }}</span>
                <button
                  class="remove-btn"
                  :disabled="newOrder.items.length === 1"
                  @click="removeItem(index)"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="items-summary">
              <div class="summary-row">
                <span class="summary-label">合计数量：</span>
                <span class="summary-value">{{ newOrder.items.reduce((sum, item) => sum + item.qty, 0) }} 件</span>
              </div>
              <div class="summary-row highlight">
                <span class="summary-label">合计金额：</span>
                <span class="summary-value">{{ formatMoney(totalAmount) }}</span>
              </div>
            </div>
          </div>

          <!-- 备注 -->
          <div class="form-section">
            <h3 class="section-title">备注信息</h3>
            <textarea
              v-model="newOrder.remark"
              class="form-textarea"
              placeholder="请输入备注信息..."
              rows="3"
            />
          </div>

          <!-- 操作按钮 -->
          <div class="form-actions">
            <button class="btn-cancel" @click="currentView = 'list'">取消</button>
            <button class="btn-draft" @click="saveDraft">保存草稿</button>
            <button class="btn-submit" @click="submitOrder">提交审批</button>
          </div>
        </div>
      </div>
    </template>

    <!-- 导入弹窗 -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="showImportModal = false">
      <div class="modal-content import-modal">
        <div class="modal-header">
          <h3 class="modal-title">模板导入</h3>
          <button class="modal-close" @click="showImportModal = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="download-section">
            <span class="download-text">请先下载导入模板</span>
            <button class="download-btn" @click="downloadTemplate">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              下载模板
            </button>
          </div>
          <div class="upload-area">
            <div class="upload-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <p class="upload-text">将文件拖拽到此处，或 <span class="upload-link">点击上传</span></p>
            <p class="upload-hint">支持 .xlsx, .xls 格式，单次最多 1000 条</p>
            <input type="file" accept=".xlsx,.xls" class="upload-input" @change="onFileChange" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="showImportModal = false">取消</button>
          <button class="btn-confirm" @click="confirmImport">确认导入</button>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal-content detail-modal">
        <div class="modal-header">
          <h3 class="modal-title">采购单详情</h3>
          <button class="modal-close" @click="showDetailModal = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="modal-body" v-loading="detailLoading">
          <div v-if="detailOrder" class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">入库单号</span>
              <span class="detail-value order-no">{{ detailOrder.orderNo }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">分公司</span>
              <span class="detail-value">{{ detailOrder.branch }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">供应商</span>
              <span class="detail-value">{{ detailOrder.supplier }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">物品数量</span>
              <span class="detail-value">{{ detailOrder.totalCount }}件</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">入库金额</span>
              <span class="detail-value amount">{{ formatMoney(detailOrder.totalAmount) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">状态</span>
              <span class="status-badge" :style="getStatusStyle(detailOrder.status)">{{ detailOrder.status }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">提交人</span>
              <span class="detail-value">{{ detailOrder.submitter }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">提交时间</span>
              <span class="detail-value">{{ detailOrder.submitTime }}</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="detailOrder?.status === '待审批'" class="btn-reject" @click="rejectOrder(detailOrder); showDetailModal = false">驳回</button>
          <button v-if="detailOrder?.status === '待审批'" class="btn-confirm" @click="approveOrder(detailOrder); showDetailModal = false">通过</button>
          <button v-else class="btn-cancel" @click="showDetailModal = false">关闭</button>
        </div>
      </div>
    </div>
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

.action-buttons {
  display: flex;
  gap: var(--space-2);
}

.action-btn {
  padding: var(--space-1) var(--space-3);
  background: var(--color-bg-elevated);
  border: none;
  border-radius: 6px;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.action-btn.primary {
  background: var(--color-primary-500);
  color: white;
}

.action-btn.danger {
  background: oklch(0.92 0.10 25);
  color: var(--color-danger);
}

/* 新建视图 */
.create-view {
  max-width: 1000px;
}

.create-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
}

.back-btn svg {
  width: 18px;
  height: 18px;
}

.create-title {
  font-size: var(--text-xl);
  font-weight: 600;
  margin: 0;
}

.create-content {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  padding: var(--space-6);
}

.form-section {
  margin-bottom: var(--space-6);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.section-title {
  font-size: var(--text-base);
  font-weight: 600;
  margin: 0 0 var(--space-4) 0;
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border-light);
}

.section-header .section-title {
  margin: 0;
  border: none;
  padding: 0;
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

.form-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.required {
  color: var(--color-danger);
}

.form-input,
.form-select {
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
}

.checkbox-item {
  flex-direction: row;
  align-items: center;
  padding-top: var(--space-6);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

.add-row-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-primary-50);
  border: 1px solid var(--color-primary-200);
  border-radius: 8px;
  padding: var(--space-2) var(--space-4);
  color: var(--color-primary-600);
  font-size: var(--text-sm);
  cursor: pointer;
}

.add-row-btn svg {
  width: 16px;
  height: 16px;
}

/* 物品明细表格 */
.items-table {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.items-header {
  display: grid;
  grid-template-columns: 120px 1fr 120px 80px 100px 100px 40px;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-elevated);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
}

.items-row {
  display: grid;
  grid-template-columns: 120px 1fr 120px 80px 100px 100px 40px;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--color-border-light);
  align-items: center;
}

.item-input {
  height: 36px;
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
}

.item-input:focus {
  outline: none;
  border-color: var(--color-primary-400);
}

.item-amount {
  font-weight: 500;
  color: var(--color-text-primary);
}

.remove-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--color-text-tertiary);
  cursor: pointer;
}

.remove-btn:hover:not(:disabled) {
  background: oklch(0.92 0.10 25);
  color: var(--color-danger);
}

.remove-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.remove-btn svg {
  width: 16px;
  height: 16px;
}

/* 合计 */
.items-summary {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-8);
  padding: var(--space-4);
  background: var(--color-bg-elevated);
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-3);
  border-radius: 8px;
}

.summary-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.summary-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.summary-value {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.summary-row.highlight .summary-value {
  color: var(--color-primary-600);
}

/* 文本域 */
.form-textarea {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
  resize: vertical;
}

/* 操作按钮 */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-6);
}

.btn-cancel,
.btn-draft,
.btn-submit {
  height: 40px;
  padding: 0 var(--space-6);
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

.btn-draft {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn-submit {
  background: var(--color-primary-500);
  border: none;
  color: white;
}

/* 导入弹窗 */
.import-modal {
  width: 500px;
}

.download-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  background: var(--color-bg-page);
  border-radius: 8px;
  margin-bottom: var(--space-4);
}

.download-text {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.download-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-primary-50);
  border: 1px solid var(--color-primary-200);
  border-radius: 6px;
  padding: var(--space-2) var(--space-3);
  color: var(--color-primary-600);
  font-size: var(--text-sm);
  cursor: pointer;
}

.download-btn svg {
  width: 16px;
  height: 16px;
}

.upload-area {
  border: 2px dashed var(--color-border);
  border-radius: 12px;
  padding: var(--space-8);
  text-align: center;
  position: relative;
}

.upload-input {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.upload-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--space-4);
  background: var(--color-primary-50);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary-500);
}

.upload-icon svg {
  width: 24px;
  height: 24px;
}

.upload-text {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.upload-link {
  color: var(--color-primary-500);
  cursor: pointer;
}

.upload-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
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

.modal-close svg {
  width: 18px;
  height: 18px;
}

.modal-body {
  padding: var(--space-5);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-5);
  border-top: 1px solid var(--color-border);
}

.btn-cancel,
.btn-confirm {
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

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-4);
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .items-header,
  .items-row {
    grid-template-columns: 1fr;
  }
}

/* 详情弹窗 */
.detail-modal {
  width: 560px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
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

.btn-reject {
  height: 40px;
  padding: 0 var(--space-5);
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  background: oklch(0.92 0.10 25);
  border: none;
  color: var(--color-danger);
}
</style>
