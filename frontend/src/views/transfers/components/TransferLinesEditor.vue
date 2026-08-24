<script setup lang="ts">
import { ref, watch } from 'vue'
import ItemPicker from '@/components/ItemPicker.vue'
import { getDepartmentOptions, type Department } from '@/api/departments'
import { emptyDraft, type LineDraft } from './lineDrafts'
import type { TransferType } from '@/constants'

const props = defineProps<{
  modelValue: LineDraft[]
  type: TransferType
  /** 领用行部门下拉联动分公司 */
  branchId?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: LineDraft[]): void
}>()

const drafts = ref<LineDraft[]>(props.modelValue.length ? props.modelValue : [emptyDraft()])
watch(
  () => props.modelValue,
  (value) => {
    if (value !== drafts.value) drafts.value = value
  },
)

function touch() {
  emit('update:modelValue', drafts.value)
}

function addRow() {
  drafts.value.push(emptyDraft())
  touch()
}

function removeRow(index: number) {
  drafts.value.splice(index, 1)
  if (drafts.value.length === 0) drafts.value = [emptyDraft()]
  touch()
}

function onItemPicked(index: number, item: any) {
  drafts.value[index].item = item
  touch()
}

// 领用行的部门字典（按分公司过滤；department 为字典 FK）
const departments = ref<Department[]>([])
watch(
  () => props.branchId,
  async (branchId) => {
    if (props.type !== 'assign' || !branchId) {
      departments.value = []
      return
    }
    try {
      const { data } = await getDepartmentOptions({ branch_id: branchId })
      departments.value = data
    } catch {
      departments.value = []
    }
  },
  { immediate: true },
)

/** 校验：每行已选品目且数量 ≥1 返回 true */
function validate(): boolean {
  return drafts.value.every((d) => d.item !== null && Number(d.数量) >= 1)
}

defineExpose({ validate })
</script>

<template>
  <div class="lines-editor">
    <div class="section-header">
      <h3 class="section-title">明细行</h3>
      <button class="add-row-btn" type="button" @click="addRow">+ 添加行</button>
    </div>
    <div class="lines-table">
      <div class="lines-header" :data-type="type">
        <span>品目 <span class="req">*</span></span>
        <span>数量 <span class="req">*</span></span>
        <span v-if="type === 'purchase' || type === 'transfer' || type === 'recovery'">本批规格</span>
        <span v-if="type === 'purchase'">单价</span>
        <span v-if="type === 'purchase'">金额</span>
        <span v-if="type === 'assign'">使用人</span>
        <span v-if="type === 'assign'">领用部门</span>
        <span v-if="type === 'recovery'">存放位置</span>
        <span v-if="type === 'recovery'">内部编号</span>
        <span></span>
      </div>
      <div v-for="(draft, index) in drafts" :key="draft.key" class="lines-row" :data-type="type">
        <div class="cell item-cell">
          <ItemPicker :model-value="draft.item?.id ?? ''" @change="(item) => onItemPicked(index, item)" />
          <div v-if="draft.item" class="picked-meta">{{ draft.item.asset_name }}{{ draft.item.specification ? ` · ${draft.item.specification}` : '' }}{{ draft.item.unit ? ` · ${draft.item.unit}` : '' }}</div>
        </div>
        <div class="cell"><input v-model.number="draft.数量" type="number" class="row-input qty" min="1" @change="touch" /></div>
        <div v-if="type === 'purchase' || type === 'transfer' || type === 'recovery'" class="cell"><input v-model="draft.本批规格" type="text" class="row-input" placeholder="记录性" @change="touch" /></div>
        <div v-if="type === 'purchase'" class="cell"><input v-model.number="draft.单价" type="number" class="row-input num" min="0" step="0.01" @change="touch" /></div>
        <div v-if="type === 'purchase'" class="cell"><input v-model.number="draft.金额" type="number" class="row-input num" min="0" step="0.01" @change="touch" /></div>
        <div v-if="type === 'assign'" class="cell"><input v-model="draft.使用人" type="text" class="row-input" placeholder="使用人姓名" @change="touch" /></div>
        <div v-if="type === 'assign'" class="cell">
          <select v-model="draft.department" class="row-input" @change="touch">
            <option :value="null">部门（选填）</option>
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">{{ dept.name }}</option>
          </select>
        </div>
        <div v-if="type === 'recovery'" class="cell"><input v-model="draft.存放位置" type="text" class="row-input" placeholder="存放位置" @change="touch" /></div>
        <div v-if="type === 'recovery'" class="cell"><input v-model="draft.固定资产内部编号" type="text" class="row-input" placeholder="选填" @change="touch" /></div>
        <div class="cell ops"><button class="remove-btn" type="button" @click="removeRow(index)">删除</button></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.lines-editor { margin-top: var(--space-4); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.section-title { font-size: 15px; font-weight: 600; margin: 0; }
.req { color: var(--color-danger); }
.add-row-btn { padding: 6px 12px; background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 6px; color: var(--color-primary-600); font-size: 13px; cursor: pointer; }
.lines-table { border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden; }
.lines-header, .lines-row { display: grid; gap: 8px; padding: 8px 12px; align-items: center; }
.lines-header { background: var(--color-bg-elevated); font-size: 13px; color: var(--color-text-secondary); }
.lines-row { border-top: 1px solid var(--color-border); }
.lines-header[data-type='purchase'] , .lines-row[data-type='purchase'] { grid-template-columns: 2.2fr 0.6fr 1fr 0.9fr 0.9fr 56px; }
.lines-header[data-type='assign'] , .lines-row[data-type='assign'] { grid-template-columns: 2.2fr 0.6fr 1fr 1.2fr 56px; }
.lines-header[data-type='transfer'] , .lines-row[data-type='transfer'] { grid-template-columns: 2.6fr 0.7fr 1.2fr 56px; }
.lines-header[data-type='recovery'] , .lines-row[data-type='recovery'] { grid-template-columns: 2fr 0.6fr 1fr 1.1fr 1.1fr 56px; }
.cell { min-width: 0; }
.item-cell { display: flex; flex-direction: column; gap: 4px; }
.picked-meta { font-size: 12px; color: var(--color-text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row-input { width: 100%; height: 36px; padding: 0 8px; border: 1px solid var(--color-border); border-radius: 6px; font-size: 13px; background: var(--color-bg-page); outline: none; box-sizing: border-box; }
.row-input.qty, .row-input.num { text-align: center; }
.row-select { width: 100%; }
.remove-btn { height: 36px; width: 100%; border: 1px solid var(--color-border); border-radius: 6px; background: transparent; color: var(--color-danger); font-size: 13px; cursor: pointer; }
.remove-btn:hover { border-color: var(--color-danger); }
@media (max-width: 768px) {
  .lines-header { display: none; }
  .lines-header[data-type] , .lines-row[data-type] { grid-template-columns: 1fr; }
  .lines-row { position: relative; padding-bottom: 32px; }
  .cell.ops { position: absolute; right: 12px; bottom: 8px; width: 64px; }
}
</style>
