<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TransferDetailLayout from './components/TransferDetailLayout.vue'
import { draftsFromLines, draftsToItems, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { getTransfer, updateTransfer, resubmitTransfer } from '@/api/transfers'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { TransferDocument } from '@/types'

const route = useRoute()
const router = useRouter()
const transfer = ref<TransferDocument | null>(null)
const loading = ref(false)
const editing = ref(false)
const saving = ref(false)
const editForm = ref<Record<string, any>>({})
const editLines = ref<LineDraft[]>([])
const linesEditor = ref<InstanceType<typeof TransferLinesEditor> | null>(null)

async function fetchTransfer() {
  loading.value = true
  try {
    const { data } = await getTransfer(route.params.id as string)
    transfer.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

function startEdit() {
  if (!transfer.value) return
  editForm.value = { ...transfer.value }
  editLines.value = draftsFromLines(transfer.value.lines ?? [])
  editing.value = true
}

async function saveAndResubmit() {
  if (!transfer.value) return
  const items = draftsToItems(editLines.value)
  if (items.length === 0 || !linesEditor.value?.validate()) {
    ElMessage.warning('每行请选择品目并填写数量（≥1）')
    return
  }
  saving.value = true
  try {
    await updateTransfer(transfer.value.id, {
      调拨日期: editForm.value.调拨日期,
      供应商: editForm.value.供应商,
      需求部门: editForm.value.需求部门,
      采购经办人: editForm.value.采购经办人,
      备注: editForm.value.备注,
      items,
    })
    await resubmitTransfer(transfer.value.id)
    ElMessage.success('已修改并重新提交')
    editing.value = false
    await fetchTransfer()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

onMounted(fetchTransfer)
</script>

<template>
  <TransferDetailLayout
    title="采购入库详情"
    back-path="/transfers/purchase"
    type="purchase"
    :doc="transfer"
    :loading="loading"
  >
    <template #extra-view="{ doc }">
      <div class="extra-grid">
        <span class="extra-item"><label>供应商</label><span>{{ doc.供应商 || '-' }}</span></span>
        <span class="extra-item"><label>需求部门</label><span>{{ doc.需求部门 || '-' }}</span></span>
        <span class="extra-item"><label>采购经办人</label><span>{{ doc.采购经办人 || '-' }}</span></span>
        <span class="extra-item full"><label>备注</label><span>{{ doc.备注 || '-' }}</span></span>
      </div>
    </template>

    <template #extra-edit>
      <div v-if="editing" class="edit-block">
        <div class="edit-grid">
          <div class="form-item"><label>日期</label><input v-model="editForm.调拨日期" type="date" class="form-input" /></div>
          <div class="form-item"><label>供应商</label><input v-model="editForm.供应商" type="text" class="form-input" /></div>
          <div class="form-item"><label>需求部门</label><input v-model="editForm.需求部门" type="text" class="form-input" /></div>
          <div class="form-item"><label>采购经办人</label><input v-model="editForm.采购经办人" type="text" class="form-input" /></div>
          <div class="form-item full"><label>备注</label><textarea v-model="editForm.备注" class="form-input" rows="2"></textarea></div>
        </div>
        <h4 class="edit-lines-title">明细行（整体替换）</h4>
        <TransferLinesEditor ref="linesEditor" v-model="editLines" type="purchase" />
      </div>
    </template>

    <template #footer="{ doc }">
      <template v-if="!editing && doc.审批状态 === '已驳回'">
        <button class="btn-primary" @click="startEdit">修改</button>
      </template>
      <template v-if="editing">
        <button class="btn-cancel" @click="editing = false">取消</button>
        <button class="btn-primary" :disabled="saving" @click="saveAndResubmit">{{ saving ? '提交中...' : '保存并重新提交' }}</button>
      </template>
    </template>
  </TransferDetailLayout>
</template>

<style scoped>
.extra-grid { display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-6); }
.extra-item { display: inline-flex; align-items: baseline; gap: 6px; font-size: var(--text-sm); }
.extra-item label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.extra-item span { color: var(--color-text-primary); }
.extra-item.full { flex-basis: 100%; }
.edit-block { display: flex; flex-direction: column; gap: var(--space-4); padding-top: var(--space-4); border-top: 1px dashed var(--color-border); }
.edit-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); }
.edit-lines-title { margin: 0; font-size: 14px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full { grid-column: 1 / -1; }
.form-item label { font-size: 13px; font-weight: 500; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg-page); outline: none; box-sizing: border-box; }
.btn-cancel { height: 40px; padding: 0 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-card); cursor: pointer; font-size: 14px; }
.btn-primary { height: 40px; padding: 0 20px; border-radius: 8px; border: none; background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: 14px; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
@media (max-width: 768px) { .edit-grid { grid-template-columns: 1fr; } }
</style>
