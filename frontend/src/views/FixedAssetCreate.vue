<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { createFixedAsset } from '@/api/assets'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import TransferCreateLayout from './transfers/components/TransferCreateLayout.vue'

const router = useRouter()
const creating = ref(false)
const createForm = ref({
  资产编号: '',
  序列号: '',
  供应商: '',
  入库日期: '',
  使用人: '',
  所属部门: '',
  当前状态: '在库',
  备注: '',
})

function goBack() {
  router.replace('/fixed-assets')
}

async function submitCreate() {
  const f = createForm.value
  if (!f.资产编号) {
    ElMessage.warning('请填写资产编号')
    return
  }
  creating.value = true
  try {
    await createFixedAsset(f)
    ElMessage.success('创建成功')
    goBack()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <TransferCreateLayout title="新增固定资产" :loading="creating" submit-text="确定" @submit="submitCreate" @back="goBack">
    <div class="form-grid">
      <div class="form-item full">
        <label class="form-label">资产编号 <span class="required">*</span></label>
        <input v-model="createForm.资产编号" type="text" class="form-input" placeholder="资产编号需已存在于资产品目中" />
      </div>
      <div class="form-item"><label class="form-label">电脑序列号</label><input v-model="createForm.序列号" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">供应商</label><input v-model="createForm.供应商" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">入库日期</label><input v-model="createForm.入库日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">状态</label>
        <select v-model="createForm.当前状态" class="form-select">
          <option value="在库">在库</option>
          <option value="在用">在用</option>
          <option value="空闲">空闲</option>
        </select>
      </div>
      <div class="form-item"><label class="form-label">使用人</label><input v-model="createForm.使用人" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">所属部门</label><input v-model="createForm.所属部门" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item full"><label class="form-label">备注</label><textarea v-model="createForm.备注" class="form-textarea" rows="2" placeholder="选填"></textarea></div>
    </div>
  </TransferCreateLayout>
</template>
