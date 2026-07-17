<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTransfer, updateTransfer, resubmitTransfer, approveTransfer, rejectTransfer } from '@/api/transfers'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Transfer } from '@/types'

const route = useRoute()
const router = useRouter()
const transfer = ref<Transfer | null>(null)
const loading = ref(false)
const editing = ref(false)
const saving = ref(false)
const approving = ref(false)
const editForm = ref<Partial<Transfer>>({})

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
  editing.value = true
}

async function saveAndResubmit() {
  if (!transfer.value) return
  saving.value = true
  try {
    await updateTransfer(transfer.value.id, editForm.value)
    await resubmitTransfer(transfer.value.id)
    ElMessage.success('已修改并重新提交')
    editing.value = false
    router.replace('/transfers/transfer')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

async function handleApprove() {
  if (!transfer.value) return
  approving.value = true
  try {
    await ElMessageBox.confirm('确定通过此申请？', '审批确认', { type: 'info' })
    await approveTransfer(transfer.value.id, { approved: true })
    ElMessage.success('审批通过')
    router.replace('/transfers/transfer')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(handleApiError(error))
  } finally {
    approving.value = false
  }
}

async function handleReject() {
  if (!transfer.value) return
  approving.value = true
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回确认', {
      confirmButtonText: '确定驳回',
      cancelButtonText: '取消',
      inputValidator: (v: string) => (v && v.trim() ? true : '请输入驳回原因'),
    })
    await rejectTransfer(transfer.value.id, { reason: value })
    ElMessage.success('已驳回')
    router.replace('/transfers/transfer')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(handleApiError(error))
  } finally {
    approving.value = false
  }
}

onMounted(fetchTransfer)
</script>

<template>
  <div class="detail-page">
    <div class="page-header">
      <button class="back-btn" @click="router.replace('/transfers/transfer')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回
      </button>
      <h1 class="page-title">调拨详情</h1>
    </div>

    <div v-if="loading" class="state-text">加载中...</div>
    <div v-else-if="!transfer" class="state-text">未找到记录</div>

    <div v-else class="form-card">
      <div v-if="!editing" class="form-grid">
        <div class="form-item"><label>调拨日期</label><span class="value">{{ transfer.调拨日期 || '-' }}</span></div>
        <div class="form-item"><label>资产编号</label><span class="value">{{ transfer.资产编号 || '-' }}</span></div>
        <div class="form-item"><label>资产名称</label><span class="value">{{ transfer.资产名称 || '-' }}</span></div>
        <div class="form-item"><label>规格型号</label><span class="value">{{ transfer.规格型号 || '-' }}</span></div>
        <div class="form-item"><label>调拨数量</label><span class="value">{{ transfer.调拨数量 ?? '-' }}</span></div>
        <div class="form-item"><label>调出分公司</label><span class="value">{{ transfer.调出分公司 || '-' }}</span></div>
        <div class="form-item"><label>调入分公司</label><span class="value">{{ transfer.调入分公司 || '-' }}</span></div>
        <div class="form-item"><label>调出部门</label><span class="value">{{ transfer.调出部门 || '-' }}</span></div>
        <div class="form-item"><label>调入部门</label><span class="value">{{ transfer.调入部门 || '-' }}</span></div>
        <div class="form-item"><label>调出负责人</label><span class="value">{{ transfer.调出负责人 || '-' }}</span></div>
        <div class="form-item"><label>调入负责人</label><span class="value">{{ transfer.调入负责人 || '-' }}</span></div>
        <div class="form-item"><label>审批状态</label><span class="value">{{ transfer.审批状态 }}</span></div>
        <div class="form-item full"><label>调拨原因</label><span class="value">{{ transfer.调拨原因 || '-' }}</span></div>
        <div class="form-item full"><label>备注</label><span class="value">{{ transfer.备注 || '-' }}</span></div>
      </div>

      <div v-else class="form-grid">
        <div class="form-item"><label>资产名称</label><input v-model="editForm.资产名称" type="text" class="form-input" /></div>
        <div class="form-item"><label>规格型号</label><input v-model="editForm.规格型号" type="text" class="form-input" /></div>
        <div class="form-item"><label>调拨数量</label><input v-model.number="editForm.调拨数量" type="number" class="form-input" min="1" /></div>
        <div class="form-item"><label>调出分公司</label><input v-model="editForm.调出分公司" type="text" class="form-input" /></div>
        <div class="form-item"><label>调入分公司</label><input v-model="editForm.调入分公司" type="text" class="form-input" /></div>
        <div class="form-item"><label>调出部门</label><input v-model="editForm.调出部门" type="text" class="form-input" /></div>
        <div class="form-item"><label>调入部门</label><input v-model="editForm.调入部门" type="text" class="form-input" /></div>
        <div class="form-item full"><label>调拨原因</label><textarea v-model="editForm.调拨原因" class="form-textarea" rows="2"></textarea></div>
        <div class="form-item full"><label>备注</label><textarea v-model="editForm.备注" class="form-textarea" rows="3"></textarea></div>
      </div>

      <div class="form-footer">
        <template v-if="!editing">
          <button v-if="transfer.审批状态 === '待审批'" class="btn-reject" :disabled="approving" @click="handleReject">驳回</button>
          <button v-if="transfer.审批状态 === '待审批'" class="btn-primary" :disabled="approving" @click="handleApprove">{{ approving ? '处理中...' : '通过' }}</button>
          <button v-if="transfer.审批状态 === '已驳回'" class="btn-primary" @click="startEdit">修改</button>
        </template>
        <template v-else>
          <button class="btn-cancel" @click="editing = false">取消</button>
          <button class="btn-primary" :disabled="saving" @click="saveAndResubmit">{{ saving ? '提交中...' : '保存并重新提交' }}</button>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-page { max-width: 960px; margin: 0 auto; }
.page-header { display: flex; align-items: center; gap: var(--space-4); margin-bottom: var(--space-6); }
.back-btn { display: inline-flex; align-items: center; gap: var(--space-1); height: 36px; padding: 0 var(--space-3); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-secondary); cursor: pointer; }
.back-btn:hover { color: var(--color-primary-500); border-color: var(--color-primary-300); }
.back-btn svg { width: 16px; height: 16px; }
.page-title { font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.state-text { text-align: center; color: var(--color-text-secondary); padding: var(--space-8); }
.form-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 16px; padding: var(--space-6); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full { grid-column: 1 / -1; }
.form-item label { font-size: 14px; font-weight: 500; color: var(--color-text-primary); }
.form-item .value { font-size: 14px; color: var(--color-text-secondary); }
.form-input, .form-textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg-page); outline: none; box-sizing: border-box; }
.form-textarea { resize: vertical; }
.form-footer { display: flex; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-6); }
.btn-cancel { height: 40px; padding: 0 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-card); cursor: pointer; font-size: 14px; color: var(--color-text-primary); }
.btn-primary { height: 40px; padding: 0 20px; border-radius: 8px; border: none; background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: 14px; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-reject { height: 40px; padding: 0 20px; border-radius: 8px; border: none; background: oklch(0.92 0.10 25); color: var(--color-danger); cursor: pointer; font-size: 14px; font-weight: 500; }
.btn-reject:disabled { opacity: 0.6; cursor: not-allowed; }
@media (max-width: 768px) { .form-grid { grid-template-columns: 1fr; } }
</style>
