<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTransfers, approveTransfer, rejectTransfer } from '@/api/transfers'
import { useUserStore } from '@/store/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Transfer } from '@/types'

const router = useRouter()
const userStore = useUserStore()

const pendingApprovals = ref<Transfer[]>([])
const doneApprovals = ref<Transfer[]>([])
const loading = ref(false)
const activeTab = ref<'pending' | 'done'>('pending')

const canApprove = computed(() => userStore.hasMinRole('supervisor'))

const actionLabels: Record<string, string> = {
  assign: '领用',
  return: '归还',
  transfer: '调拨',
}

function getActionType(transfer: Transfer): string {
  return (transfer as any).action_type || 'transfer'
}

async function fetchPendingApprovals() {
  loading.value = true
  try {
    const { data } = await getTransfers({ status: '待审批', pageSize: 50 })
    pendingApprovals.value = data.results || []
  } catch (error) {
    ElMessage.error('获取待审批列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchDoneApprovals() {
  loading.value = true
  try {
    const { data } = await getTransfers({ status: '已通过,已驳回', pageSize: 50 })
    doneApprovals.value = data.results || []
  } catch (error) {
    ElMessage.error('获取已处理列表失败')
  } finally {
    loading.value = false
  }
}

async function handleApprove(transfer: Transfer) {
  try {
    await ElMessageBox.confirm('确定通过此申请？', '审批确认', {
      confirmButtonText: '通过',
      cancelButtonText: '取消',
      type: 'success',
    })
    await approveTransfer(transfer.id, { approved: true })
    ElMessage.success('审批通过')
    await fetchPendingApprovals()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '操作失败')
    }
  }
}

async function handleReject(transfer: Transfer) {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回', {
      confirmButtonText: '确定驳回',
      cancelButtonText: '取消',
      inputPlaceholder: '请说明驳回原因',
    })
    await rejectTransfer(transfer.id, { reason: value || '' })
    ElMessage.success('已驳回')
    await fetchPendingApprovals()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '操作失败')
    }
  }
}

function viewDetail(transfer: Transfer) {
  router.push(`/mobile/approval/${transfer.id}`)
}

function formatTime(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  fetchPendingApprovals()
  fetchDoneApprovals()
})
</script>

<template>
  <div class="approval-list-page">
    <!-- 头部 -->
    <div class="page-header">
      <h1>审批中心</h1>
      <span class="pending-count">{{ pendingApprovals.length }} 条待处理</span>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button
        :class="{ active: activeTab === 'pending' }"
        @click="activeTab = 'pending'"
      >
        待审批
        <span v-if="pendingApprovals.length" class="tab-badge">{{ pendingApprovals.length }}</span>
      </button>
      <button
        :class="{ active: activeTab === 'done' }"
        @click="activeTab = 'done'"
      >
        已处理
      </button>
    </div>

    <!-- 待审批列表 -->
    <div v-if="activeTab === 'pending'" class="approval-list">
      <div
        v-for="item in pendingApprovals"
        :key="item.id"
        class="approval-card"
      >
        <div class="card-header" @click="viewDetail(item)">
          <span class="type-tag">{{ actionLabels[item.action_type || 'transfer'] }}</span>
          <span class="time">{{ formatTime(item.createdAt) }}</span>
        </div>

        <div class="card-body" @click="viewDetail(item)">
          <h3 class="asset-name">{{ item.资产名称 }}</h3>
          <p class="asset-code">{{ item.资产编号 }}</p>
          <div class="flow-info">
            <span class="from">{{ item.调出分公司 || '-' }}</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
            <span class="to">{{ item.调入分公司 || '-' }}</span>
          </div>
          <p class="submitter">提交人：{{ item.创建人 || '-' }}</p>
        </div>

        <div v-if="canApprove" class="card-actions">
          <button class="reject-btn" @click="handleReject(item)">驳回</button>
          <button class="approve-btn" @click="handleApprove(item)">通过</button>
        </div>
      </div>

      <div v-if="!pendingApprovals.length && !loading" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <polyline points="20 6 9 17 4.5 4.5"/>
        </svg>
        <p>暂无待审批事项</p>
      </div>
    </div>

    <!-- 已处理列表 -->
    <div v-if="activeTab === 'done'" class="approval-list">
      <div
        v-for="item in doneApprovals"
        :key="item.id"
        class="approval-card done"
      >
        <div class="card-header">
          <span class="type-tag">{{ actionLabels[item.action_type || 'transfer'] }}</span>
          <span
            class="status-tag"
            :class="{ passed: item.审批状态 === '已通过', rejected: item.审批状态 === '已驳回' }"
          >
            {{ item.审批状态 }}
          </span>
        </div>

        <div class="card-body">
          <h3 class="asset-name">{{ item.资产名称 }}</h3>
          <p class="asset-code">{{ item.资产编号 }}</p>
          <p class="approver">审批人：{{ item.审批人 || '-' }}</p>
        </div>
      </div>

      <div v-if="!doneApprovals.length && !loading" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 8v4l3 3m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <p>暂无已处理记录</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.approval-list-page {
  padding: var(--space-4);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.pending-count {
  font-size: 13px;
  color: var(--color-primary-500);
}

.tab-bar {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.tab-bar button {
  flex: 1;
  height: 44px;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  cursor: pointer;
  position: relative;
}

.tab-bar button.active {
  background: var(--color-primary-500);
  color: white;
}

.tab-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  font-size: 10px;
  font-weight: 600;
  color: white;
  background: var(--color-danger);
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.approval-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  margin-bottom: var(--space-3);
  overflow: hidden;
}

.approval-card.done {
  opacity: 0.8;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-elevated);
}

.type-tag {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--color-primary-50);
  color: var(--color-primary-600);
}

.time {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.status-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
}

.status-tag.passed {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.status-tag.rejected {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.card-body {
  padding: var(--space-4);
  cursor: pointer;
}

.asset-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.asset-code {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--color-text-tertiary);
  margin: 0;
}

.flow-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
  font-size: 13px;
}

.flow-info svg {
  width: 16px;
  height: 16px;
  color: var(--color-text-tertiary);
}

.from, .to {
  color: var(--color-text-secondary);
}

.submitter,
.approver {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin: var(--space-2) 0 0;
}

.card-actions {
  display: flex;
  border-top: 1px solid var(--color-border);
}

.card-actions button {
  flex: 1;
  height: 48px;
  border: none;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
}

.reject-btn {
  background: transparent;
  color: var(--color-danger);
  border-right: 1px solid var(--color-border) !important;
}

.approve-btn {
  background: transparent;
  color: var(--color-success);
}

.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin-bottom: var(--space-3);
}
</style>
