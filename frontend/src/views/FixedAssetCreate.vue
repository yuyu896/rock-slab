<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createFixedAsset } from '@/api/assets'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import TransferCreateLayout from './transfers/components/TransferCreateLayout.vue'

const router = useRouter()
const creating = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])
const createForm = ref({
  分公司: '',
  资产编号: '',
  分公司编号: '',
  序列号: '',
  供应商: '',
  物品分类: '',
  资产名称: '',
  入库日期: '',
  是否租用: false,
  数量: 1,
  规格: '',
  单价: 0,
  购入金额: 0,
  出库日期: '',
  所属部门: '',
  使用人: '',
  当前状态: '在库',
  备注: '',
})

async function fetchBranches() {
  try {
    const { data } = await getBranches()
    branchOptions.value = data.map((b: any) => ({ value: b.name, label: b.name }))
  } catch (error) {
    console.error('Failed to fetch branches:', error)
  }
}

function goBack() {
  router.replace('/fixed-assets')
}

async function submitCreate() {
  const f = createForm.value
  if (!f.分公司) {
    ElMessage.warning('请选择分公司')
    return
  }
  if (!f.资产编号) {
    ElMessage.warning('请填写资产编号')
    return
  }
  if (!f.资产名称) {
    ElMessage.warning('请填写资产名称')
    return
  }
  if (!f.序列号) {
    ElMessage.warning('请填写电脑序列号')
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

onMounted(() => {
  fetchBranches()
})
</script>

<template>
  <TransferCreateLayout title="新增固定资产" :loading="creating" submit-text="确定" @submit="submitCreate" @back="goBack">
    <div class="form-grid">
      <div class="form-item">
        <label class="form-label">分公司 <span class="required">*</span></label>
        <select v-model="createForm.分公司" class="form-select">
          <option value="">请选择分公司</option>
          <option v-for="b in branchOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
        </select>
      </div>
      <div class="form-item">
        <label class="form-label">资产编号 <span class="required">*</span></label>
        <input v-model="createForm.资产编号" type="text" class="form-input" placeholder="资产编号需已存在于资产品目中" />
      </div>
      <div class="form-item"><label class="form-label">分公司编号</label><input v-model="createForm.分公司编号" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">电脑序列号 <span class="required">*</span></label><input v-model="createForm.序列号" type="text" class="form-input" placeholder="请输入电脑序列号" /></div>
      <div class="form-item"><label class="form-label">供应商</label><input v-model="createForm.供应商" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">物品分类</label><input v-model="createForm.物品分类" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">资产名称 <span class="required">*</span></label><input v-model="createForm.资产名称" type="text" class="form-input" placeholder="请输入资产名称" /></div>
      <div class="form-item"><label class="form-label">入库日期</label><input v-model="createForm.入库日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">是否租用</label>
        <div class="form-toggle">
          <label><input type="radio" :value="false" v-model="createForm.是否租用" /> 自购</label>
          <label><input type="radio" :value="true" v-model="createForm.是否租用" /> 租用</label>
        </div>
      </div>
      <div class="form-item"><label class="form-label">数量</label><input v-model.number="createForm.数量" type="number" class="form-input" min="1" /></div>
      <div class="form-item"><label class="form-label">规格</label><input v-model="createForm.规格" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">单价</label><input v-model.number="createForm.单价" type="number" class="form-input" min="0" step="0.01" /></div>
      <div class="form-item"><label class="form-label">购入金额</label><input v-model.number="createForm.购入金额" type="number" class="form-input" min="0" step="0.01" /></div>
      <div class="form-item"><label class="form-label">出库日期</label><input v-model="createForm.出库日期" type="date" class="form-input" /></div>
      <div class="form-item"><label class="form-label">所属部门</label><input v-model="createForm.所属部门" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item"><label class="form-label">使用人</label><input v-model="createForm.使用人" type="text" class="form-input" placeholder="选填" /></div>
      <div class="form-item">
        <label class="form-label">状态</label>
        <select v-model="createForm.当前状态" class="form-select">
          <option value="在库">在库</option>
          <option value="在用">在用</option>
          <option value="空闲">空闲</option>
        </select>
      </div>
      <div class="form-item full"><label class="form-label">备注</label><textarea v-model="createForm.备注" class="form-textarea" rows="2" placeholder="选填"></textarea></div>
    </div>
  </TransferCreateLayout>
</template>

<style scoped>
.form-toggle { display: flex; gap: 16px; padding: 8px 0; }
.form-toggle label { display: flex; align-items: center; gap: 4px; font-size: 14px; cursor: pointer; }
</style>
