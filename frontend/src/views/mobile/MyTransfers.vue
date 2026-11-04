<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deleteTransferDraft, getTransfers, submitTransfer, withdrawTransfer } from '@/api/transfers'
import { useUserStore } from '@/store/user'
import { handleApiError } from '@/utils/request'
import { transferDocSummary } from '@/types'
import type { Transfer } from '@/types'
import { canManageTransfer, MY_DOCUMENT_PERMISSION_KEYS, TRANSFER_PERMISSION_OPERATIONS, type ActiveTransferActionType } from '@/utils/permissionGroups'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const activeStatus = ref<'草稿' | '已驳回' | '待审批'>('草稿')
const documents = ref<Transfer[]>([])
const visibleDocuments = computed(() => documents.value.filter((doc) => doc.审批状态 === activeStatus.value))

const typeLabels: Record<string, string> = {
  purchase: '采购入库',
  assign: '领用出库',
  transfer: '调拨',
  recovery: '回收',
}

const mobileCreatePaths: Partial<Record<ActiveTransferActionType, string>> = {
  purchase: '/mobile/purchase',
  assign: '/mobile/submit/assign',
  transfer: '/mobile/submit/transfer',
}

async function fetchDocuments() {
  loading.value = true
  try {
    const types = (Object.keys(TRANSFER_PERMISSION_OPERATIONS) as ActiveTransferActionType[])
      .filter((type) => userStore.can(TRANSFER_PERMISSION_OPERATIONS[type].view)
        && MY_DOCUMENT_PERMISSION_KEYS.some((key) =>
        userStore.can(TRANSFER_PERMISSION_OPERATIONS[type][key]),
        ))
    const statuses = ['草稿', '已驳回', '待审批'] as const
    const results = await Promise.all(types.flatMap((type) => statuses.map((status) =>
      getTransfers({ type, status, mine: true, page: 1, pageSize: 50 }),
    )))
    documents.value = results
      .flatMap((result) => result.data.results ?? [])
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

function editDocument(doc: Transfer) {
  if (doc.actionType === 'return') return
  const type = (doc.actionType || 'transfer') as ActiveTransferActionType
  const path = mobileCreatePaths[type]
  if (!path || !canManageTransfer(type, code => userStore.can(code)) || doc.canEditDraft !== true) return
  router.push({ path, query: { id: doc.id } })
}

function canEditDocument(doc: Transfer) {
  if (doc.actionType === 'return') return false
  const type = (doc.actionType || 'transfer') as ActiveTransferActionType
  return Boolean(mobileCreatePaths[type])
    && canManageTransfer(type, code => userStore.can(code))
    && doc.canEditDraft === true
}

function canSubmitDocument(doc: Transfer) {
  if (doc.actionType === 'return') return false
  const type = (doc.actionType || 'transfer') as ActiveTransferActionType
  return doc.审批状态 === '草稿'
    && canManageTransfer(type, code => userStore.can(code))
    && doc.canEditDraft === true
}

function canDeleteDocument(doc: Transfer) {
  if (doc.actionType === 'return') return false
  const type = (doc.actionType || 'transfer') as ActiveTransferActionType
  return doc.审批状态 === '草稿'
    && userStore.can(TRANSFER_PERMISSION_OPERATIONS[type].view)
    && userStore.can(TRANSFER_PERMISSION_OPERATIONS[type].deleteDraft)
    && doc.canEditDraft === true
}

function canWithdrawDocument(doc: Transfer) {
  if (doc.actionType === 'return') return false
  const type = (doc.actionType || 'transfer') as ActiveTransferActionType
  return doc.审批状态 === '待审批'
    && canManageTransfer(type, code => userStore.can(code))
    && doc.canWithdraw === true
}

async function submitDraft(doc: Transfer) {
  if (doc.actionType === 'return') return
  const type = (doc.actionType || 'transfer') as ActiveTransferActionType
  if (!canManageTransfer(type, code => userStore.can(code)) || doc.canEditDraft !== true) return
  try {
    await submitTransfer(doc.id)
    ElMessage.success('已提交审批')
    await fetchDocuments()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

async function withdrawDraft(doc: Transfer) {
  if (doc.actionType === 'return') return
  const type = (doc.actionType || 'transfer') as ActiveTransferActionType
  if (!canManageTransfer(type, code => userStore.can(code)) || doc.canWithdraw !== true) return
  try {
    await ElMessageBox.confirm('撤回后单据回到草稿，可修改后重新提交', '确认撤回？', {
      confirmButtonText: '撤回',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await withdrawTransfer(doc.id)
    ElMessage.success('已撤回为草稿')
    await fetchDocuments()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(handleApiError(error))
  }
}

async function deleteDraft(doc: Transfer) {
  if (!canDeleteDocument(doc)) return
  const number = doc.单据编号 || doc.id.slice(0, 8)
  try {
    await ElMessageBox.confirm(
      `删除草稿 ${number} 后无法恢复，确认删除？`,
      '删除草稿',
      { confirmButtonText: '删除草稿', cancelButtonText: '保留草稿', type: 'warning' },
    )
    await deleteTransferDraft(doc.id)
    ElMessage.success('草稿已删除')
    await fetchDocuments()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(handleApiError(error))
  }
}

onMounted(fetchDocuments)
</script>

<template>
  <div class="my-transfers-page">
    <header class="page-header">
      <h1>我的申请</h1>
      <button class="refresh-btn" aria-label="刷新" title="刷新" :disabled="loading" @click="fetchDocuments">↻</button>
    </header>

    <div class="status-tabs" role="tablist" aria-label="单据状态">
      <button :class="{ active: activeStatus === '草稿' }" role="tab" :aria-selected="activeStatus === '草稿'" @click="activeStatus = '草稿'">草稿</button>
      <button :class="{ active: activeStatus === '已驳回' }" role="tab" :aria-selected="activeStatus === '已驳回'" @click="activeStatus = '已驳回'">已驳回</button>
      <button :class="{ active: activeStatus === '待审批' }" role="tab" :aria-selected="activeStatus === '待审批'" @click="activeStatus = '待审批'">待审批</button>
    </div>

    <div v-if="loading" class="state-message">加载中...</div>
    <div v-else-if="visibleDocuments.length" class="document-list">
      <article v-for="doc in visibleDocuments" :key="doc.id" class="document-row">
        <div class="document-main">
          <div class="document-title">
            <span>{{ typeLabels[doc.actionType || 'transfer'] }}</span>
            <span class="document-number">{{ doc.单据编号 || doc.id.slice(0, 8) }}</span>
          </div>
          <div class="document-summary">{{ transferDocSummary(doc).name }} · {{ transferDocSummary(doc).qty }} 件</div>
          <div class="document-date">{{ doc.updatedAt?.slice(0, 10) || doc.调拨日期 || '-' }}</div>
        </div>
        <div v-if="canEditDocument(doc) || canSubmitDocument(doc) || canWithdrawDocument(doc) || canDeleteDocument(doc)" class="document-actions">
          <button v-if="canEditDocument(doc)" class="edit-btn" @click="editDocument(doc)">{{ doc.审批状态 === '草稿' ? '继续编辑' : '修改并重提' }}</button>
          <button v-if="canSubmitDocument(doc)" class="submit-btn" @click="submitDraft(doc)">提交</button>
          <button v-if="canWithdrawDocument(doc)" class="withdraw-btn" @click="withdrawDraft(doc)">撤回</button>
          <button v-if="canDeleteDocument(doc)" class="delete-btn" @click="deleteDraft(doc)">删除草稿</button>
        </div>
        <span v-else class="permission-note">当前账号没有此单据的可操作权限</span>
      </article>
    </div>
    <div v-else class="state-message">暂无{{ activeStatus }}单据</div>
  </div>
</template>

<style scoped>
.my-transfers-page { min-height: 100%; padding: var(--space-4); }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.page-header h1 { margin: 0; font-size: 20px; font-weight: 600; color: var(--color-text-primary); }
.refresh-btn { width: 40px; height: 40px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-secondary); font-size: 22px; cursor: pointer; }
.refresh-btn:disabled { opacity: .5; cursor: wait; }
.status-tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; padding: 4px; margin-bottom: var(--space-4); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-elevated); }
.status-tabs button { height: 38px; border: 0; border-radius: 6px; background: transparent; color: var(--color-text-secondary); font-size: 14px; cursor: pointer; }
.status-tabs button.active { background: var(--color-bg-card); color: var(--color-primary-600); box-shadow: 0 1px 2px rgb(0 0 0 / 8%); }
.document-list { display: flex; flex-direction: column; gap: var(--space-3); }
.document-row { padding: var(--space-4); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); }
.document-title { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--space-2); color: var(--color-text-primary); font-size: 14px; font-weight: 600; }
.document-number { color: var(--color-text-tertiary); font: 12px var(--font-mono); }
.document-summary { margin-top: var(--space-2); overflow: hidden; color: var(--color-text-secondary); font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
.document-date { margin-top: var(--space-1); color: var(--color-text-tertiary); font-size: 12px; }
.document-actions { display: flex; gap: var(--space-2); margin-top: var(--space-3); }
.document-actions button { flex: 1; height: 40px; border-radius: 6px; font-size: 14px; cursor: pointer; }
.edit-btn { border: 1px solid var(--color-border); background: var(--color-bg-card); color: var(--color-text-primary); }
.submit-btn { border: 1px solid var(--color-primary-500); background: var(--color-primary-500); color: #fff; }
.withdraw-btn { border: 1px solid var(--color-warning); background: var(--color-bg-card); color: var(--color-warning); }
.delete-btn { border: 1px solid var(--color-danger); background: var(--color-bg-card); color: var(--color-danger); }
.permission-note { display: block; margin-top: var(--space-3); color: var(--color-text-tertiary); font-size: 12px; }
.state-message { padding: var(--space-8) var(--space-4); color: var(--color-text-tertiary); text-align: center; font-size: 14px; }
</style>
