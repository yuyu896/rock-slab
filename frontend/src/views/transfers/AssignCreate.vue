<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { assignAsset } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'

const router = useRouter()
const creating = ref(false)
const branchOptions = ref<{ value: string; label: string }[]>([])

const form = ref({
  调拨日期: '',
  fromBranch: '',
  备注: '',
  items: [{ 资产编号: '', 资产名称: '', 调拨数量: 1, 使用人: '' }],
})

function addItem() {
  form.value.items.push({ 资产编号: '', 资产名称: '', 调拨数量: 1, 使用人: '' })
}
function removeItem(index: number) {
  if (form.value.items.length > 1) form.value.items.splice(index, 1)
}

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
  for (const item of f.items) {
    if (!item.资产编号 || !item.资产名称 || !item.调拨数量) {
      ElMessage.warning('每行请填写资产编号、资产名称、数量')
      return
    }
  }
  creating.value = true
  try {
    for (const item of f.items) {
      await assignAsset({
        调拨日期: f.调拨日期,
        资产编号: item.资产编号,
        资产名称: item.资产名称,
        调拨数量: item.调拨数量,
        fromBranch: f.fromBranch,
        备注: `使用人: ${item.使用人}${f.备注 ? '；' + f.备注 : ''}`,
      })
    }
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

    <div class="items-section">
      <div class="section-header">
        <h3 class="section-title">领用物品</h3>
        <button class="add-row-btn" type="button" @click="addItem">+ 添加物品</button>
      </div>
      <div class="items-table">
        <div class="items-header">
          <span>资产编号</span><span>资产名称</span><span>数量</span><span>使用人</span><span></span>
        </div>
        <div v-for="(item, index) in form.items" :key="index" class="items-row">
          <input v-model="item.资产编号" type="text" class="row-input" placeholder="资产编号" />
          <input v-model="item.资产名称" type="text" class="row-input" placeholder="资产名称" />
          <input v-model.number="item.调拨数量" type="number" class="row-input qty" min="1" placeholder="数量" />
          <input v-model="item.使用人" type="text" class="row-input" placeholder="使用人" />
          <button class="remove-btn" type="button" :disabled="form.items.length === 1" @click="removeItem(index)">删除</button>
        </div>
      </div>
    </div>

    <div class="form-item full remark-item"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
  </TransferCreateLayout>
</template>

<style scoped>
.items-section { margin-top: var(--space-4); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.section-title { font-size: 15px; font-weight: 600; margin: 0; }
.add-row-btn { padding: 6px 12px; background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 6px; color: var(--color-primary-600); font-size: 13px; cursor: pointer; }
.items-table { border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden; }
.items-header { display: grid; grid-template-columns: 1.2fr 1.5fr 0.7fr 1fr 56px; gap: 8px; padding: 8px 12px; background: var(--color-bg-elevated); font-size: 13px; color: var(--color-text-secondary); }
.items-row { display: grid; grid-template-columns: 1.2fr 1.5fr 0.7fr 1fr 56px; gap: 8px; padding: 8px 12px; border-top: 1px solid var(--color-border); align-items: center; }
.row-input { height: 36px; padding: 0 8px; border: 1px solid var(--color-border); border-radius: 6px; font-size: 13px; background: var(--color-bg-page); outline: none; box-sizing: border-box; }
.row-input.qty { text-align: center; }
.remove-btn { height: 36px; border: 1px solid var(--color-border); border-radius: 6px; background: transparent; color: var(--color-danger); font-size: 13px; cursor: pointer; }
.remove-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.remark-item { margin-top: var(--space-4); }
</style>
