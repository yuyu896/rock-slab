<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getInventoryReport } from '@/api/inventories'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { InventoryItem } from '@/types'

const props = defineProps<{ visible: boolean; taskId: string; taskName: string }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'confirm'): void }>()

const loading = ref(false)
const submitting = ref(false)
const items = ref<InventoryItem[]>([])

const varianceRows = computed(() =>
  items.value.filter(
    (it) => (it.result === 'surplus' || it.result === 'missing') && it.actualQty != null,
  ),
)
const surplusCount = computed(() => varianceRows.value.filter((it) => (it.actualQty ?? 0) > (it.expectedQty ?? 0)).length)
const missingCount = computed(() => varianceRows.value.length - surplusCount.value)

watch(() => props.visible, async (v) => {
  if (!v) return
  items.value = []
  loading.value = true
  try {
    const { data } = await getInventoryReport(props.taskId)
    items.value = data.items || []
  } catch (error) {
    ElMessage.error(handleApiError(error))
    emit('close')
  } finally {
    loading.value = false
  }
}, { immediate: true })

function delta(it: InventoryItem) {
  return (it.actualQty ?? 0) - (it.expectedQty ?? 0)
}

function onConfirm() {
  submitting.value = true
  emit('confirm')
}

defineExpose({ done: () => { submitting.value = false } })
</script>

<template>
  <div v-if="visible" class="modal-overlay" role="dialog" aria-modal="true" @click.self="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">审批确认：{{ taskName }}</h3>
        <button class="modal-close" aria-label="关闭" @click="emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div v-if="loading" class="empty-cell">加载差异中...</div>
        <template v-else>
          <p v-if="varianceRows.length === 0" class="hint">
            无差异项，审批通过不生成调整单、台账不变动。
          </p>
          <template v-else>
            <p class="hint">
              审批通过后将生成 <strong>{{ varianceRows.length }}</strong> 条调整单修正台账（在库列）：
              盘盈 {{ surplusCount }} / 盘亏 {{ missingCount }}
            </p>
            <table class="data-table">
              <thead>
                <tr><th>资产编号</th><th>名称</th><th>应盘</th><th>实盘</th><th>变动</th></tr>
              </thead>
              <tbody>
                <tr v-for="it in varianceRows" :key="it.id">
                  <td><span class="asset-code">{{ it.assetCode || '-' }}</span></td>
                  <td>{{ it.assetName || '-' }}</td>
                  <td class="col-qty">{{ it.expectedQty }}</td>
                  <td class="col-qty">{{ it.actualQty }}</td>
                  <td class="col-qty" :class="delta(it) > 0 ? 'pos' : 'neg'">
                    {{ delta(it) > 0 ? '+' : '' }}{{ delta(it) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </template>
        </template>
      </div>

      <div class="modal-footer">
        <button class="btn-secondary" :disabled="submitting" @click="emit('close')">取消</button>
        <button class="btn-primary" :disabled="loading || submitting" @click="onConfirm">
          {{ submitting ? '审批中...' : '通过并生成调整单' }}
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
  width: min(640px, calc(100vw - 32px));
  max-height: calc(100vh - 64px);
  background: var(--color-bg-card); border-radius: 12px;
  border: 1px solid var(--color-border);
  display: flex; flex-direction: column; overflow: hidden;
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: var(--space-4) var(--space-5); flex-shrink: 0;
  border-bottom: 1px solid var(--color-border);
}
.modal-title { margin: 0; font-size: var(--text-lg); font-weight: 600; }
.modal-close {
  border: none; background: none; font-size: 20px; cursor: pointer;
  color: var(--color-text-tertiary); line-height: 1;
}
.modal-body { padding: var(--space-5); overflow: auto; display: flex; flex-direction: column; gap: var(--space-4); }
.hint { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  text-align: left; padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border); white-space: nowrap;
}
.data-table td {
  padding: var(--space-2) var(--space-3); font-size: var(--text-sm);
  color: var(--color-text-primary); border-bottom: 1px solid var(--color-border-light);
  white-space: nowrap;
}
.data-table tbody tr:hover { background: var(--color-bg-elevated); }
.asset-code { font-family: var(--font-mono); color: var(--color-primary-600); }
.col-qty { text-align: right; font-variant-numeric: tabular-nums; }
.col-qty.pos { color: var(--color-success); }
.col-qty.neg { color: var(--color-danger); }
.empty-cell { text-align: center; padding: var(--space-8) 0; color: var(--color-text-tertiary); }
.modal-footer {
  display: flex; justify-content: flex-end; gap: var(--space-3);
  padding: var(--space-4) var(--space-5); border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}
.btn-secondary, .btn-primary {
  height: 36px; padding: 0 var(--space-4); border-radius: 8px;
  font-size: var(--text-sm); cursor: pointer;
}
.btn-secondary { background: var(--color-bg-card); border: 1px solid var(--color-border); }
.btn-primary { background: var(--color-primary-500); border: 1px solid var(--color-primary-500); color: #fff; }
.btn-primary:disabled, .btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
