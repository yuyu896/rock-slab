<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { transferAsset } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'

const router = useRouter()
const creating = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({
  调拨日期: '', 资产编号: '', 资产名称: '', 调拨数量: 1,
  fromBranch: '', toBranch: '',
  调出部门: '', 调入部门: '',
  调出负责人: '', 调入负责人: '', 调拨原因: '', 备注: '',
})

onMounted(async () => {
  try {
    const { data } = await getBranches()
    branchOptions.value = data.map((b: any) => ({ value: b.id, label: b.name }))
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
})

function goBack() {
  router.replace('/transfers/transfer')
}

async function submit() {
  const f = form.value
  if (!f.调拨日期 || !f.资产编号 || !f.资产名称 || !f.调拨数量) {
    ElMessage.warning('请填写必填字段')
    return
  }
  if (f.fromBranch && f.toBranch && f.fromBranch === f.toBranch) {
    ElMessage.warning('调出与调入分公司不能相同')
    return
  }
  creating.value = true
  try {
    await transferAsset({ ...f })
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
      <div class="form-item"><label class="form-label">资产编号 <span class="required">*</span></label><input v-model="form.资产编号" type="text" class="form-input" placeholder="请输入资产编号" /></div>
      <div class="form-item"><label class="form-label">资产名称 <span class="required">*</span></label><input v-model="form.资产名称" type="text" class="form-input" placeholder="请输入资产名称" /></div>
      <div class="form-item"><label class="form-label">数量 <span class="required">*</span></label><input v-model.number="form.调拨数量" type="number" class="form-input" min="1" /></div>
      <div class="form-item">
        <label class="form-label">调出分公司 <span class="required">*</span></label>
        <select v-model="form.fromBranch" class="form-select">
          <option value="">请选择</option>
          <option v-for="b in branchOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </div>
      <div class="form-item">
        <label class="form-label">调入分公司 <span class="required">*</span></label>
        <select v-model="form.toBranch" class="form-select">
          <option value="">请选择</option>
          <option v-for="b in branchOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </div>
      <div class="form-item"><label class="form-label">调出部门</label><input v-model="form.调出部门" type="text" class="form-input" /></div>
      <div class="form-item"><label class="form-label">调入部门</label><input v-model="form.调入部门" type="text" class="form-input" /></div>
      <div class="form-item"><label class="form-label">调出负责人</label><input v-model="form.调出负责人" type="text" class="form-input" /></div>
      <div class="form-item"><label class="form-label">调入负责人</label><input v-model="form.调入负责人" type="text" class="form-input" /></div>
      <div class="form-item full"><label class="form-label">调拨原因</label><input v-model="form.调拨原因" type="text" class="form-input" /></div>
      <div class="form-item full"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
    </div>
  </TransferCreateLayout>
</template>
