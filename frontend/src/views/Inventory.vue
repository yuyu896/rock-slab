<script setup lang="ts">
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useInventoryStore } from '@/store/inventory'
import {
  getInventoryTasks,
  createInventoryTask,
  startInventory as startInventoryApi,
  cancelInventory,
  approveInventory,
  rejectInventory,
  recountInventory,
  getInventoryReport,
  getInventoryProgress,
  submitInventory,
  downloadInventoryTemplate,
  importInventoryResult,
} from '@/api/inventories'
import { getBranches } from '@/api/branches'
import { getCategories } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { INVENTORY_STATUS_OPTIONS, INVENTORY_STATUS_COLORS, INVENTORY_STATUS_MAP, INVENTORY_RESULT_MAP, MISSED_RULE_LABELS, REPEAT_RULE_LABELS } from '@/constants'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { InventoryTask, MissedRuleType, RepeatRuleType } from '@/types'

const inventoryStore = useInventoryStore()

const router = useRouter()

// 当前视图状态
const currentView = ref<'list' | 'detail' | 'scanning'>('list')

// 加载状态
const loading = ref(false)

// 盘点任务列表
const inventoryTasks = ref<any[]>([])

// 分页
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 当前选中的任务
const selectedTask = ref<any>(null)

// 全局状态统计
const statusStats = ref({ pending: 0, inProgress: 0, pendingReview: 0 })

// 获取全局状态统计（无分页，按状态分别请求）
async function fetchStatusStats() {
  try {
    const [pendingRes, inProgressRes, pendingReviewRes] = await Promise.all([
      getInventoryTasks({ status: 'pending', pageSize: 1 }),
      getInventoryTasks({ status: 'in_progress', pageSize: 1 }),
      getInventoryTasks({ status: 'pending_review', pageSize: 1 }),
    ])
    statusStats.value = {
      pending: pendingRes.data.count,
      inProgress: inProgressRes.data.count,
      pendingReview: pendingReviewRes.data.count,
    }
  } catch { /* ignore */ }
}

// 筛选条件
const filters = ref({
  status: '',
  branch: '',
  keyword: ''
})

// 状态选项
const statusOptions = INVENTORY_STATUS_OPTIONS

// 分公司选项
const branchOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部分公司' }])

// 获取状态样式
const getStatusStyle = (status: string) => {
  const colorSet = INVENTORY_STATUS_COLORS[status as keyof typeof INVENTORY_STATUS_COLORS] || { bg: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }
  return { ...colorSet, border: colorSet.bg }
}

// 获取状态标签
const getStatusLabel = (status: string) => {
  return INVENTORY_STATUS_MAP[status as keyof typeof INVENTORY_STATUS_MAP] || status
}

// 获取分公司名称
const getBranchName = (branchId: string | null | undefined) => {
  if (!branchId) return '全部分公司'
  const opt = branchOptions.value.find(b => b.value === branchId)
  return opt?.label || branchId
}

// 格式化日期
const formatDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return '-'
  return dateStr.slice(0, 10)
}

// 获取规则标签
const getMissedRuleLabel = (rule: string) => MISSED_RULE_LABELS[rule as MissedRuleType] || '-'
const getRepeatRuleLabel = (rule: string) => REPEAT_RULE_LABELS[rule as RepeatRuleType] || '-'

