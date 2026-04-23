<script setup lang="ts">
import { ref } from 'vue'
import { importAssets } from '@/api/assets'
import { generateAssetTemplate } from '@/utils/importTemplate'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'

defineProps<{ visible: boolean }>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'success'): void
}>()

const importLoading = ref(false)
const importResult = ref<{ imported: number; errors: string[] } | null>(null)

function handleDownloadTemplate() {
  generateAssetTemplate()
}

async function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  importLoading.value = true
  importResult.value = null
  try {
    const { data } = await importAssets(file)
    importResult.value = data as any
    if ((data as any).errors?.length === 0) {
      ElMessage.success(`成功导入 ${(data as any).imported} 条`)
      emit('success')
    }
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    importLoading.value = false
  }
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>批量导入资产</h3>
        <button class="modal-close" @click="emit('close')">&times;</button>
      </div>
      <div class="modal-body">
        <div class="import-row">
          <div class="import-row-info">
            <span class="import-row-label">下载导入模板</span>
            <span class="import-row-desc">按格式填写资产数据后上传</span>
          </div>
          <button class="btn-secondary" @click="handleDownloadTemplate">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            下载模板
          </button>
        </div>
        <label class="import-upload-area" :class="{ 'upload-loading': importLoading }">
          <input type="file" accept=".xlsx,.xls" class="import-file-input" @change="handleImportFile" :disabled="importLoading" />
          <template v-if="importLoading">
            <div class="import-spinner"></div>
            <span>正在导入...</span>
          </template>
          <template v-else>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>点击选择文件或拖拽到此处</span>
            <span class="import-upload-hint">支持 .xlsx / .xls 格式</span>
          </template>
        </label>
        <div v-if="importResult" class="import-result">
          <div class="import-result-header">
            <span :class="importResult.errors.length === 0 ? 'result-success' : 'result-partial'">
              成功导入 {{ importResult.imported }} 条
            </span>
            <span v-if="importResult.errors.length > 0" class="result-fail-count">
              失败 {{ importResult.errors.length }} 条
            </span>
          </div>
          <div v-if="importResult.errors.length > 0" class="import-errors">
            <div v-for="(err, idx) in importResult.errors" :key="idx" class="import-error-item">
              {{ err }}
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-cancel" @click="emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-elevated); border-radius: 16px; width: 90%; max-width: 640px; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-close { background: none; border: none; font-size: 22px; cursor: pointer; color: var(--color-text-secondary); }
.modal-body { padding: 20px; }
.modal-footer { padding: 12px 20px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.import-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.import-row-info { display: flex; flex-direction: column; gap: 2px; }
.import-row-label { font-size: 14px; font-weight: 600; }
.import-row-desc { font-size: 12px; color: var(--color-text-secondary); }
.btn-secondary { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 13px; }
.import-upload-area { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 24px; border: 2px dashed var(--color-border); border-radius: 12px; cursor: pointer; text-align: center; color: var(--color-text-secondary); font-size: 13px; transition: border-color 0.2s; margin-bottom: 16px; }
.import-upload-area:hover { border-color: var(--color-primary); }
.import-upload-area.upload-loading { opacity: 0.6; pointer-events: none; }
.import-file-input { display: none; }
.import-upload-hint { font-size: 12px; color: var(--color-text-tertiary); }
.import-spinner { width: 20px; height: 20px; border: 2px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.import-result { background: var(--color-bg); border-radius: 8px; padding: 12px; }
.import-result-header { display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; }
.result-success { color: var(--color-success); }
.result-partial { color: var(--color-warning); }
.result-fail-count { color: var(--color-danger); }
.import-errors { margin-top: 8px; max-height: 160px; overflow-y: auto; }
.import-error-item { font-size: 12px; color: var(--color-danger); padding: 3px 0; }
.btn-cancel { padding: 6px 18px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 13px; }
</style>
