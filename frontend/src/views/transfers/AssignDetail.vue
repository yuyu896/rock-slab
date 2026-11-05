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
    title="领用出库详情"
    back-path="/transfers/assign"
    type="assign"
    :doc="transfer"
    :loading="loading"
    @lifecycle-changed="fetchTransfer"
    @approve="handleApprove"
    @reject="handleReject"
  >
    <template #extra-view="{ doc }">
      <div v-if="doc.备注" class="history-note">
        <label>历史/审批信息</label>
        <span>{{ doc.备注 }}</span>
      </div>
    </template>
  </TransferDetailLayout>
</template>

<style scoped>
.history-note { display: flex; flex-direction: column; gap: 4px; font-size: var(--text-sm); white-space: pre-wrap; overflow-wrap: anywhere; }
.history-note label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.history-note span { color: var(--color-text-primary); }
</style>
