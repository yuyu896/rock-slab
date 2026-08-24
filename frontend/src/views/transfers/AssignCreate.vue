<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { draftsToItems, emptyDraft, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { assignAsset } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'

const router = useRouter()
const creating = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({ 调拨日期: '', fromBranch: '', 备注: '' })
const lines = ref<LineDraft[]>([emptyDraft()])
const linesEditor = ref<InstanceType<typeof TransferLinesEditor> | null>(null)

onMounted(async () => {
  try {
    const { data } = await getBranches()
    branchOptions.value = data.map((b: any) => ({ value: b.id, label: b.name }))
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
})

function goBack() {
  router.replace('/transfers/assign')
}

async function submit() {
  const f = form.value
  if (!f.调拨日期 || !f.fromBranch) {
    ElMessage.warning('请填写日期与所属分公司')
    return
  }
  const items = draftsToItems(lines.value)
  if (items.length === 0 || !linesEditor.value?.validate()) {
    ElMessage.warning('每行请选择品目并填写数量（≥1）')
    return
  }
  creating.value = true
  try {
    // 一次请求提交整张多行单据（原先逐行 N 请求的 workaround 已转正为明细行）
    await assignAsset({
      调拨日期: f.调拨日期,
      fromBranch: f.fromBranch,
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
  <TransferCreateLayout title="新建领用出库" :loading="creating" @submit="submit" @back="goBack">
    <div class="form-grid">
      <div class="form-item"><label class="form-label">日期 <span class="required">*</span></label><input v-model="form.调拨日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">所属分公司 <span class="required">*</span></label>
        <select v-model="form.fromBranch" class="form-select">
          <option value="">请选择分公司</option>
          <option v-for="b in branchOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </div>
    </div>

    <TransferLinesEditor ref="linesEditor" v-model="lines" type="assign" :branch-id="form.fromBranch" />

    <div class="form-item full remark-item"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
  </TransferCreateLayout>
</template>

<style scoped>
.remark-item { margin-top: var(--space-4); }
</style>
