<script setup lang="ts">
import { ref, watch } from 'vue'
import { importAssetStocks, downloadAssetStockTemplate } from '@/api/assets'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { LedgerImportDiff } from '@/types'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'success'): void }>()

const file = ref<File | null>(null)
const uploading = ref(false)
const confirming = ref(false)
const diffs = ref<LedgerImportDiff[]>([])
const errors = ref<string[]>([])

watch(() => props.visible, (v) => {
  if (v) {
    file.value = null
    diffs.value = []
    errors.value = []
  }
})

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
  diffs.value = []
  errors.value = []
}

async function handleDownloadTemplate() {
  try {
    const { data } = await downloadAssetStockTemplate()
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = '台账增量导入模板.xlsx'
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

async function handlePreview() {
  if (!file.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  try {
    const { data } = await importAssetStocks(file.value)
    diffs.value = data.diffs ?? []
    errors.value = data.errors ?? []
    if (!diffs.value.length && !errors.value.length) {
      ElMessage.success('所有行与台账现值一致，无需调整')
    }
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    uploading.value = false
  }
}

async function handleConfirm() {
  if (!file.value) return
  confirming.value = true
  try {
    const { data } = await importAssetStocks(file.value, true)
    const applied = data.applied ?? 0
    const errs = data.errors ?? []
    if (errs.length) {
      ElMessage.warning(`已生成 ${applied} 条调整单；${errs.length} 行被拒绝（详见导入结果）`)
    } else {
      ElMessage.success(`已生成 ${applied} 条调整单并入账`)
    }
    emit('success')
    emit('close')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <div class="modal-overlay" role="dialog" aria-modal="true" @click.self="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">台账增量导入</h3>
        <button class="modal-close" aria-label="关闭" @click="emit('close')">×</button>
      </div>

      <div class="modal-body">
        <p class="hint">
          增量语义：模板 3 列（分公司 / 资产编号 / 在库数量）。系统比对现值生成差异，
          确认后每处差异生成一条调整单入账（事由=导入调整）。
          <a class="tpl-link" @click="handleDownloadTemplate">下载模板</a>
        </p>

        <div class="file-row">
          <input type="file" accept=".xlsx,.xls" @change="onFileChange" />
          <button class="btn-secondary" :disabled="uploading || !file" @click="handlePreview">
            {{ uploading ? '解析中...' : '预览差异' }}
          </button>
        </div>

        <div v-if="errors.length" class="error-list">
          <div v-for="(err, i) in errors" :key="i" class="error-item">{{ err }}</div>
        </div>

        <div v-if="diffs.length" class="diff-section">
          <table class="diff-table">
            <thead>
              <tr>
                <th>行号</th>
                <th>分公司</th>
                <th>资产编号</th>
                <th>资产名称</th>
                <th>现值</th>
                <th>导入值</th>
                <th>变动量</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in diffs" :key="`${d.分公司}-${d.资产编号}`">
                <td>{{ d.行号 }}</td>
                <td>{{ d.分公司 }}</td>
                <td>{{ d.资产编号 }}</td>
                <td>{{ d.资产名称 || '-' }}</td>
                <td>{{ d.现值 }}</td>
                <td>{{ d.导入值 }}</td>
                <td :class="d.变动量 > 0 ? 'pos' : 'neg'">{{ d.变动量 > 0 ? '+' : '' }}{{ d.变动量 }}</td>
              </tr>
            </tbody>
          </table>
          <p class="confirm-hint">
            共 {{ diffs.length }} 处差异，确认后将逐条生成调整单（留痕可追溯）。
          </p>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="emit('close')">取消</button>
        <button class="btn-confirm" :disabled="confirming || !diffs.length" @click="handleConfirm">
          {{ confirming ? '入账中...' : `确认入账（${diffs.length} 条）` }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal-content {
  background: var(--color-bg-elevated);
  border-radius: 12px;
  width: 90%;
  max-width: 720px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--color-text-secondary);
}

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
}

.hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0 0 12px;
}

.tpl-link {
  color: var(--color-primary-600);
  cursor: pointer;
  text-decoration: underline;
  margin-left: 8px;
}

.file-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.error-list {
  margin: 8px 0;
  max-height: 140px;
  overflow-y: auto;
}

.error-item {
  font-size: 13px;
  color: var(--color-danger);
  padding: 2px 0;
}

.diff-section {
  margin-top: 8px;
}

.diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.diff-table th {
  background: var(--color-bg-elevated);
  text-align: left;
  padding: 6px 8px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.diff-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--color-border-light);
}

.diff-table td.pos { color: var(--color-success); }
.diff-table td.neg { color: var(--color-danger); }

.confirm-hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 10px 0 0;
}

.modal-footer {
  padding: 14px 24px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-secondary {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  cursor: pointer;
  font-size: 13px;
}

.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-cancel {
  padding: 8px 20px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  cursor: pointer;
  font-size: 14px;
}

.btn-confirm {
  padding: 8px 20px;
  border-radius: 8px;
  border: none;
  background: var(--color-primary-500);
  color: #fff;
  cursor: pointer;
  font-size: 14px;
}

.btn-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
