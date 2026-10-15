<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { submitTransfer, withdrawTransfer } from '@/api/transfers'
import { handleApiError } from '@/utils/request'
import type { TransferDocument, TransferActionType } from '@/types'

const props = defineProps<{
  doc: TransferDocument
  type: TransferActionType
  compact?: boolean
}>()

const emit = defineEmits<{ (event: 'changed'): void }>()
const router = useRouter()

const createPath = computed(() => `/transfers/${props.type}/create`)
const editable = computed(() => props.doc.canEditDraft === true && ['草稿', '已驳回'].includes(props.doc.审批状态))

function openEditor() {
  router.push({ path: createPath.value, query: { id: props.doc.id } })
}

async function submitDraft() {
  try {
    await submitTransfer(props.doc.id)
    ElMessage.success('已提交审批')
    emit('changed')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

async function withdraw() {
  try {
    await ElMessageBox.confirm('撤回后单据回到草稿，可修改后重新提交', '确认撤回？', {
      confirmButtonText: '撤回',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await withdrawTransfer(props.doc.id)
    ElMessage.success('已撤回为草稿')
    emit('changed')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}
</script>

<template>
  <button v-if="editable" class="lifecycle-btn" :class="{ compact }" @click="openEditor">
    {{ doc.审批状态 === '草稿' ? '修改草稿' : '修改并重提' }}
  </button>
  <button v-if="doc.审批状态 === '草稿' && doc.canEditDraft === true" class="lifecycle-btn primary" :class="{ compact }" @click="submitDraft">
    提交审批
  </button>
  <button v-if="doc.canWithdraw" class="lifecycle-btn warning" :class="{ compact }" @click="withdraw">
    撤回
  </button>
</template>

<style scoped>
.lifecycle-btn { min-height: 36px; padding: 0 12px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-bg-card); color: var(--color-text-primary); cursor: pointer; white-space: nowrap; }
.lifecycle-btn.primary { border-color: var(--color-primary-500); background: var(--color-primary-500); color: #fff; }
.lifecycle-btn.warning { border-color: var(--color-warning); color: var(--color-warning); }
.lifecycle-btn.compact { min-height: 30px; padding: 0 8px; font-size: var(--text-xs); }
.lifecycle-btn:focus-visible { outline: 2px solid var(--color-primary-500); outline-offset: 2px; }
</style>
