<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { draftsToItems, emptyDraft, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { transferAsset } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import DepartmentSelect from '@/components/DepartmentSelect.vue'

const router = useRouter()
const creating = ref(false)
/** 调出=授权范围（扣数方收口）；调入=全量（单边化设计，调入方不要求授权） */
const fromBranchOptions = ref<{ value: string; label: string }[]>([])
const toBranchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({
  调拨日期: '',
  fromBranch: '', toBranch: '',
  调出部门: '', 调入部门: '',
  调出负责人: '', 调入负责人: '', 调拨原因: '', 备注: '',
})
const lines = ref<LineDraft[]>([emptyDraft()])
const linesEditor = ref<InstanceType<typeof TransferLinesEditor> | null>(null)
const fromBranchName = computed(
  () => fromBranchOptions.value.find((b: any) => b.value === form.value.fromBranch)?.label || '',
)

onMounted(async () => {
  try {
    const [scoped, all] = await Promise.all([
      getBranches({ scope: 'write' }),
      getBranches(),
    ])
    fromBranchOptions.value = scoped.data.map((b: any) => ({ value: b.id, label: b.name }))
    toBranchOptions.value = all.data.map((b: any) => ({ value: b.id, label: b.name }))
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
})

function goBack() {
  router.replace('/transfers/transfer')
}

async function submit() {
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
    await transferAsset({
      调拨日期: f.调拨日期,
      fromBranch: f.fromBranch,
      toBranch: f.toBranch,
      调出部门: f.调出部门,
      调入部门: f.调入部门,
      调出负责人: f.调出负责人,
      调入负责人: f.调入负责人,
      调拨原因: f.调拨原因,
      备注: f.备注,
      items,
    })
    ElMessage.success('提交成功')
    goBack()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <TransferCreateLayout title="新建调拨" :loading="creating" @submit="submit" @back="goBack">
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
      <div class="form-item"><label class="form-label">调出负责人</label><input v-model="form.调出负责人" type="text" class="form-input" /></div>
      <div class="form-item"><label class="form-label">调入负责人</label><input v-model="form.调入负责人" type="text" class="form-input" /></div>
      <div class="form-item"><label class="form-label">调出部门</label><DepartmentSelect v-model="form.调出部门" :branch-id="form.fromBranch" /></div>
      <div class="form-item"><label class="form-label">调入部门</label><DepartmentSelect v-model="form.调入部门" :branch-id="form.toBranch" /></div>
      <div class="form-item full"><label class="form-label">调拨原因</label><input v-model="form.调拨原因" type="text" class="form-input" /></div>
    </div>

    <TransferLinesEditor ref="linesEditor" v-model="lines" type="transfer" :branch-name="fromBranchName" />

    <div class="form-item full remark-item"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
  </TransferCreateLayout>
</template>

<style scoped>
.remark-item { margin-top: var(--space-4); }
</style>
