<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { draftsFromLines, draftsToItems, emptyDraft, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { getTransfer, purchaseAsset, resubmitTransfer, submitTransfer, updateTransfer } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { sortBranchesByName } from '@/utils/sortBranchesByName'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import DepartmentSelect from '@/components/DepartmentSelect.vue'
import { useUserStore } from '@/store/user'
import { canManageTransfer } from '@/utils/permissionGroups'
import BranchSelect from '@/components/BranchSelect.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const canCreate = computed(() => canManageTransfer('purchase', code => userStore.can(code)))
const canEdit = computed(() => canManageTransfer('purchase', code => userStore.can(code)))
const canSubmit = computed(() => canManageTransfer('purchase', code => userStore.can(code)))
const creating = ref(false)
const loadingExisting = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({ 调拨日期: '', toBranch: '', 需求部门: '', 经办人: userStore.profile?.name || '', 备注: '' })
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

onMounted(async () => {
  try {
    // 入库分公司收口到授权范围（无参全量的防线在提交端校验，见 scope=write 语义）
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
    ElMessage.warning('当前账号无权编辑采购入库单')
    router.replace('/transfers/purchase')
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
      toBranch: data.to_branch || branchOptions.value.find((b) => b.label === data.调入分公司)?.value || '',
      需求部门: data.需求部门 || '',
      经办人: data.经办人 || userStore.profile?.name || '',
      备注: data.备注 || '',
    }
    lines.value = draftsFromLines(data.lines || [])
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loadingExisting.value = false
  }
}

function goBack() {
  router.replace('/transfers/purchase')
}

async function submit(asDraft = false) {
  const editing = Boolean(requestedEditId)
  if (editing ? !canEdit.value : !canCreate.value) {
    ElMessage.warning(editing ? '当前账号无权编辑采购入库单' : '当前账号无权创建采购入库单')
    return
  }
  if (!asDraft && !editing && !canSubmit.value) {
    ElMessage.warning('当前账号无权提交采购入库单')
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
  if (!f.调拨日期 || !f.toBranch) {
    ElMessage.warning('请填写日期与入库分公司')
    return
  }
  const items = draftsToItems(lines.value)
  if (items.length === 0 || !linesEditor.value?.validate()) {
    ElMessage.warning('每行请选择品目并填写数量（≥1）')
    return
  }
  creating.value = true
  try {
    const payload = {
      调拨日期: f.调拨日期,
      toBranch: f.toBranch,
      需求部门: f.需求部门,
      经办人: f.经办人,
      备注: f.备注,
      items,
    }
    if (editingId.value) {
      await updateTransfer(editingId.value, payload)
      if (!asDraft && canSubmit.value) {
        await (editingStatus.value === '已驳回' ? resubmitTransfer(editingId.value) : submitTransfer(editingId.value))
      }
    } else {
      await purchaseAsset({ ...payload, draft: asDraft || undefined })
    }
    ElMessage.success(editingId.value && !canSubmit.value ? '已保存修改' : asDraft ? '已存为草稿' : editingStatus.value === '已驳回' ? '已修改并重新提交' : '提交成功')
    goBack()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <TransferCreateLayout :title="editingId ? '编辑采购入库' : '新建采购入库'" :submit-text="primaryActionText" :loading="creating" :submit-disabled="loadingExisting || Boolean(requestedEditId && !editingId)" :show-submit="showPrimaryAction" @submit="submit(false)" @back="goBack">
    <template #footer-extra>
      <button v-if="showDraftAction" class="btn-draft" :disabled="creating || loadingExisting || editingStatus === '已驳回'" @click="submit(true)">存为草稿</button>
    </template>
    <div class="form-grid">
      <div class="form-item"><label class="form-label">日期 <span class="required">*</span></label><input v-model="form.调拨日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">入库分公司 <span class="required">*</span></label>
        <BranchSelect v-model="form.toBranch" :options="branchOptions" placeholder="请选择分公司" />
      </div>
      <div class="form-item"><label class="form-label">需求部门</label><DepartmentSelect v-model="form.需求部门" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">经办人</label><input v-model="form.经办人" type="text" class="form-input" placeholder="默认创建人，选填" /></div>
      <div class="form-item full"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
    </div>

    <TransferLinesEditor ref="linesEditor" v-model="lines" type="purchase" />
  </TransferCreateLayout>
</template>

<style scoped>
/* 存为草稿（插槽内容不吃布局组件的 scoped 样式，此处复刻次级按钮外观） */
.btn-draft { height: 40px; padding: 0 var(--space-5); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.btn-draft:hover { border-color: var(--color-primary-300); }
.btn-draft:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
