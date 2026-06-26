<script setup lang="ts">
import { formatMoney } from '@/utils/format'

defineProps<{
  visible: boolean
  order: any
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'approve', order: any): void
  (e: 'reject', order: any): void
}>()

const getStatusStyle = (status: string) => {
  const map: Record<string, { bg: string; color: string }> = {
    '待审批': { bg: 'var(--color-approval-pending-bg)', color: 'var(--color-approval-pending-text)' },
    '已通过': { bg: 'var(--color-approval-approved-bg)', color: 'var(--color-approval-approved-text)' },
    '已驳回': { bg: 'var(--color-approval-rejected-bg)', color: 'var(--color-approval-rejected-text)' },
  }
  return map[status] || { bg: 'var(--color-inventory-unchecked-bg)', color: 'var(--color-inventory-unchecked-text)' }
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content detail-modal">
      <div class="modal-header">
        <h3 class="modal-title">采购单详情</h3>
        <button class="modal-close" @click="emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="modal-body" v-loading="loading">
        <div v-if="order" class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">入库单号</span>
            <span class="detail-value order-no">{{ order.orderNo }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">分公司</span>
            <span class="detail-value">{{ order.branch }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">供应商</span>
            <span class="detail-value">{{ order.supplier }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">物品数量</span>
            <span class="detail-value">{{ order.totalCount }}件</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">入库金额</span>
            <span class="detail-value amount">{{ formatMoney(order.totalAmount) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">状态</span>
            <span class="status-badge" :style="getStatusStyle(order.status)">{{ order.status }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">提交人</span>
            <span class="detail-value">{{ order.submitter }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">提交时间</span>
            <span class="detail-value">{{ order.submitTime }}</span>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button v-if="order?.status === '待审批'" class="btn-reject" @click="emit('reject', order)">驳回</button>
        <button v-if="order?.status === '待审批'" class="btn-confirm" @click="emit('approve', order)">通过</button>
        <button v-else class="btn-cancel" @click="emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-elevated); border-radius: 16px; width: 90%; max-width: 560px; max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); }
.modal-title { font-size: 18px; font-weight: 600; margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; color: var(--color-text-secondary); padding: 4px; }
.modal-close svg { width: 20px; height: 20px; }
.modal-body { padding: 24px; }
.modal-footer { padding: 16px 24px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.detail-item { display: flex; flex-direction: column; gap: 4px; }
.detail-label { font-size: 13px; color: var(--color-text-secondary); }
.detail-value { font-size: 15px; font-weight: 500; }
.detail-value.order-no { font-family: monospace; color: var(--color-primary); }
.detail-value.amount { color: var(--color-warning); font-weight: 700; }
.status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 500; }
.btn-confirm { padding: 8px 20px; border-radius: 8px; border: none; background: var(--color-primary); color: #fff; cursor: pointer; font-size: 14px; }
.btn-reject { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-danger); background: #fff; color: var(--color-danger); cursor: pointer; font-size: 14px; }
.btn-cancel { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 14px; }
</style>
