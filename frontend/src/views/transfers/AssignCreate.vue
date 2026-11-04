<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { draftsFromLines, draftsToItems, emptyDraft, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { assignAsset, getTransfer, resubmitTransfer, submitTransfer, updateTransfer } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { sortBranchesByName } from '@/utils/sortBranchesByName'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import { ASSIGN_SOURCE_OPTIONS } from '@/constants'
import { useUserStore } from '@/store/user'
import { canManageTransfer } from '@/utils/permissionGroups'
import BranchSelect from '@/components/BranchSelect.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const canCreate = computed(() => canManageTransfer('assign', code => userStore.can(code)))
const canEdit = computed(() => canManageTransfer('assign', code => userStore.can(code)))
const canSubmit = computed(() => canManageTransfer('assign', code => userStore.can(code)))
const creating = ref(false)
const loadingExisting = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({ 调拨日期: '', fromBranch: '', 领用来源: 'stock' as 'stock' | 'recycle_bin', 经办人: userStore.profile?.name || '' })
const lines = ref<LineDraft[]>([emptyDraft()])
const linesEditor = ref<InstanceType<typeof TransferLinesEditor> | null>(null)
const editingId = ref<string | null>(null)
const editingStatus = ref<'草稿' | '已驳回' | null>(null)
const requestedEditId = typeof route.query.id === 'string' ? route.query.id : ''
const showDraftAction = computed(() => requestedEditId
  ? canEdit.value && editingStatus.value === '草稿' && canSubmit.value
  : canCreate.value)
const showPrimaryAction = computed(() => requestedEditId
  ? canEdit.value
  : canCreate.value && canSubmit.value)
const primaryActionText = computed(() => requestedEditId && !canSubmit.value
  ? '保存修改'
  : editingStatus.value === '已驳回' ? '保存并重新提交' : editingId.value ? '保存并提交审批' : '确定提交')

const branchName = computed(
  () => branchOptions.value.find((b) => b.value === form.value.fromBranch)?.label || '',
)

onMounted(async () => {
  try {
    // 所属分公司（扣数方）收口到授权范围
    const { data } = await getBranches({ scope: 'write' })
    branchOptions.value = sortBranchesByName(data.map((b: any) => ({ value: b.id, label: b.name })))
    await loadExisting()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
})

async function loadExisting() {
  const id = requestedEditId
  if (!id) return
  if (!canEdit.value) {
    ElMessage.warning('当前账号无权编辑领用出库单')
    router.replace('/transfers/assign')
    return
  }
  loadingExisting.value = true
  try {
    const { data } = await getTransfer(id)
    if (!data.canEditDraft || !['草稿', '已驳回'].includes(data.审批状态)) {
      ElMessage.warning('当前账号无权编辑此单据，或单据状态已变化')
      return
    }
    editingId.value = id
    editingStatus.value = data.审批状态 as '草稿' | '已驳回'
    form.value = {
      调拨日期: data.调拨日期 || '',
      fromBranch: data.from_branch || branchOptions.value.find((b) => b.label === data.调出分公司)?.value || '',
      领用来源: data.领用来源 || 'stock',
      经办人: data.经办人 || userStore.profile?.name || '',
    }
    lines.value = draftsFromLines(data.lines || [])
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loadingExisting.value = false
  }
}

function goBack() {
  router.replace('/transfers/assign')
}

async function submit(asDraft = false) {
  const editing = Boolean(requestedEditId)
  if (editing ? !canEdit.value : !canCreate.value) {
    ElMessage.warning(editing ? '当前账号无权编辑领用出库单' : '当前账号无权创建领用出库单')
    return
  }
  if (!asDraft && !editing && !canSubmit.value) {
    ElMessage.warning('当前账号无权提交领用出库单')
    return
  }
  if (requestedEditId && editingId.value !== requestedEditId) {
    ElMessage.warning('单据未能加载或无权编辑，未执行提交')
    return
  }
  if (asDraft && editingStatus.value === '已驳回') {
    ElMessage.warning('已驳回单据需要修改后重新提交')
    return
  }
  const f = form.value
  if (!f.调拨日期 || !f.fromBranch) {
    ElMessage.warning('请填写日期与所属分公司')
    return
  }
  const items = draftsToItems(lines.value)
  if (items.length === 0 || !linesEditor.value?.validate()) {
    ElMessage.warning('每行请选择品目并填写数量（≥1）、使用人与领用部门；实例管理品目请选满实例')
    return
  }
  creating.value = true
  try {
    const payload = {
      调拨日期: f.调拨日期,
      fromBranch: f.fromBranch,
      领用来源: f.领用来源,
      经办人: f.经办人,
      items,
    }
    if (editingId.value) {
      await updateTransfer(editingId.value, payload)
      if (!asDraft && canSubmit.value) {
        await (editingStatus.value === '已驳回' ? resubmitTransfer(editingId.value) : submitTransfer(editingId.value))
      }
    } else {
      await assignAsset({ ...payload, draft: asDraft || undefined })
    }
    ElMessage.success(editingId.value && !canSubmit.value ? '已保存修改' : asDraft ? '已保存为草稿' : editingStatus.value === '已驳回' ? '已修改并重新提交' : '提交成功')
    goBack()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <TransferCreateLayout :title="editingId ? '编辑领用出库' : '新建领用出库'" :submit-text="primaryActionText" :loading="creating" :submit-disabled="loadingExisting || Boolean(requestedEditId && !editingId)" :show-submit="showPrimaryAction" @submit="submit(false)" @back="goBack">
    <template #footer-extra>
      <button v-if="showDraftAction" class="btn-draft" :disabled="creating || loadingExisting || editingStatus === '已驳回'" @click="submit(true)">保存为草稿</button>
    </template>
    <div class="form-grid">
      <div class="form-item"><label class="form-label">日期 <span class="required">*</span></label><input v-model="form.调拨日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">所属分公司 <span class="required">*</span></label>
        <BranchSelect v-model="form.fromBranch" :options="branchOptions" placeholder="请选择分公司" />
      </div>
      <div class="form-item">
        <label class="form-label">库存来源 <span class="required">*</span></label>
        <select v-model="form.领用来源" class="form-select">
          <option v-for="opt in ASSIGN_SOURCE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <div v-if="form.领用来源 === 'recycle_bin'" class="source-hint">
          回收库来源仅适用于数量/实例管理品目；消耗品行须走新品库（领出即耗用）。
        </div>
      </div>
      <div class="form-item"><label class="form-label">经办人</label><input v-model="form.经办人" type="text" class="form-input" placeholder="默认创建人，选填" /></div>
    </div>

    <TransferLinesEditor
      ref="linesEditor"
      v-model="lines"
      type="assign"
      :branch-id="form.fromBranch"
      :branch-name="branchName"
      :can-view-instances="userStore.can('view_instances')"
      :assign-source="form.领用来源"
    />

  </TransferCreateLayout>
</template>

<style scoped>
.source-hint { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; line-height: 1.5; }
.btn-draft { height: 40px; padding: 0 var(--space-5); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.btn-draft:disabled { opacity: .6; cursor: not-allowed; }
</style>
