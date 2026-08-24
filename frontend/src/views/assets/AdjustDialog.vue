<script setup lang="ts">
import { ref, watch } from 'vue'
import { createLedgerAdjustment } from '@/api/assets'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { AssetStock } from '@/types'

const props = defineProps<{ visible: boolean; stock: AssetStock | null }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'success'): void }>()

const COLUMN_OPTIONS = [
  { value: '在库数量', label: '在库' },
  { value: '在用数量', label: '在用' },
  { value: '回收库数量', label: '回收库' },
]

const form = ref({ column: '在库数量', delta: 1, reason: '' })
const submitting = ref(false)
const errorText = ref('')

watch(() => props.visible, (v) => {
  if (v) {
    form.value = { column: '在库数量', delta: 1, reason: '' }
    errorText.value = ''
  }
})

async function handleSubmit() {
  if (!props.stock) return
  if (!form.value.reason.trim()) {
    errorText.value = '事由不能为空'
    return
  }
  if (!Number.isInteger(form.value.delta) || form.value.delta === 0) {
    errorText.value = '变动量必须是非零整数'
    return
  }
  submitting.value = true
  try {
    const { data } = await createLedgerAdjustment({
      branch: props.stock.branch,
      资产编号: props.stock.资产编号,
      目标列: form.value.column,
      变动量: form.value.delta,
      事由: form.value.reason.trim(),
    })
    ElMessage.success(`调整单 ${data.单据编号} 已入账`)
    emit('success')
    emit('close')
  } catch (error) {
    errorText.value = handleApiError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" role="dialog" aria-modal="true" @click.self="emit('close')">
    <div class="modal-content modal-sm">
      <div class="modal-header">
        <h3 class="modal-title">台账调整</h3>
        <button class="modal-close" aria-label="关闭" @click="emit('close')">×</button>
      </div>

      <div class="modal-body">
        <p v-if="stock" class="hint">
          {{ stock.branchName }} × {{ stock.资产编号 }}（{{ stock.资产名称 || '—' }}）
          当前 在库 {{ stock.在库数量 }} / 在用 {{ stock.在用数量 }} / 回收库 {{ stock.回收库数量 }}
        </p>

        <div class="form-grid">
          <label class="form-field">
            <span>目标列</span>
            <select v-model="form.column">
              <option v-for="opt in COLUMN_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </label>
          <label class="form-field">
            <span>变动量（可正可负）</span>
            <input v-model.number="form.delta" type="number" step="1" />
          </label>
        </div>
        <label class="form-field">
          <span>事由（必填）</span>
          <input v-model="form.reason" type="text" maxlength="200" placeholder="如：实物校准、漏记入账" />
        </label>

        <div v-if="errorText" class="error-text">{{ errorText }}</div>
      </div>

      <div class="modal-footer">
        <button class="btn-secondary" :disabled="submitting" @click="emit('close')">取消</button>
        <button class="btn-primary" :disabled="submitting" @click="handleSubmit">
          {{ submitting ? '提交中...' : '生成调整单' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  display: flex; align-items: center; justify-content: center;
}
.modal-content {
  width: min(480px, calc(100vw - 32px));
  background: var(--color-bg-card); border-radius: 12px;
  border: 1px solid var(--color-border); overflow: hidden;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}
.modal-title { margin: 0; font-size: var(--text-lg); font-weight: 600; }
.modal-close {
  border: none; background: none; font-size: 20px; cursor: pointer;
  color: var(--color-text-tertiary); line-height: 1;
}
.modal-body { padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-4); }
.hint { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
.form-field { display: flex; flex-direction: column; gap: var(--space-2); font-size: var(--text-sm); }
.form-field span { color: var(--color-text-secondary); }
.form-field input, .form-field select {
  height: 36px; padding: 0 var(--space-3);
  border: 1px solid var(--color-border); border-radius: 8px;
  background: var(--color-bg-card); font-size: var(--text-sm);
}
.error-text { color: var(--color-danger); font-size: var(--text-sm); white-space: pre-wrap; }
.modal-footer {
  display: flex; justify-content: flex-end; gap: var(--space-3);
  padding: var(--space-4) var(--space-5); border-top: 1px solid var(--color-border);
}
.btn-secondary, .btn-primary {
  height: 36px; padding: 0 var(--space-4); border-radius: 8px;
  font-size: var(--text-sm); cursor: pointer;
}
.btn-secondary { background: var(--color-bg-card); border: 1px solid var(--color-border); }
.btn-primary { background: var(--color-primary-500); border: 1px solid var(--color-primary-500); color: #fff; }
.btn-primary:disabled, .btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
