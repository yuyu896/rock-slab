<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TransferCreateLayout from './components/TransferCreateLayout.vue'
import { draftsToItems, emptyDraft, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { recoverAsset } from '@/api/transfers'
import { getBranches } from '@/api/branches'
import { getInventoryReport } from '@/api/inventories'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import DepartmentSelect from '@/components/DepartmentSelect.vue'

const RECOVERY_CATEGORIES = ['闲置回收', '报废回收', '捐赠回收', '其他']
const DISPOSAL_METHODS = ['出售', '报废', '捐赠']

const router = useRouter()
const route = useRoute()
const creating = ref(false)
const branchOptions = ref<{ value: string; label: string; id?: string }[]>([])
const form = ref({
  调拨日期: '',
  回收分类: '',
  回收去向: 'recycle_bin' as 'recycle_bin' | 'dispose',
  处置方式: '' as '' | '出售' | '报废' | '捐赠',
  处置金额: undefined as number | undefined,
  出库日期: '',
  调出分公司: '',
  调出部门: '',
  采购经办人: '',
  备注: '',
})
const lines = ref<LineDraft[]>([emptyDraft()])
const linesEditor = ref<InstanceType<typeof TransferLinesEditor> | null>(null)
const fromBranchName = computed(() => form.value.调出分公司)

/** 盘亏跟进预填：来自实例盘报告的缺失实例（按品目聚合成行，实例逐台带入） */
async function prefillFromInventoryTask(taskId: string) {
  try {
    const { data: report } = await getInventoryReport(taskId)
    // 实例盘报告的 items 为 InventoryInstanceItem（inventoryKind=instance 保证）
    const missing = ((report.items ?? []) as any[]).filter((i: any) => i.result === 'missing')
    if (!missing.length) {
      ElMessage.warning('该盘点任务没有缺失实例，无需发起回收')
      return
    }
    const byItem = new Map<string, { draft: LineDraft; item: any }>()
    for (const entry of missing) {
      let group = byItem.get(entry.itemId)
      if (!group) {
        const draft = emptyDraft()
        draft.item = {
          id: entry.itemId,
          asset_code: entry.assetCode,
          asset_name: entry.assetName,
          specification: '',
          unit: entry.unit,
          assetCategory: '',
          itemCategory: '',
          managementType: 'instance',
        }
        draft.instances = []
        group = { draft, item: entry }
        byItem.set(entry.itemId, group)
      }
      group.draft.instances.push({ id: entry.instance, code: entry.instanceCode })
    }
    for (const g of byItem.values()) g.draft.数量 = g.draft.instances.length
    lines.value = [...byItem.values()].map(g => g.draft)
    const task = report.task as any
    if (task.branch) {
      const branchName = branchOptions.value.find(b => b.id === task.branch || b.value === task.branch)?.label
        ?? branchOptions.value.find(b => b.id === task.branch)?.value
      if (branchName) form.value.调出分公司 = branchName
    }
    form.value.备注 = `盘亏跟进：来自盘点任务「${task.name}」缺失 ${missing.length} 台`
    ElMessage.success(`已预填 ${missing.length} 台缺失实例，请补全单头后提交`)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

onMounted(async () => {
  try {
    const { data } = await getBranches()
    branchOptions.value = data.map((b: any) => ({ value: b.name, label: b.name, id: b.id }))
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
  const fromTask = route.query.fromInventoryTask
  if (typeof fromTask === 'string' && fromTask) {
    await prefillFromInventoryTask(fromTask)
  }
})

function goBack() {
  router.replace('/transfers/recovery')
}

async function submit() {
  const f = form.value
  if (!f.调拨日期 || !f.调出分公司) {
    ElMessage.warning('请填写日期与分公司')
    return
  }
  if (f.回收去向 === 'dispose' && !f.处置方式) {
    ElMessage.warning('直接处置需选择处置方式')
    return
  }
  const items = draftsToItems(lines.value)
  if (items.length === 0 || !linesEditor.value?.validate()) {
    ElMessage.warning(linesEditor.value?.validateMessage || '每行请选择品目并填写数量（≥1）')
    return
  }
  creating.value = true
  try {
    await recoverAsset({
      调拨日期: f.调拨日期,
      回收分类: f.回收分类,
      回收去向: f.回收去向,
      处置方式: f.回收去向 === 'dispose' ? f.处置方式 : '',
      处置金额: f.回收去向 === 'dispose' && f.处置方式 === '出售' ? f.处置金额 : undefined,
      出库日期: f.出库日期 || undefined,
      调出分公司: f.调出分公司,
      调出部门: f.调出部门,
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
  <TransferCreateLayout title="新建回收记录" :loading="creating" @submit="submit" @back="goBack">
    <div class="form-grid">
      <div class="form-item"><label class="form-label">入库日期 <span class="required">*</span></label><input v-model="form.调拨日期" type="date" class="form-input" /></div>
      <div class="form-item">
        <label class="form-label">回收分类 <span class="required">*</span></label>
        <select v-model="form.回收分类" class="form-select">
          <option value="">请选择</option>
          <option v-for="cat in RECOVERY_CATEGORIES" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>

      <!-- 回收去向二选一（设计书 5.2：入回收库 / 直接处置） -->
      <div class="form-item full">
        <label class="form-label">回收去向 <span class="required">*</span></label>
        <div class="destination-row">
          <label class="radio-label">
            <input v-model="form.回收去向" type="radio" value="recycle_bin" />
            入回收库（可再领用）
          </label>
          <label class="radio-label">
            <input v-model="form.回收去向" type="radio" value="dispose" />
            直接处置（出局）
          </label>
        </div>
      </div>
      <div v-if="form.回收去向 === 'dispose'" class="form-item">
        <label class="form-label">处置方式 <span class="required">*</span></label>
        <select v-model="form.处置方式" class="form-select">
          <option value="">请选择</option>
          <option v-for="m in DISPOSAL_METHODS" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>
      <div v-if="form.回收去向 === 'dispose' && form.处置方式 === '出售'" class="form-item">
        <label class="form-label">处置金额</label>
        <input v-model.number="form.处置金额" type="number" class="form-input" min="0" step="0.01" />
      </div>

      <div class="form-item">
        <label class="form-label">分公司 <span class="required">*</span></label>
        <select v-model="form.调出分公司" class="form-select">
          <option value="">请选择</option>
          <option v-for="b in branchOptions" :key="b.value" :value="b.label">{{ b.label }}</option>
        </select>
      </div>
      <div class="form-item"><label class="form-label">所属部门</label><DepartmentSelect v-model="form.调出部门" :branch="form.调出分公司" /></div>
      <div class="form-item"><label class="form-label">出库日期</label><input v-model="form.出库日期" type="date" class="form-input" /></div>
      <div class="form-item"><label class="form-label">经办人</label><input v-model="form.采购经办人" type="text" class="form-input" /></div>
      <div class="form-item full"><label class="form-label">备注</label><textarea v-model="form.备注" class="form-textarea" rows="2" placeholder="备注信息"></textarea></div>
    </div>

    <TransferLinesEditor ref="linesEditor" v-model="lines" type="recovery" :branch-name="fromBranchName" />
  </TransferCreateLayout>
</template>

<style scoped>
.destination-row {
  display: flex;
  gap: var(--space-6);
  padding: var(--space-2) 0;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  cursor: pointer;
}
</style>