// 从扫码视图提交审批
const submitFromScan = async (task: any) => {
  try {
    await ElMessageBox.confirm('确定要提交审批吗？提交后将无法继续盘点。', '提交确认', {
      confirmButtonText: '提交', cancelButtonText: '取消', type: 'warning',
    })
    await submitInventory(task.id)
    ElMessage.success('已提交审核')
    backToList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// 获取任务列表
async function fetchTasks() {
  loading.value = true
  try {
    const { data } = await getInventoryTasks({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      status: filters.value.status || undefined,
      branchId: filters.value.branch || undefined,
    })
    inventoryTasks.value = data.results
    pagination.value.total = data.count
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

// 获取分公司选项
async function fetchBranches() {
  try {
    const { data } = await getBranches()
    branchOptions.value = [
      { value: '', label: '全部分公司' },
      ...data.map(b => ({ value: b.id, label: b.name }))
    ]
  } catch (error) {
    console.error('Failed to fetch branches:', error)
  }
}

// 获取资产类目选项
async function fetchCategories() {
  try {
    const { data } = await getCategories({ pageSize: 500 })
    const categories = (data.results || []) as any[]
    // List all individual categories with ID as value
    // Group display as "一级类目 - 二级分类 - 资产名称"
    categoryOptions.value = categories.map(c => ({
      value: c.id,
      label: `${c['资产类目']} - ${c['物品分类']}${c['资产名称'] ? ' - ' + c['资产名称'] : ''}`,
    }))
  } catch (error) {
    console.error('Failed to fetch categories:', error)
  }
}

// 查看任务详情
const viewTask = async (task: any) => {
  // Enrich task data with progress and resolved names
  const enriched = { ...task }
  try {
    const { data: progress } = await getInventoryProgress(task.id)
    enriched.totalItems = progress.totalItems
    enriched.checkedItems = progress.checkedItems
    enriched.surplusCount = progress.surplusCount
    enriched.missingCount = progress.missingCount
    enriched.uncheckedCount = progress.uncheckedCount
    enriched.progress = progress.totalItems ? Math.round(progress.checkedItems / progress.totalItems * 100) : 0
  } catch { /* ignore */ }
  // Resolve branch name
  const branchOpt = branchOptions.value.find(b => b.value === task.branch)
  enriched.branchName = branchOpt?.label || task.branch || '全部分公司'
  // Resolve creator name from created_by (may be an ID or nested)
  enriched.creatorName = task.created_by_name || task.createdBy || '-'
  selectedTask.value = enriched
  currentView.value = 'detail'
}

// 开始盘点
const startInventory = async (task: any) => {
  try {
    await startInventoryApi(task.id)
    ElMessage.success('盘点已开始')
    router.push(`/mobile/scan/${task.id}`)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

// 返回列表
const backToList = () => {
  currentView.value = 'list'
  selectedTask.value = null
}

// ========== 7.1 创建盘点任务 ==========
const creatingTask = ref(false)
const showCreateTaskModal = ref(false)
const newTaskForm = reactive({
  name: '',
  branchId: '',
  categoryId: '',
  missedRule: 'keep' as MissedRuleType,
  repeatRule: 'last' as RepeatRuleType,
})

const categoryOptions = ref<{ value: string; label: string }[]>([])

const missedRuleOptions = Object.entries(MISSED_RULE_LABELS).map(([value, label]) => ({
  value,
  label,
}))

const repeatRuleOptions = Object.entries(REPEAT_RULE_LABELS).map(([value, label]) => ({
  value,
  label,
}))

const openCreateTaskModal = () => {
  newTaskForm.name = ''
  newTaskForm.branchId = ''
  newTaskForm.categoryId = ''
  newTaskForm.missedRule = 'keep'
  newTaskForm.repeatRule = 'last'
  showCreateTaskModal.value = true
}

const submitCreateTask = async () => {
  if (!newTaskForm.name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  creatingTask.value = true
  try {
    await createInventoryTask({
      name: newTaskForm.name,
      branch: newTaskForm.branchId || undefined,
      category: newTaskForm.categoryId || undefined,
      missed_rule: newTaskForm.missedRule,
      repeat_rule: newTaskForm.repeatRule,
    } as any)
    ElMessage.success('盘点任务创建成功')
    showCreateTaskModal.value = false
    await fetchTasks()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    creatingTask.value = false
  }
}

// ========== 7.2 删除盘点任务 ==========
const deleteTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除盘点任务「${task.name}」吗？此操作不可撤销。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await inventoryStore.deleteTask(task.id)
    ElMessage.success('任务已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// helper for template
const getResultLabel = (result: string) => INVENTORY_RESULT_MAP[result as keyof typeof INVENTORY_RESULT_MAP] ?? result

// ========== 7.3 作废盘点任务 ==========
const cancelTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要作废盘点任务「${task.name}」吗？此操作不可撤销。`,
      '作废确认',
      { confirmButtonText: '作废', cancelButtonText: '取消', type: 'warning' }
    )
    await cancelInventory(task.id)
    ElMessage.success('任务已作废')
    await fetchTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// ========== 7.4 审批通过 ==========
const approveTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要通过「${task.name}」的盘点审批吗？`,
      '审批确认',
      { confirmButtonText: '通过', cancelButtonText: '取消', type: 'success' }
    )
    await approveInventory(task.id)
    ElMessage.success('审批已通过')
    await fetchTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// ========== 7.5 驳回 ==========
const rejectTask = async (task: any) => {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      `请输入驳回「${task.name}」的原因：`,
      '驳回审批',
      {
        confirmButtonText: '驳回',
        cancelButtonText: '取消',
        type: 'warning',
        inputValidator: (val: string | null) => (val && val.trim() ? true : '请输入驳回原因'),
      }
    )
    await rejectInventory(task.id, { reason })
    ElMessage.success('已驳回')
    await fetchTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// ========== 7.6 重新盘点 ==========
const recountTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      '仅重盘异常项（盘盈/盘亏/未盘点），已正常的项目保留盘点结果。',
      '重盘异常项',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' },
    )
    await recountInventory(task.id, { reset_scope: 'abnormal_only' })
    ElMessage.success('已开始重新盘点')
    router.push(`/mobile/scan/${task.id}`)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

const recountAllTask = async (task: any) => {
  try {
    await ElMessageBox.confirm(
      '确定要重盘所有物品吗？已正常的项目也会被重置。',
      '全部重盘',
      { confirmButtonText: '全部重盘', cancelButtonText: '取消', type: 'warning' },
    )
    await recountInventory(task.id, { reset_scope: 'all' })
    ElMessage.success('已开始重新盘点')
    router.push(`/mobile/scan/${task.id}`)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

// ========== 7.7 查看报告 ==========
const reportVisible = ref(false)
const reportLoading = ref(false)
const reportData = ref<any>(null)

const viewReport = async (task: any) => {
  reportVisible.value = true
  reportLoading.value = true
  try {
    const { data } = await getInventoryReport(task.id)
    reportData.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    reportLoading.value = false
  }
}

// ========== 7.8 下载模板 ==========
const downloadingTemplate = ref(false)
const downloadTemplateAction = async (task: any) => {
  downloadingTemplate.value = true
  try {
    const { data } = await downloadInventoryTemplate(task.id)
    const url = window.URL.createObjectURL(new Blob([data as any]))
    const link = document.createElement('a')
    link.href = url
    link.download = `盘点表_${task.name}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    downloadingTemplate.value = false
  }
}

// ========== 7.9 导入盘点结果 ==========
const importFileInput = ref<HTMLInputElement | null>(null)
const importingTaskId = ref<string | null>(null)

const triggerImport = (task: any) => {
  importingTaskId.value = task.id
  // Reset and trigger file input
  if (importFileInput.value) {
    importFileInput.value.value = ''
    importFileInput.value.click()
  }
}

const handleImportFile = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !importingTaskId.value) return

  try {
    const { data } = await importInventoryResult(importingTaskId.value, file)
    const result = data as any
    if (result.errors?.length > 0) {
      ElMessage.warning(`导入完成：${result.imported} 条成功，${result.errors.length} 条失败`)
      console.warn('导入错误:', result.errors)
    } else {
      ElMessage.success(`导入成功：${result.imported} 条`)
    }
    await fetchTasks()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    importingTaskId.value = null
  }
}

// 筛选后的任务列表
const filteredTasks = computed(() => {
  return inventoryTasks.value.filter(task => {
    if (filters.value.keyword && !task.name.includes(filters.value.keyword)) return false
    return true
  })
})

// 统计数据
const stats = computed(() => ({
  total: pagination.value.total,
  pending: statusStats.value.pending,
  inProgress: statusStats.value.inProgress,
  pendingReview: statusStats.value.pendingReview,
}))

// 监听筛选条件变化
watch(filters, () => {
  pagination.value.page = 1
  fetchTasks()
}, { deep: true })

// 初始化
onMounted(() => {
  fetchTasks()
  fetchBranches()
  fetchCategories()
  fetchStatusStats()
})
</script>

<template>
  <div class="inventory-page">
    <!-- 任务列表视图 -->
    <template v-if="currentView === 'list'">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-info">
          <h1 class="page-title">资产盘点</h1>
          <p class="page-desc">管理盘点任务，追踪盘点进度</p>
        </div>
        <button class="btn-primary" @click="openCreateTaskModal">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          创建盘点任务
        </button>
      </div>

      <!-- 快速统计 -->
      <div class="quick-stats">
        <div class="stat-item">
          <span class="stat-num">{{ stats.total }}</span>
          <span class="stat-label">全部任务</span>
        </div>
        <div class="stat-item">
          <span class="stat-num pending">{{ stats.pending }}</span>
          <span class="stat-label">待盘点</span>
        </div>
        <div class="stat-item">
          <span class="stat-num in-progress">{{ stats.inProgress }}</span>
          <span class="stat-label">盘点中</span>
        </div>
        <div class="stat-item">
          <span class="stat-num review">{{ stats.pendingReview }}</span>
          <span class="stat-label">待审核</span>
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
              placeholder="搜索任务名称..."
              class="filter-input"
              aria-label="搜索盘点任务"
            />
          </div>

          <div class="filter-item">
            <select
              v-model="filters.status"
              class="filter-select"
              aria-label="筛选任务状态"
            >
              <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- 隐藏的文件导入 input -->
      <input
        ref="importFileInput"
        type="file"
        accept=".xlsx,.xls"
        style="display: none"
        @change="handleImportFile"
      />

      <!-- 任务列表表格 -->
      <div class="task-table-wrapper">
        <table class="task-table">
          <thead>
            <tr>
              <th>任务名称</th>
              <th>盘点范围</th>
              <th>状态</th>
              <th>漏盘规则</th>
              <th>重复规则</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="table-empty">加载中...</td>
            </tr>
            <tr v-else-if="filteredTasks.length === 0">
              <td colspan="7" class="table-empty">暂无盘点任务</td>
            </tr>
            <tr v-for="task in filteredTasks" :key="task.id" :class="[task.status]">
              <td class="cell-name">{{ task.name }}</td>
              <td>{{ getBranchName(task.branch) }}</td>
              <td>
                <span class="task-status" :style="getStatusStyle(task.status)">
                  {{ getStatusLabel(task.status) }}
                </span>
              </td>
              <td>{{ getMissedRuleLabel(task.missedRule) }}</td>
              <td>{{ getRepeatRuleLabel(task.repeatRule) }}</td>
              <td>{{ formatDate(task.createdAt) }}</td>
              <td class="cell-actions">
                <template v-if="task.status === 'pending'">
                  <button class="row-btn danger" title="删除" @click="deleteTask(task)">删除</button>
                  <button class="row-btn secondary" @click="cancelTask(task)">作废</button>
                  <button class="row-btn primary" @click="startInventory(task)">开始盘点</button>
                </template>
                <template v-else-if="task.status === 'in_progress'">
                  <button class="row-btn secondary" @click="viewTask(task)">查看进度</button>
                  <button class="row-btn accent" @click="downloadTemplateAction(task)" :disabled="downloadingTemplate">下载模板</button>
                  <button class="row-btn accent" @click="triggerImport(task)">导入盘点表</button>
                  <button class="row-btn secondary" @click="cancelTask(task)">作废</button>
                  <button class="row-btn primary" @click="submitFromScan(task)">提交审核</button>
                </template>
                <template v-else-if="task.status === 'pending_review'">
                  <button class="row-btn secondary" @click="viewTask(task)">查看详情</button>
                  <button class="row-btn danger" @click="rejectTask(task)">驳回</button>
                  <button class="row-btn primary" @click="approveTask(task)">审批通过</button>
                </template>
                <template v-else-if="task.status === 'rejected'">
                  <button class="row-btn secondary" @click="viewTask(task)">查看原因</button>
                  <button class="row-btn warning" @click="recountTask(task)">重盘异常项</button>
                  <button class="row-btn warning" @click="recountAllTask(task)">全部重盘</button>
                </template>
                <template v-else-if="task.status === 'completed'">
                  <button class="row-btn secondary" @click="viewReport(task)">查看报告</button>
                </template>
                <template v-else-if="task.status === 'cancelled'">
                  <span class="row-btn disabled">已作废</span>
                </template>
                <template v-else>
                  <button class="row-btn secondary" @click="viewTask(task)">查看详情</button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 任务详情视图 -->
    <template v-else-if="currentView === 'detail' && selectedTask">
      <div class="detail-view">
        <div class="detail-header">
          <button class="back-btn" @click="backToList">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            返回列表
          </button>
          <div class="header-actions">
            <button class="btn-secondary">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              导出报告
            </button>
            <button class="btn-primary">继续盘点</button>
          </div>
        </div>

        <div class="detail-content">
          <h2 class="detail-title">{{ selectedTask.name }}</h2>

          <div class="detail-grid">
            <!-- 基本信息 -->
            <div class="info-card">
              <h4 class="info-card-title">基本信息</h4>
              <div class="info-list">
                <div class="info-item">
                  <span class="info-label">盘点范围</span>
                  <span class="info-value">{{ selectedTask.branchName || '全部分公司' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">创建时间</span>
                  <span class="info-value">{{ selectedTask.createdAt?.slice(0, 10) || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">开始时间</span>
                  <span class="info-value">{{ selectedTask.startedAt?.slice(0, 10) || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">创建人</span>
                  <span class="info-value">{{ selectedTask.creatorName }}</span>
                </div>
              </div>
            </div>

            <!-- 盘点统计 -->
            <div class="info-card stats-card">
              <h4 class="info-card-title">盘点统计</h4>
              <div class="stats-grid">
                <div class="stat-box">
                  <span class="stat-number">{{ selectedTask.totalItems }}</span>
                  <span class="stat-text">应盘数量</span>
                </div>
                <div class="stat-box success">
                  <span class="stat-number">{{ selectedTask.checkedItems }}</span>
                  <span class="stat-text">已盘点</span>
                </div>
                <div class="stat-box warning">
                  <span class="stat-number">{{ selectedTask.surplusCount }}</span>
                  <span class="stat-text">盘盈</span>
                </div>
                <div class="stat-box danger">
                  <span class="stat-number">{{ selectedTask.missingCount }}</span>
                  <span class="stat-text">盘亏</span>
                </div>
              </div>
              <div class="progress-info">
                <div class="progress-bar-lg">
                  <div
                    class="progress-fill-lg"
                    :style="{ width: selectedTask.progress + '%' }"
                  />
                </div>
                <span class="progress-text">完成度 {{ selectedTask.progress }}%</span>
              </div>
            </div>
          </div>

          <!-- 盘点规则 -->
          <div class="checkers-card">
            <h4 class="info-card-title">盘点规则</h4>
            <div class="info-list">
              <div class="info-item">
                <span class="info-label">漏盘规则</span>
                <span class="info-value">{{ getMissedRuleLabel(selectedTask.missedRule) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">重复盘点规则</span>
                <span class="info-value">{{ getRepeatRuleLabel(selectedTask.repeatRule) }}</span>
              </div>
              <div v-if="selectedTask.rejectReason" class="info-item">
                <span class="info-label">驳回原因</span>
                <span class="info-value" style="color: var(--color-danger)">{{ selectedTask.rejectReason }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 扫码盘点视图 -->
    <template v-else-if="currentView === 'scanning' && selectedTask">
      <div class="scanning-view">
        <div class="scanning-header">
          <button class="back-btn" @click="backToList">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
            返回列表
          </button>
          <div class="scanning-title">{{ selectedTask.name }}</div>
          <div class="scanning-progress">
            <span class="progress-num">{{ selectedTask.checkedItems }}</span>
            <span class="progress-total">/{{ selectedTask.totalItems }}</span>
          </div>
        </div>

        <div class="scanning-content">
          <!-- 扫码区域 -->
          <div class="scan-area">
            <div class="scan-input-wrapper">
              <input
                type="text"
                placeholder="扫描或输入资产编号..."
                class="scan-input"
                autofocus
              />
              <button class="scan-btn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
                  <line x1="7" y1="12" x2="17" y2="12"/>
                </svg>
                扫码
              </button>
            </div>

            <!-- 最近盘点记录 -->
            <div class="recent-checks">
              <h4 class="recent-title">最近盘点</h4>
              <div class="check-list">
                <div class="check-item success">
                  <div class="check-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  </div>
                  <div class="check-info">
                    <span class="check-code">A-a00001</span>
                    <span class="check-name">Herman Miller办公椅</span>
                  </div>
                  <span class="check-time">刚刚</span>
                </div>
                <div class="check-item success">
                  <div class="check-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  </div>
                  <div class="check-info">
                    <span class="check-code">A-b00015</span>
                    <span class="check-name">MacBook Pro 14寸</span>
                  </div>
                  <span class="check-time">2分钟前</span>
                </div>
                <div class="check-item warning">
                  <div class="check-icon warning">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                      <line x1="12" y1="9" x2="12" y2="13"/>
                      <line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                  </div>
                  <div class="check-info">
                    <span class="check-code">B-a00008</span>
                    <span class="check-name">A4打印纸</span>
                    <span class="check-alert">盘亏：账面100，实际85</span>
                  </div>
                  <span class="check-time">5分钟前</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧信息面板 -->
          <div class="info-panel">
            <div class="panel-card">
              <h4 class="panel-title">盘点进度</h4>
              <div class="progress-ring">
                <svg viewBox="0 0 120 120">
                  <circle
                    cx="60"
                    cy="60"
                    r="54"
                    fill="none"
                    stroke="var(--color-bg-elevated)"
                    stroke-width="8"
                  />
                  <circle
                    cx="60"
                    cy="60"
                    r="54"
                    fill="none"
                    stroke="var(--color-primary-500)"
                    stroke-width="8"
                    stroke-linecap="round"
                    :stroke-dasharray="339.292"
                    :stroke-dashoffset="339.292 * (1 - selectedTask.progress / 100)"
                    transform="rotate(-90 60 60)"
                  />
                </svg>
                <div class="progress-center">
                  <span class="progress-percent">{{ selectedTask.progress }}</span>
                  <span class="progress-unit">%</span>
                </div>
              </div>
              <div class="progress-stats">
                <div class="p-stat">
                  <span class="p-value">{{ selectedTask.checkedItems }}</span>
                  <span class="p-label">已盘点</span>
                </div>
                <div class="p-stat">
                  <span class="p-value">{{ selectedTask.uncheckedCount }}</span>
                  <span class="p-label">未盘点</span>
                </div>
              </div>
            </div>

            <div class="panel-card">
              <h4 class="panel-title">异常统计</h4>
              <div class="abnormal-stats">
                <div class="abnormal-item surplus">
                  <span class="abnormal-count">{{ selectedTask.surplusCount }}</span>
                  <span class="abnormal-label">盘盈</span>
                </div>
                <div class="abnormal-item missing">
                  <span class="abnormal-count">{{ selectedTask.missingCount }}</span>
                  <span class="abnormal-label">盘亏</span>
                </div>
              </div>
            </div>

            <div class="panel-actions">
              <button class="panel-btn secondary" @click="backToList">
                暂停盘点
              </button>
              <button class="panel-btn primary" @click="submitFromScan(selectedTask)">
                提交审批
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 7.1 创建盘点任务弹窗 -->
    <div v-if="showCreateTaskModal" class="modal-overlay" @click.self="showCreateTaskModal = false">
      <div class="modal-dialog">
        <div class="modal-header">
          <h3 class="modal-title">创建盘点任务</h3>
          <button class="modal-close" @click="showCreateTaskModal = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">任务名称 <span class="required">*</span></label>
            <input v-model="newTaskForm.name" type="text" class="form-input" placeholder="请输入任务名称" />
          </div>
          <div class="form-group">
            <label class="form-label">分公司</label>
            <select v-model="newTaskForm.branchId" class="form-input">
              <option value="">请选择分公司</option>
              <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">资产类目</label>
            <select v-model="newTaskForm.categoryId" class="form-input">
              <option value="">请选择类目</option>
              <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">漏盘规则</label>
            <select v-model="newTaskForm.missedRule" class="form-input">
              <option v-for="opt in missedRuleOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">重复盘点规则</label>
            <select v-model="newTaskForm.repeatRule" class="form-input">
              <option v-for="opt in repeatRuleOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateTaskModal = false">取消</button>
          <button class="btn-primary" :disabled="creatingTask" @click="submitCreateTask">
            {{ creatingTask ? '创建中...' : '创建任务' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 7.7 查看报告弹窗 -->
    <div v-if="reportVisible" class="modal-overlay" @click.self="reportVisible = false">
      <div class="modal-dialog modal-lg">
        <div class="modal-header">
          <h3 class="modal-title">盘点报告</h3>
          <button class="modal-close" @click="reportVisible = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div v-if="reportLoading" class="report-loading">加载中...</div>
          <div v-else-if="reportData" class="report-content">
            <!-- 报告统计 -->
            <div class="report-stats">
              <div class="report-stat-item">
                <span class="report-stat-value">{{ reportData.progress?.totalItems ?? 0 }}</span>
                <span class="report-stat-label">应盘数量</span>
              </div>
              <div class="report-stat-item">
                <span class="report-stat-value success">{{ reportData.progress?.checkedItems ?? 0 }}</span>
                <span class="report-stat-label">已盘点</span>
              </div>
              <div class="report-stat-item">
                <span class="report-stat-value warning">{{ reportData.progress?.surplusCount ?? 0 }}</span>
                <span class="report-stat-label">盘盈</span>
              </div>
              <div class="report-stat-item">
                <span class="report-stat-value danger">{{ reportData.progress?.missingCount ?? 0 }}</span>
                <span class="report-stat-label">盘亏</span>
              </div>
            </div>
            <!-- 差异率 -->
            <div class="report-stats" v-if="reportData.progress?.checkedItems">
              <div class="report-stat-item">
                <span class="report-stat-value success">{{ reportData.progress?.matchRate ?? 0 }}%</span>
                <span class="report-stat-label">正常率</span>
              </div>
              <div class="report-stat-item">
                <span class="report-stat-value warning">{{ reportData.progress?.surplusRate ?? 0 }}%</span>
                <span class="report-stat-label">盘盈率</span>
              </div>
              <div class="report-stat-item">
                <span class="report-stat-value danger">{{ reportData.progress?.missingRate ?? 0 }}%</span>
                <span class="report-stat-label">盘亏率</span>
              </div>
            </div>
            <!-- 盘点明细列表 -->
            <div v-if="reportData.items?.length" class="report-table-wrapper">
              <table class="report-table">
                <thead>
                  <tr>
                    <th>资产编号</th>
                    <th>资产名称</th>
                    <th>账面数量</th>
                    <th>实际数量</th>
                    <th>变动</th>
                    <th>结果</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in reportData.items" :key="item.id">
                    <td>{{ item.assetId }}</td>
                    <td>{{ item.assetName ?? '-' }}</td>
                    <td>{{ item.expectedQty }}</td>
                    <td>{{ item.actualQty ?? '-' }}</td>
                    <td :style="{ color: (item.actualQty ?? 0) > item.expectedQty ? 'var(--color-success)' : (item.actualQty ?? 0) < item.expectedQty ? 'var(--color-danger)' : '' }">
                      {{ item.actualQty != null ? (item.actualQty - item.expectedQty >= 0 ? '+' : '') + (item.actualQty - item.expectedQty) : '-' }}
                    </td>
                    <td>{{ getResultLabel(item.result) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="report-empty">暂无盘点明细</div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="reportVisible = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inventory-page {
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

.btn-primary,
.btn-secondary {
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

.btn-primary {
  background: var(--color-primary-500);
  border: 1px solid var(--color-primary-500);
  color: white;
}

.btn-primary:hover {
  background: var(--color-primary-600);
}

.btn-secondary {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.btn-secondary:hover {
  border-color: var(--color-primary-300);
}

.btn-primary svg,
.btn-secondary svg {
  width: 18px;
  height: 18px;
}

/* 快速统计 */
.quick-stats {
  display: flex;
  gap: var(--space-8);
  margin-bottom: var(--space-6);
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

.stat-num.pending {
  color: var(--color-text-secondary);
}

.stat-num.in-progress {
  color: var(--color-primary-500);
}

.stat-num.review {
  color: oklch(0.60 0.14 85);
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* 筛选区 */
.filter-section {
  margin-bottom: var(--space-5);
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
  min-width: 140px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
}

/* 任务状态标签 */
.task-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: 500;
  white-space: nowrap;
}

/* 任务列表表格 */
.task-table-wrapper {
  overflow-x: auto;
}

.task-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-bg-card);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.task-table th {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-bg-page);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.task-table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: middle;
}

.task-table tbody tr:hover {
  background: var(--color-bg-page);
}

.task-table tbody tr:last-child td {
  border-bottom: none;
}

.table-empty {
  text-align: center;
  padding: var(--space-8) var(--space-4) !important;
  color: var(--color-text-tertiary);
}

.cell-name {
  font-weight: 600;
  min-width: 160px;
}

.cell-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: nowrap;
  min-width: 200px;
}

.row-btn {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: var(--text-xs);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  height: 28px;
  line-height: 1;
}

.row-btn.secondary {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.row-btn.secondary:hover {
  border-color: var(--color-primary-300);
}

.row-btn.primary {
  background: var(--color-primary-500);
  border: 1px solid var(--color-primary-500);
  color: white;
}

.row-btn.primary:hover {
  background: var(--color-primary-600);
}

.row-btn.accent {
  background: var(--color-bg-card);
  border: 1px solid var(--color-primary-300);
  color: var(--color-primary-600);
}

.row-btn.accent:hover {
  background: var(--color-primary-50);
}

.row-btn.warning {
  background: oklch(0.60 0.14 85);
  border: 1px solid oklch(0.60 0.14 85);
  color: white;
}

.row-btn.danger {
  background: transparent;
  border: 1px solid oklch(0.78 0.14 25);
  color: oklch(0.55 0.18 25);
}

.row-btn.danger:hover {
  background: oklch(0.95 0.06 25);
}

.row-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  color: var(--color-text-tertiary);
}

.row-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 详情视图 */
.detail-view {
  max-width: 1000px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.back-btn:hover {
  color: var(--color-primary-500);
}

.back-btn svg {
  width: 18px;
  height: 18px;
}

.header-actions {
  display: flex;
  gap: var(--space-3);
}

.detail-content {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  padding: var(--space-6);
}

.detail-title {
  font-size: var(--text-xl);
  font-weight: 600;
  margin: 0 0 var(--space-6) 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

.info-card {
  background: var(--color-bg-page);
  border-radius: 8px;
  padding: var(--space-4);
}

.info-card-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4) 0;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.info-item {
  display: flex;
  justify-content: space-between;
}

.info-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.info-value {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-weight: 500;
}

/* 统计卡片 */
.stats-card .stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.stat-box {
  text-align: center;
  padding: var(--space-3);
  background: var(--color-bg-card);
  border-radius: 6px;
}

.stat-number {
  display: block;
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-box.success .stat-number {
  color: var(--color-success);
}

.stat-box.warning .stat-number {
  color: oklch(0.60 0.14 85);
}

.stat-box.danger .stat-number {
  color: var(--color-danger);
}

.stat-text {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.progress-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.progress-bar-lg {
  flex: 1;
  height: 8px;
  background: var(--color-bg-card);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill-lg {
  height: 100%;
  background: var(--color-primary-500);
  border-radius: 4px;
}

.progress-text {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

/* 盘点人员卡片 */
.checkers-card {
  background: var(--color-bg-page);
  border-radius: 8px;
  padding: var(--space-4);
}

.checkers-list {
  display: flex;
  gap: var(--space-4);
}

.checker-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-card);
  border-radius: 8px;
}

.checker-avatar-lg {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  color: white;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.checker-info {
  display: flex;
  flex-direction: column;
}

.checker-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.checker-role {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 扫码视图 */
.scanning-view {
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.scanning-header {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  margin-bottom: var(--space-4);
}

.scanning-title {
  flex: 1;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.scanning-progress {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
}

.progress-num {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-primary-500);
}

.progress-total {
  font-size: var(--text-lg);
  color: var(--color-text-tertiary);
}

.scanning-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: var(--space-4);
}

/* 扫码区域 */
.scan-area {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  padding: var(--space-5);
}

.scan-input-wrapper {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.scan-input {
  flex: 1;
  height: 48px;
  padding: 0 var(--space-4);
  border: 2px solid var(--color-primary-300);
  border-radius: 10px;
  background: var(--color-bg-page);
  font-size: var(--text-base);
  font-family: var(--font-mono);
}

.scan-input:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}

.scan-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 48px;
  padding: 0 var(--space-5);
  background: var(--color-primary-500);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
}

.scan-btn svg {
  width: 20px;
  height: 20px;
}

/* 最近盘点 */
.recent-checks {
  flex: 1;
}

.recent-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3) 0;
}

.check-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.check-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-page);
  border-radius: 8px;
}

.check-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: oklch(0.92 0.08 145);
  color: var(--color-success);
  display: flex;
  align-items: center;
  justify-content: center;
}

.check-icon.warning {
  background: oklch(0.94 0.06 85);
  color: oklch(0.55 0.14 85);
}

.check-icon svg {
  width: 16px;
  height: 16px;
}

.check-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.check-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-primary-600);
}

.check-name {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.check-alert {
  font-size: var(--text-xs);
  color: oklch(0.55 0.14 85);
}

.check-time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 信息面板 */
.info-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.panel-card {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  padding: var(--space-4);
}

.panel-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4) 0;
}

/* 进度环 */
.progress-ring {
  width: 120px;
  height: 120px;
  margin: 0 auto var(--space-4);
  position: relative;
}

.progress-ring svg {
  width: 100%;
  height: 100%;
}

.progress-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.progress-percent {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-primary-500);
}

.progress-unit {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.progress-stats {
  display: flex;
  justify-content: center;
  gap: var(--space-6);
}

.p-stat {
  text-align: center;
}

.p-value {
  display: block;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.p-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 异常统计 */
.abnormal-stats {
  display: flex;
  gap: var(--space-3);
}

.abnormal-item {
  flex: 1;
  text-align: center;
  padding: var(--space-3);
  border-radius: 8px;
}

.abnormal-item.surplus {
  background: oklch(0.92 0.08 145);
}

.abnormal-item.missing {
  background: oklch(0.92 0.10 25);
}

.abnormal-count {
  display: block;
  font-size: var(--text-xl);
  font-weight: 700;
}

.abnormal-item.surplus .abnormal-count {
  color: var(--color-success);
}

.abnormal-item.missing .abnormal-count {
  color: var(--color-danger);
}

.abnormal-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

/* 面板操作 */
.panel-actions {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.panel-btn {
  height: 40px;
  border-radius: 8px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
}

.panel-btn.secondary {
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
}

.panel-btn.primary {
  background: var(--color-primary-500);
  border: 1px solid var(--color-primary-500);
  color: white;
}

/* ========== 弹窗通用样式 ========== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-dialog {
  background: var(--color-bg-card);
  border-radius: 14px;
  width: 480px;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal-dialog.modal-lg {
  width: 720px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border-light);
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
  color: var(--color-text-primary);
}

.modal-close svg {
  width: 18px;
  height: 18px;
}

.modal-body {
  padding: var(--space-5);
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--color-border-light);
}

/* 表单样式 */
.form-group {
  margin-bottom: var(--space-4);
}

.form-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.form-label .required {
  color: var(--color-danger);
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}

/* ========== 报告样式 ========== */
.report-loading {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-text-tertiary);
}

.report-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.report-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.report-stat-item {
  text-align: center;
  padding: var(--space-3);
  background: var(--color-bg-page);
  border-radius: 8px;
}

.report-stat-value {
  display: block;
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.report-stat-value.success {
  color: var(--color-success);
}

.report-stat-value.warning {
  color: oklch(0.60 0.14 85);
}

.report-stat-value.danger {
  color: var(--color-danger);
}

.report-stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.report-table-wrapper {
  overflow-x: auto;
}

.report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.report-table th,
.report-table td {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  border-bottom: 1px solid var(--color-border-light);
}

.report-table th {
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-bg-page);
}

.report-table td {
  color: var(--color-text-primary);
}

.report-empty {
  text-align: center;
  padding: var(--space-6);
  color: var(--color-text-tertiary);
}

/* 响应式 */
@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .scanning-content {
    grid-template-columns: 1fr;
  }

  .info-panel {
    order: -1;
  }
}
</style>
