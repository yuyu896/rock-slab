<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import TransferDetailLayout from './components/TransferDetailLayout.vue'
import { draftsFromLines, draftsToItems, type LineDraft } from './components/lineDrafts'
import TransferLinesEditor from './components/TransferLinesEditor.vue'
import { getTransfer, updateTransfer, resubmitTransfer, submitTransfer, withdrawTransfer } from '@/api/transfers'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TransferDocument } from '@/types'

const route = useRoute()
const transfer = ref<TransferDocument | null>(null)
const loading = ref(false)
const editing = ref(false)
const saving = ref(false)
const editForm = ref<Record<string, any>>({})
const editLines = ref<LineDraft[]>([])
const linesEditor = ref<InstanceType<typeof TransferLinesEditor> | null>(null)
/** 编辑来源态：已驳回保存后 resubmit，草稿保存后 submit */
const editFrom = ref<'rejected' | 'draft'>('rejected')

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

/** 撤回入口显隐由服务端 canWithdraw 判定（账号身份，purchase-withdraw-creator-fk） */

async function withdrawDoc(doc: TransferDocument) {
  try {
    await ElMessageBox.confirm('撤回后单据回到草稿，可修改后重新提交', '确认撤回？', {
      confirmButtonText: '撤回',
      cancelButtonText: '再想想',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await withdrawTransfer(doc.id)
    ElMessage.success('已撤回为草稿，可直接修改后重新提交')
    await fetchTransfer()
    startEdit('draft')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

async function submitDraft(doc: TransferDocument) {
  try {
    await submitTransfer(doc.id)
    ElMessage.success('已提交审批')
    await fetchTransfer()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

function startEdit(from: 'rejected' | 'draft') {
  if (!transfer.value) return
  editFrom.value = from
  editForm.value = { ...transfer.value }
  editLines.value = draftsFromLines(transfer.value.lines ?? [])
  editing.value = true
}

async function saveAndSubmit() {
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
      需求部门: editForm.value.需求部门,
      采购经办人: editForm.value.采购经办人,
      备注: editForm.value.备注,
      items,
    })
    await (editFrom.value === 'draft' ? submitTransfer(transfer.value.id) : resubmitTransfer(transfer.value.id))
    ElMessage.success(editFrom.value === 'draft' ? '已保存并提交' : '已修改并重新提交')
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
      <div class="info-row">
        <span class="info-item"><label>需求部门</label><span>{{ doc.需求部门 || '-' }}</span></span>
        <span class="info-item"><label>采购经办人</label><span>{{ doc.采购经办人 || '-' }}</span></span>
        <span class="info-item wide"><label>备注</label><span>{{ doc.备注 || '-' }}</span></span>
      </div>
    </template>

    <template #extra-edit>
      <div v-if="editing" class="edit-block">
        <div class="edit-grid">
          <div class="form-item"><label>日期</label><input v-model="editForm.调拨日期" type="date" class="form-input" /></div>
          <div class="form-item"><label>需求部门</label><input v-model="editForm.需求部门" type="text" class="form-input" /></div>
          <div class="form-item"><label>采购经办人</label><input v-model="editForm.采购经办人" type="text" class="form-input" /></div>
          <div class="form-item full"><label>备注</label><textarea v-model="editForm.备注" class="form-input" rows="2"></textarea></div>
        </div>
        <h4 class="edit-lines-title">明细行（整体替换，供应商按行填写）</h4>
        <TransferLinesEditor ref="linesEditor" v-model="editLines" type="purchase" />
      </div>
    </template>

    <template #footer="{ doc }">
      <template v-if="!editing && doc.canWithdraw">
        <button class="btn-cancel" @click="withdrawDoc(doc)">撤回</button>
      </template>
      <template v-if="!editing && doc.审批状态 === '已驳回'">
        <button class="btn-primary" @click="startEdit('rejected')">修改</button>
      </template>
      <template v-if="!editing && doc.审批状态 === '草稿'">
        <button class="btn-cancel" @click="startEdit('draft')">修改</button>
        <button class="btn-primary" @click="submitDraft(doc)">提交审批</button>
      </template>
      <template v-if="editing">
        <button class="btn-cancel" @click="editing = false">取消</button>
        <button class="btn-primary" :disabled="saving" @click="saveAndSubmit">{{ saving ? '提交中...' : editFrom === 'draft' ? '保存并提交' : '保存并重新提交' }}</button>
      </template>
    </template>
  </TransferDetailLayout>
</template>

<style scoped>
.info-row { display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-6); }
.info-item { display: inline-flex; align-items: baseline; gap: 6px; font-size: var(--text-sm); }
.info-item label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.info-item span { color: var(--color-text-primary); }
.info-item.wide { flex-basis: 100%; }
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
