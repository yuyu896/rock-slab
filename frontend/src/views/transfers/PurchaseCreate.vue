<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { draftsToItems, emptyDraft, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { purchaseAsset } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import DepartmentSelect from '@/components/DepartmentSelect.vue'

const router = useRouter()
const creating = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({ 调拨日期: '', toBranch: '', 供应商: '', 需求部门: '', 采购经办人: '', 备注: '' })
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
  router.replace('/transfers/purchase')
}

async function submit() {
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
    await purchaseAsset({
      调拨日期: f.调拨日期,
      toBranch: f.toBranch,
      供应商: f.供应商,
      需求部门: f.需求部门,
      采购经办人: f.采购经办人,
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
  <TransferCreateLayout title="新建采购入库" :loading="creating" @submit="submit" @back="goBack">
    <div class="form-grid">
      <div class="form-item"><label class="form-label">日期 <span class="required">*</span></label><input v-model="form.调拨日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">入库分公司 <span class="required">*</span></label>
        <select v-model="form.toBranch" class="form-select">
          <option value="">请选择分公司</option>
          <option v-for="b in branchOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </div>
      <div class="form-item"><label class="form-label">供应商</label><input v-model="form.供应商" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">需求部门</label><DepartmentSelect v-model="form.需求部门" :branch-id="form.toBranch" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">采购经办人</label><input v-model="form.采购经办人" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item full"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
    </div>

    <TransferLinesEditor ref="linesEditor" v-model="lines" type="purchase" />
  </TransferCreateLayout>
</template>
