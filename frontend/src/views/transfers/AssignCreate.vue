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

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const creating = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({ 调拨日期: '', fromBranch: '', 领用来源: 'stock' as 'stock' | 'recycle_bin', 经办人: userStore.profile?.name || '', 备注: '' })
const lines = ref<LineDraft[]>([emptyDraft()])
const linesEditor = ref<InstanceType<typeof TransferLinesEditor> | null>(null)
const editingId = ref<string | null>(null)
const editingStatus = ref<'草稿' | '已驳回' | null>(null)
const requestedEditId = typeof route.query.id === 'string' ? route.query.id : ''

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
      备注: data.备注 || '',
    }
    lines.value = draftsFromLines(data.lines || [])
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

function goBack() {
  router.replace('/transfers/assign')
}

async function submit(asDraft = false) {
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
      备注: f.备注,
      items,
    }
    if (editingId.value) {
      await updateTransfer(editingId.value, payload)
      if (!asDraft) {
        await (editingStatus.value === '已驳回' ? resubmitTransfer(editingId.value) : submitTransfer(editingId.value))
      }
    } else {
      await assignAsset({ ...payload, draft: asDraft || undefined })
    }
    ElMessage.success(asDraft && editingStatus.value !== '已驳回' ? '已保存为草稿' : editingStatus.value === '已驳回' ? '已修改并重新提交' : asDraft ? '已保存为草稿' : '提交成功')
    goBack()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <TransferCreateLayout :title="editingId ? '编辑领用出库' : '新建领用出库'" :loading="creating" @submit="submit(false)" @back="goBack">
    <template #footer-extra>
      <button class="btn-draft" :disabled="creating || editingStatus === '已驳回'" @click="submit(true)">保存为草稿</button>
    </template>
    <div class="form-grid">
      <div class="form-item"><label class="form-label">日期 <span class="required">*</span></label><input v-model="form.调拨日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">所属分公司 <span class="required">*</span></label>
        <select v-model="form.fromBranch" class="form-select">
          <option value="">请选择分公司</option>
          <option v-for="b in branchOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
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
      :assign-source="form.领用来源"
    />

    <div class="form-item full remark-item"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
  </TransferCreateLayout>
</template>

<style scoped>
.remark-item { margin-top: var(--space-4); }
.source-hint { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; line-height: 1.5; }
.btn-draft { height: 40px; padding: 0 var(--space-5); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.btn-draft:disabled { opacity: .6; cursor: not-allowed; }
</style>
