<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import TransferDetailLayout from './components/TransferDetailLayout.vue'
import { getTransfer } from '@/api/transfers'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
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

onMounted(fetchTransfer)
</script>

<template>
  <TransferDetailLayout
    title="回收详情"
    back-path="/transfers/recovery"
    type="recovery"
    :doc="transfer"
    :loading="loading"
  >
    <template #extra-view="{ doc }">
      <div class="extra-grid">
        <span class="extra-item"><label>回收分类</label><span>{{ doc.回收分类 || '-' }}</span></span>
        <span class="extra-item"><label>回收去向</label><span>{{ doc.回收去向 === 'dispose' ? '直接处置' : '入回收库' }}</span></span>
        <span v-if="doc.回收去向 === 'dispose'" class="extra-item"><label>处置方式</label><span>{{ doc.处置方式 || '-' }}</span></span>
        <span v-if="doc.回收去向 === 'dispose' && doc.处置方式 === '出售'" class="extra-item"><label>处置金额</label><span>{{ doc.处置金额 ?? '-' }}</span></span>
        <span class="extra-item"><label>所属部门</label><span>{{ doc.调出部门 || '-' }}</span></span>
        <span class="extra-item"><label>出库日期</label><span class="mono">{{ doc.出库日期 || '-' }}</span></span>
        <span class="extra-item"><label>经办人</label><span>{{ doc.采购经办人 || '-' }}</span></span>
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
.mono { font-family: var(--font-mono); }
</style>
