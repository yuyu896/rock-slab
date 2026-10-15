<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { draftsFromLines, draftsToItems, emptyDraft, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { getTransfer, resubmitTransfer, submitTransfer, transferAsset, updateTransfer } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { sortBranchesByName } from '@/utils/sortBranchesByName'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import DepartmentSelect from '@/components/DepartmentSelect.vue'
import { useUserStore } from '@/store/user'
import { getUsers } from '@/api/users'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const creating = ref(false)
/** 调出=授权范围（扣数方收口）；调入=全量（单边化设计，调入方不要求授权） */
const fromBranchOptions = ref<{ value: string; label: string }[]>([])
const toBranchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({
  调拨日期: '',
  fromBranch: '', toBranch: '',
  调出部门: '', 调入部门: '',
  调入负责人: '', 经办人: userStore.profile?.name || '', 调拨原因: '', 备注: '',
})
const lines = ref<LineDraft[]>([emptyDraft()])
const linesEditor = ref<InstanceType<typeof TransferLinesEditor> | null>(null)
const editingId = ref<string | null>(null)
const editingStatus = ref<'草稿' | '已驳回' | null>(null)
const requestedEditId = typeof route.query.id === 'string' ? route.query.id : ''
const fromBranchName = computed(
  () => fromBranchOptions.value.find((b: any) => b.value === form.value.fromBranch)?.label || '',
)

/** 调入负责人纯下拉：选项=调入分公司员工（员工即系统账号）；切换公司清空重拉 */
const toBranchUserOptions = ref<string[]>([])
const loadingExisting = ref(false)
watch(() => form.value.toBranch, async (branchId) => {
  if (!loadingExisting.value) form.value.调入负责人 = ''
  toBranchUserOptions.value = []
  if (!branchId) return
  try {
    const { data } = await getUsers({ branch: branchId })
    toBranchUserOptions.value = data
      .map((u: any) => u.name)
      .filter(Boolean)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}, { flush: 'sync' })

onMounted(async () => {
  try {
    const [scoped, all] = await Promise.all([
      getBranches({ scope: 'write' }),
      getBranches(),
    ])
    fromBranchOptions.value = sortBranchesByName(scoped.data.map((b: any) => ({ value: b.id, label: b.name })))
    toBranchOptions.value = sortBranchesByName(all.data.map((b: any) => ({ value: b.id, label: b.name })))
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
    loadingExisting.value = true
    form.value = {
      调拨日期: data.调拨日期 || '',
      fromBranch: data.from_branch || fromBranchOptions.value.find((b) => b.label === data.调出分公司)?.value || '',
      toBranch: data.to_branch || toBranchOptions.value.find((b) => b.label === data.调入分公司)?.value || '',
      调出部门: data.调出部门 || '',
      调入部门: data.调入部门 || '',
      调入负责人: data.调入负责人 || '',
      经办人: data.经办人 || userStore.profile?.name || '',
      调拨原因: data.调拨原因 || '',
      备注: data.备注 || '',
    }
    loadingExisting.value = false
    lines.value = draftsFromLines(data.lines || [])
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

function goBack() {
  router.replace('/transfers/transfer')
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
  if (!f.调拨日期 || !f.fromBranch || !f.toBranch) {
    ElMessage.warning('请填写日期与调出/调入分公司')
    return
  }
  if (f.fromBranch === f.toBranch) {
    ElMessage.warning('调出与调入分公司不能相同')
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
      fromBranch: f.fromBranch,
      toBranch: f.toBranch,
      调出部门: f.调出部门,
      调入部门: f.调入部门,
      调入负责人: f.调入负责人,
      经办人: f.经办人,
      调拨原因: f.调拨原因,
      备注: f.备注,
      items,
    }
    if (editingId.value) {
      await updateTransfer(editingId.value, payload)
      if (!asDraft) {
        await (editingStatus.value === '已驳回' ? resubmitTransfer(editingId.value) : submitTransfer(editingId.value))
      }
    } else {
      await transferAsset({ ...payload, draft: asDraft || undefined })
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
  <TransferCreateLayout :title="editingId ? '编辑调拨' : '新建调拨'" :loading="creating" @submit="submit(false)" @back="goBack">
    <template #footer-extra>
      <button class="btn-draft" :disabled="creating || editingStatus === '已驳回'" @click="submit(true)">保存为草稿</button>
    </template>
    <div class="form-grid">
      <div class="form-item"><label class="form-label">调拨日期 <span class="required">*</span></label><input v-model="form.调拨日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">调出分公司 <span class="required">*</span></label>
        <select v-model="form.fromBranch" class="form-select">
          <option value="">请选择</option>
          <option v-for="b in fromBranchOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </div>
      <div class="form-item">
        <label class="form-label">调入分公司 <span class="required">*</span></label>
        <select v-model="form.toBranch" class="form-select">
          <option value="">请选择</option>
          <option v-for="b in toBranchOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </div>
      <div class="form-item">
        <label class="form-label">调入负责人</label>
        <select v-model="form.调入负责人" class="form-select" :disabled="!form.toBranch">
          <option value="">{{ form.toBranch ? '请选择' : '请先选调入分公司' }}</option>
          <option v-for="name in toBranchUserOptions" :key="name" :value="name">{{ name }}</option>
        </select>
      </div>
      <div class="form-item"><label class="form-label">经办人</label><input v-model="form.经办人" type="text" class="form-input" placeholder="默认创建人，选填" /></div>
      <div class="form-item"><label class="form-label">调出部门</label><DepartmentSelect v-model="form.调出部门" /></div>
      <div class="form-item"><label class="form-label">调入部门</label><DepartmentSelect v-model="form.调入部门" /></div>
      <div class="form-item full"><label class="form-label">调拨原因</label><input v-model="form.调拨原因" type="text" class="form-input" /></div>
    </div>

    <TransferLinesEditor ref="linesEditor" v-model="lines" type="transfer" :branch-name="fromBranchName" />

    <div class="form-item full remark-item"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
  </TransferCreateLayout>
</template>

<style scoped>
.remark-item { margin-top: var(--space-4); }
.btn-draft { height: 40px; padding: 0 var(--space-5); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.btn-draft:disabled { opacity: .6; cursor: not-allowed; }
</style>
