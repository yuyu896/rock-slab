<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { recoverAsset } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'

const RECOVERY_CATEGORIES = ['闲置回收', '报废回收', '捐赠回收', '其他']

const router = useRouter()
const creating = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])
const form = ref({
  调拨日期: '', 资产编号: '', 资产类目: '', 物品分类: '', 资产名称: '',
  回收分类: '', 调拨数量: 1, 单位: '', 规格型号: '', 出库日期: '',
  调出分公司: '', 调出部门: '', 存放位置: '', 采购经办人: '', 备注: '',
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
  router.replace('/transfers/recovery')
}

async function submit() {
  const f = form.value
  if (!f.调拨日期 || !f.资产编号 || !f.资产名称) {
    ElMessage.warning('请填写必填字段')
    return
  }
  creating.value = true
  try {
    await recoverAsset({
      调拨日期: f.调拨日期,
      资产编号: f.资产编号,
      资产名称: f.资产名称,
      资产类目: f.资产类目,
      物品分类: f.物品分类,
      回收分类: f.回收分类,
      调拨数量: f.调拨数量,
      单位: f.单位,
      规格型号: f.规格型号,
      出库日期: f.出库日期 || undefined,
      调出分公司: f.调出分公司,
      调出部门: f.调出部门,
      存放位置: f.存放位置,
      采购经办人: f.采购经办人,
      备注: f.备注,
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
  <TransferCreateLayout title="新建回收记录" :loading="creating" @submit="submit" @back="goBack">
    <div class="form-grid">
      <div class="form-item"><label class="form-label">入库日期 <span class="required">*</span></label><input v-model="form.调拨日期" type="date" class="form-input" /></div>
      <div class="form-item"><label class="form-label">资产编号 <span class="required">*</span></label><input v-model="form.资产编号" type="text" class="form-input" placeholder="请输入资产编号" /></div>
      <div class="form-item"><label class="form-label">资产名称 <span class="required">*</span></label><input v-model="form.资产名称" type="text" class="form-input" placeholder="请输入资产名称" /></div>
      <div class="form-item">
        <label class="form-label">回收分类 <span class="required">*</span></label>
        <select v-model="form.回收分类" class="form-select">
          <option value="">请选择</option>
          <option v-for="cat in RECOVERY_CATEGORIES" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>
      <div class="form-item"><label class="form-label">资产类目</label><input v-model="form.资产类目" type="text" class="form-input" placeholder="如：固定资产类" /></div>
      <div class="form-item"><label class="form-label">物品分类</label><input v-model="form.物品分类" type="text" class="form-input" placeholder="如：办公设备" /></div>
      <div class="form-item"><label class="form-label">数量</label><input v-model.number="form.调拨数量" type="number" class="form-input" min="1" /></div>
      <div class="form-item"><label class="form-label">单位</label><input v-model="form.单位" type="text" class="form-input" placeholder="如：台、个" /></div>
      <div class="form-item"><label class="form-label">规格</label><input v-model="form.规格型号" type="text" class="form-input" /></div>
      <div class="form-item"><label class="form-label">出库日期</label><input v-model="form.出库日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">分公司</label>
        <select v-model="form.调出分公司" class="form-select">
          <option value="">请选择</option>
          <option v-for="b in branchOptions" :key="b.value" :value="b.label">{{ b.label }}</option>
        </select>
      </div>
      <div class="form-item"><label class="form-label">所属部门</label><input v-model="form.调出部门" type="text" class="form-input" /></div>
      <div class="form-item"><label class="form-label">存放位置</label><input v-model="form.存放位置" type="text" class="form-input" /></div>
      <div class="form-item"><label class="form-label">经办人</label><input v-model="form.采购经办人" type="text" class="form-input" /></div>
      <div class="form-item full"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
    </div>
  </TransferCreateLayout>
</template>
