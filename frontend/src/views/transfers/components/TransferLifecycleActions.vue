<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteTransferDraft, submitTransfer, withdrawTransfer } from '@/api/transfers'
import { useUserStore } from '@/store/user'
import { handleApiError } from '@/utils/request'
import type { TransferDocument } from '@/types'
import { canManageTransfer, TRANSFER_PERMISSION_OPERATIONS, type ActiveTransferActionType } from '@/utils/permissionGroups'

const props = withDefaults(defineProps<{
  doc: TransferDocument
  type: ActiveTransferActionType
  compact?: boolean
  showWithdraw?: boolean
  showEdit?: boolean
  showSubmit?: boolean
}>(), {
  showWithdraw: false,
  showEdit: true,
  showSubmit: true,
})

const emit = defineEmits<{ (event: 'changed' | 'deleted'): void }>()
const router = useRouter()
const userStore = useUserStore()
const permissionOperations = computed(() => TRANSFER_PERMISSION_OPERATIONS[props.type])

const createPath = computed(() => `/transfers/${props.type}/create`)
const canManage = computed(() => canManageTransfer(props.type, code => userStore.can(code)))
const editable = computed(() => canManage.value
  && props.doc.canEditDraft === true && ['草稿', '已驳回'].includes(props.doc.审批状态))
const canDeleteDraft = computed(() => userStore.can(permissionOperations.value.deleteDraft)
  && userStore.can(permissionOperations.value.view)
  && props.doc.canEditDraft === true && props.doc.审批状态 === '草稿')
const canSubmit = computed(() => canManage.value)
const canWithdraw = computed(() => canManage.value && props.doc.canWithdraw)

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

async function deleteDraft() {
  const number = props.doc.单据编号 || props.doc.id.slice(0, 8)
  try {
    await ElMessageBox.confirm(
      `删除草稿 ${number} 后无法恢复，确认删除？`,
      '删除草稿',
      { confirmButtonText: '删除草稿', cancelButtonText: '保留草稿', type: 'warning' },
    )
    await deleteTransferDraft(props.doc.id)
    ElMessage.success('草稿已删除')
    emit('deleted')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(handleApiError(error))
  }
}
</script>

<template>
  <button v-if="props.showEdit && editable" class="lifecycle-btn" :class="{ compact }" @click="openEditor">
    {{ doc.审批状态 === '草稿' ? '修改草稿' : '修改并重提' }}
  </button>
  <button v-if="props.showSubmit && canSubmit && doc.审批状态 === '草稿' && doc.canEditDraft === true" class="lifecycle-btn primary" :class="{ compact }" @click="submitDraft">
    提交审批
  </button>
  <button v-if="canDeleteDraft" class="lifecycle-btn danger" :class="{ compact }" @click="deleteDraft">
    删除草稿
  </button>
  <button v-if="props.showWithdraw && canWithdraw" class="lifecycle-btn warning" :class="{ compact }" @click="withdraw">
    撤回
  </button>
</template>

<style scoped>
.lifecycle-btn { min-height: 36px; padding: 0 12px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-bg-card); color: var(--color-text-primary); cursor: pointer; white-space: nowrap; }
.lifecycle-btn.primary { border-color: var(--color-primary-500); background: var(--color-primary-500); color: #fff; }
.lifecycle-btn.warning { border-color: var(--color-warning); color: var(--color-warning); }
.lifecycle-btn.danger { border-color: var(--color-danger); color: var(--color-danger); }
.lifecycle-btn.compact { height: 30px; min-height: 30px; padding: 0 8px; font-size: var(--text-xs); line-height: 1; }
.lifecycle-btn:focus-visible { outline: 2px solid var(--color-primary-500); outline-offset: 2px; }
</style>
