<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import TransferDetailLayout from './components/TransferDetailLayout.vue'
import { getTransfer, approveTransfer, rejectTransfer } from '@/api/transfers'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TransferDocument } from '@/types'

const route = useRoute()
const transfer = ref<TransferDocument | null>(null)
const loading = ref(false)

async function fetchTransfer() {
  loading.value = true
  try {
    const { data } = await getTransfer(route.params.id as string)
    transfer.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

async function handleApprove() {
  try {
    await ElMessageBox.confirm('确定通过此申请？', '审批确认', { type: 'info' })
    await approveTransfer(route.params.id as string, { approved: true })
    ElMessage.success('审批通过')
    await fetchTransfer()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(handleApiError(error))
  }
}

async function handleReject() {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回确认', {
      confirmButtonText: '确定驳回',
      cancelButtonText: '取消',
      inputValidator: (v: string) => (v && v.trim() ? true : '请输入驳回原因'),
    })
    await rejectTransfer(route.params.id as string, { reason: value })
    ElMessage.success('已驳回')
    await fetchTransfer()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(handleApiError(error))
  }
}

onMounted(fetchTransfer)
</script>

<template>
  <TransferDetailLayout
    title="调拨详情"
    back-path="/transfers/transfer"
    type="transfer"
    :doc="transfer"
    :loading="loading"
    @approve="handleApprove"
    @reject="handleReject"
  >
    <template #extra-view="{ doc }">
      <div class="extra-grid">
        <span class="extra-item"><label>调出部门</label><span>{{ doc.调出部门 || '-' }}</span></span>
        <span class="extra-item"><label>调入部门</label><span>{{ doc.调入部门 || '-' }}</span></span>
        <span class="extra-item"><label>调出负责人</label><span>{{ doc.调出负责人 || '-' }}</span></span>
        <span class="extra-item"><label>调入负责人</label><span>{{ doc.调入负责人 || '-' }}</span></span>
        <span class="extra-item"><label>调拨原因</label><span>{{ doc.调拨原因 || '-' }}</span></span>
        <span class="extra-item full"><label>备注</label><span>{{ doc.备注 || '-' }}</span></span>
      </div>
    </template>
  </TransferDetailLayout>
</template>

<style scoped>
.extra-grid { display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-6); }
.extra-item { display: inline-flex; align-items: baseline; gap: 6px; font-size: var(--text-sm); }
.extra-item label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.extra-item span { color: var(--color-text-primary); }
.extra-item.full { flex-basis: 100%; }
</style>
