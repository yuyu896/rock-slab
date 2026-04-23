<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTransfer, approveTransfer, rejectTransfer } from '@/api/transfers'
import { useUserStore } from '@/store/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Transfer } from '@/types'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const transferId = computed(() => route.params.id as string)
const transfer = ref<Transfer | null>(null)
const loading = ref(true)
const rejectReason = ref('')
const showRejectInput = ref(false)

const canApprove = computed(() => userStore.hasMinRole('supervisor'))

const actionLabels: Record<string, string> = {
  assign: '领用',
  return: '归还',
  transfer: '调拨',
}

const statusColors: Record<string, string> = {
  待审批: 'var(--color-warning)',
  已通过: 'var(--color-success)',
  已驳回: 'var(--color-danger)',
}

async function fetchDetail() {
  loading.value = true
  try {
    const { data } = await getTransfer(transferId.value)
    transfer.value = data
  } catch (error) {
    ElMessage.error('获取详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

async function handleApprove() {
  if (!transfer.value) return
  try {
    await ElMessageBox.confirm('确定通过此申请？', '审批确认', {
      confirmButtonText: '通过',
      cancelButtonText: '取消',
      type: 'success',
    })
    await approveTransfer(transfer.value.id, { approved: true })
    ElMessage.success('审批通过')
    router.push('/mobile/approval')
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || '操作失败')
    }
  }
}

async function handleReject() {
  if (!transfer.value) return
  if (!rejectReason.value.trim()) {
    showRejectInput.value = true
    return
  }
  try {
    await rejectTransfer(transfer.value.id, { reason: rejectReason.value })
    ElMessage.success('已驳回')
    router.push('/mobile/approval')
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  fetchDetail()
})
</script>

<template>
  <div class="approval-detail-page">
    <!-- 头部导航 -->
    <div class="page-header">
      <button class="back-btn" @click="router.back()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
      <h1>审批详情</h1>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <span>加载中...</span>
    </div>

    <!-- 详情内容 -->
    <div v-else-if="transfer" class="detail-content">
      <!-- 状态卡片 -->
      <div class="status-card">
        <div class="status-header">
          <span class="action-type">{{ actionLabels[transfer.action_type || 'transfer'] }}</span>
          <span class="status-tag" :style="{ color: statusColors[transfer.审批状态] }">
            {{ transfer.审批状态 }}
          </span>
        </div>
        <div class="asset-info">
          <h2 class="asset-name">{{ transfer.资产名称 }}</h2>
          <p class="asset-code">{{ transfer.资产编号 }}</p>
        </div>
      </div>

      <!-- 详细信息 -->
      <div class="info-section">
        <h3 class="section-title">基本信息</h3>
        <div class="info-list">
          <div class="info-item">
            <span class="label">调拨日期</span>
            <span class="value">{{ formatDate(transfer.调拨日期) }}</span>
          </div>
          <div class="info-item">
            <span class="label">调拨数量</span>
            <span class="value">{{ transfer.调拨数量 }}</span>
          </div>
          <div class="info-item">
            <span class="label">调出分公司</span>
            <span class="value">{{ transfer.调出分公司 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">调入分公司</span>
            <span class="value">{{ transfer.调入分公司 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">调出负责人</span>
            <span class="value">{{ transfer.调出负责人 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">调入负责人</span>
            <span class="value">{{ transfer.调入负责人 || '-' }}</span>
          </div>
          <div v-if="transfer.调拨原因" class="info-item">
            <span class="label">调拨原因</span>
            <span class="value">{{ transfer.调拨原因 }}</span>
          </div>
          <div v-if="transfer.备注" class="info-item">
            <span class="label">备注</span>
            <span class="value">{{ transfer.备注 }}</span>
          </div>
        </div>
      </div>

      <!-- 审批信息 -->
      <div v-if="transfer.审批人" class="info-section">
        <h3 class="section-title">审批信息</h3>
        <div class="info-list">
          <div class="info-item">
            <span class="label">审批人</span>
            <span class="value">{{ transfer.审批人 }}</span>
          </div>
          <div class="info-item">
            <span class="label">审批时间</span>
            <span class="value">{{ transfer.审批时间 || '-' }}</span>
          </div>
        </div>
      </div>

      <!-- 提交信息 -->
      <div class="info-section">
        <h3 class="section-title">提交信息</h3>
        <div class="info-list">
          <div class="info-item">
            <span class="label">提交人</span>
            <span class="value">{{ transfer.创建人 }}</span>
          </div>
          <div class="info-item">
            <span class="label">提交时间</span>
            <span class="value">{{ formatDate(transfer.createdAt) }}</span>
          </div>
        </div>
      </div>

      <!-- 驳回输入 -->
      <div v-if="showRejectInput" class="reject-section">
        <textarea
          v-model="rejectReason"
          placeholder="请输入驳回原因..."
          class="reject-input"
        />
      </div>

      <!-- 操作按钮 -->
      <div v-if="canApprove && transfer.审批状态 === '待审批'" class="action-section">
        <button class="reject-btn" @click="handleReject">
          {{ showRejectInput ? '确认驳回' : '驳回' }}
        </button>
        <button class="approve-btn" @click="handleApprove">
          通过
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.approval-detail-page {
  padding: var(--space-4);
  padding-bottom: 100px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.back-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 10px;
  background: var(--color-bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.back-btn svg {
  width: 20px;
  height: 20px;
  color: var(--color-text-secondary);
}

.page-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.loading-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-tertiary);
}

.status-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.action-type {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.status-tag {
  font-size: 14px;
  font-weight: 600;
}

.asset-info {
  text-align: center;
  padding: var(--space-2) 0;
}

.asset-name {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.asset-code {
  font-size: 13px;
  font-family: var(--font-mono);
  color: var(--color-text-tertiary);
  margin: 4px 0 0;
}

.info-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  margin-bottom: var(--space-3);
  overflow: hidden;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-elevated);
  margin: 0;
}

.info-list {
  padding: var(--space-2) var(--space-4);
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) 0;
}

.info-item .label {
  font-size: 14px;
  color: var(--color-text-tertiary);
}

.info-item .value {
  font-size: 14px;
  color: var(--color-text-primary);
  font-weight: 500;
}

.reject-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.reject-input {
  width: 100%;
  height: 100px;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-page);
  font-size: 14px;
  resize: none;
}

.action-section {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-width: 480px;
  margin: 0 auto;
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-card);
  border-top: 1px solid var(--color-border);
}

.reject-btn,
.approve-btn {
  flex: 1;
  height: 50px;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
}

.reject-btn {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.approve-btn {
  background: var(--color-success);
  color: white;
}
</style>
