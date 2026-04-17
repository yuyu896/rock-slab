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
  getInventoryProgress,
  submitInventory,
  downloadInventoryTemplate,
  importInventoryResult,
} from '@/api/inventories'
import { getBranches } from '@/api/branches'
import { getCategories } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { MISSED_RULE_LABELS, REPEAT_RULE_LABELS } from '@/constants'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { MissedRuleType, RepeatRuleType } from '@/types'

import InventoryTaskList from './inventory/InventoryTaskList.vue'
import InventoryCheckPanel from './inventory/InventoryCheckPanel.vue'
import InventoryReport from './inventory/InventoryReport.vue'

const inventoryStore = useInventoryStore()
const router = useRouter()

// 当前视图状态
const currentView = ref<'list' | 'detail' | 'scanning'>('list')

// 加载状态
const loading = ref(false)

// 盘点任务列表
const inventoryTasks = ref<any[]>([])

// 分页
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

// 当前选中的任务
const selectedTask = ref<any>(null)

// 全局状态统计
const statusStats = ref({ pending: 0, inProgress: 0, pendingReview: 0 })

// 报告弹窗
const reportVisible = ref(false)
const reportRef = ref<InstanceType<typeof InventoryReport> | null>(null)

// 筛选条件
const filters = ref({ status: '', branch: '', keyword: '' })

// 分公司选项
const branchOptions = ref<{ value: string; label: string }[]>([{ value: '', label: '全部分公司' }])

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
const categoryOptions = ref<{ value: string; label: string }[]>([])
async function fetchCategories() {
  try {
    const { data } = await getCategories({ pageSize: 500 })
    const categories = (data.results || []) as any[]
    categoryOptions.value = categories.map(c => ({
      value: c.id,
      label: `${c['资产类目']} - ${c['物品分类']}${c['资产名称'] ? ' - ' + c['资产名称'] : ''}`,
    }))
  } catch (error) {
    console.error('Failed to fetch categories:', error)
  }
}

// 获取全局状态统计
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

// 查看任务详情
const viewTask = async (task: any) => {
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
  const branchOpt = branchOptions.value.find(b => b.value === task.branch)
  enriched.branchName = branchOpt?.label || task.branch || '全部分公司'
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

// ========== 创建盘点任务 ==========
const creatingTask = ref(false)
const showCreateTaskModal = ref(false)
const newTaskForm = reactive({
  name: '',
  branchId: '',
  categoryId: '',
  missedRule: 'keep' as MissedRuleType,
  repeatRule: 'last' as RepeatRuleType,
})

const missedRuleOptions = Object.entries(MISSED_RULE_LABELS).map(([value, label]) => ({ value, label }))
const repeatRuleOptions = Object.entries(REPEAT_RULE_LABELS).map(([value, label]) => ({ value, label }))

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

// ========== 删除盘点任务 ==========
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

// ========== 作废盘点任务 ==========
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

// ========== 审批通过 ==========
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

// ========== 驳回 ==========
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

// ========== 重新盘点 ==========
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

// ========== 下载模板 ==========
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

// ========== 导入盘点结果 ==========
const importFileInput = ref<HTMLInputElement | null>(null)
const importingTaskId = ref<string | null>(null)

const triggerImport = (task: any) => {
  importingTaskId.value = task.id
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

// ========== 查看报告 ==========
const viewReport = (task: any) => {
  reportRef.value?.open(task.id)
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
      <InventoryTaskList
        :loading="loading"
        :tasks="filteredTasks"
        :stats="stats"
        :filters="filters"
        :branch-options="branchOptions"
        @update:filters="filters = $event"
        @create="openCreateTaskModal"
        @view="viewTask"
        @start="startInventory"
        @delete="deleteTask"
        @cancel="cancelTask"
        @approve="approveTask"
        @reject="rejectTask"
        @recount="recountTask"
        @recount-all="recountAllTask"
        @report="viewReport"
        @download-template="downloadTemplateAction"
        @import="triggerImport"
        @submit="submitFromScan"
      />

      <!-- 隐藏的文件导入 input -->
      <input
        ref="importFileInput"
        type="file"
        accept=".xlsx,.xls"
        style="display: none"
        @change="handleImportFile"
      />
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
                  <div class="progress-fill-lg" :style="{ width: selectedTask.progress + '%' }" />
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
      <InventoryCheckPanel
        :task="selectedTask"
        @back="backToList"
        @submit="submitFromScan"
      />
    </template>

    <!-- 创建盘点任务弹窗 -->
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

    <!-- 报告弹窗 -->
    <InventoryReport ref="reportRef" :visible="reportVisible" @update:visible="reportVisible = $event" />
  </div>
</template>

<style scoped>
.inventory-page { max-width: 1400px; margin: 0 auto; }

/* 详情视图 */
.detail-view { display: flex; flex-direction: column; gap: 24px; }
.detail-header { display: flex; justify-content: space-between; align-items: center; }
.back-btn { display: flex; align-items: center; gap: 6px; background: none; border: 1px solid var(--color-border); border-radius: 8px; padding: 8px 16px; cursor: pointer; color: var(--color-text-secondary); font-size: 14px; }
.back-btn svg { width: 16px; height: 16px; }
.header-actions { display: flex; gap: 12px; }
.btn-primary, .btn-secondary { display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 20px; border-radius: 10px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; }
.btn-primary { background: var(--color-primary); color: #fff; }
.btn-secondary { background: var(--color-bg-elevated); color: var(--color-text-secondary); border: 1px solid var(--color-border); }
.btn-primary svg, .btn-secondary svg { width: 16px; height: 16px; }
.detail-title { font-size: 20px; font-weight: 600; margin: 0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.info-card { background: var(--color-bg-elevated); border-radius: 12px; padding: 20px; border: 1px solid var(--color-border); }
.info-card-title { font-size: 14px; font-weight: 600; margin: 0 0 16px; }
.info-list { display: flex; flex-direction: column; gap: 12px; }
.info-item { display: flex; justify-content: space-between; font-size: 14px; }
.info-label { color: var(--color-text-secondary); }
.info-value { font-weight: 500; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.stat-box { text-align: center; padding: 12px; background: var(--color-bg); border-radius: 8px; }
.stat-box.success { border-left: 3px solid var(--color-success); }
.stat-box.warning { border-left: 3px solid var(--color-warning); }
.stat-box.danger { border-left: 3px solid var(--color-danger); }
.stat-number { display: block; font-size: 24px; font-weight: 700; }
.stat-text { font-size: 12px; color: var(--color-text-secondary); }
.progress-info { display: flex; align-items: center; gap: 12px; }
.progress-bar-lg { flex: 1; height: 8px; background: var(--color-bg); border-radius: 4px; overflow: hidden; }
.progress-fill-lg { height: 100%; background: var(--color-primary); border-radius: 4px; transition: width 0.3s; }
.progress-text { font-size: 13px; color: var(--color-text-secondary); white-space: nowrap; }
.checkers-card { background: var(--color-bg-elevated); border-radius: 12px; padding: 20px; border: 1px solid var(--color-border); }

/* 模态框 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-dialog { background: var(--color-bg-elevated); border-radius: 12px; width: 90%; max-width: 500px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); }
.modal-title { font-size: 18px; font-weight: 600; margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; padding: 4px; color: var(--color-text-secondary); }
.modal-close svg { width: 20px; height: 20px; }
.modal-body { padding: 24px; }
.modal-footer { padding: 16px 24px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.form-group { margin-bottom: 16px; }
.form-label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 6px; }
.required { color: var(--color-danger); }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg); outline: none; }
.form-input:focus { border-color: var(--color-primary); }
</style>
