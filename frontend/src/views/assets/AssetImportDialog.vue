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
    input.value = ''
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
        <div class="import-step">
          <div class="import-step-header">
            <span class="import-step-num">1</span>
            <span class="import-step-title">下载导入模板</span>
          </div>
          <p class="import-step-desc">请先下载模板文件，按格式填写资产数据后上传</p>
          <button class="btn-secondary import-template-btn" @click="handleDownloadTemplate">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            下载模板
          </button>
        </div>
        <div class="import-step">
          <div class="import-step-header">
            <span class="import-step-num">2</span>
            <span class="import-step-title">上传填写好的 Excel 文件</span>
          </div>
          <label class="import-upload-area" :class="{ 'upload-loading': importLoading }">
            <input type="file" accept=".xlsx,.xls" class="import-file-input" @change="handleImportFile" :disabled="importLoading" />
            <template v-if="importLoading">
              <div class="import-spinner"></div>
              <span>正在导入...</span>
            </template>
            <template v-else>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <span>点击选择文件或拖拽到此处</span>
              <span class="import-upload-hint">支持 .xlsx / .xls 格式</span>
            </template>
          </label>
        </div>
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
.modal-content { background: var(--color-bg-card); border-radius: 16px; width: 90%; max-width: 640px; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { margin: 0; font-size: var(--text-lg); font-weight: 600; }
.modal-close { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; font-size: 20px; color: var(--color-text-tertiary); cursor: pointer; border-radius: 6px; }
.modal-close:hover { background: var(--color-bg-elevated); }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: var(--space-3); padding: 12px 20px; border-top: 1px solid var(--color-border); }
.import-step { margin-bottom: 16px; }
.import-step-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.import-step-num { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; background: var(--color-primary-500); color: white; border-radius: 50%; font-size: var(--text-xs); font-weight: 600; }
.import-step-title { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.import-step-desc { font-size: var(--text-xs); color: var(--color-text-tertiary); margin: 0 0 var(--space-2); }
.import-template-btn svg { width: 16px; height: 16px; }
.btn-secondary { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 10px; border: 1px solid var(--color-border); background: var(--color-bg-card); cursor: pointer; font-size: var(--text-sm); }
.import-upload-area { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; padding: 20px; border: 2px dashed var(--color-border); border-radius: 12px; cursor: pointer; text-align: center; color: var(--color-text-secondary); font-size: var(--text-sm); }
.import-upload-area:hover { border-color: var(--color-primary-300); background: var(--color-primary-50); }
.import-upload-area.upload-loading { cursor: not-allowed; opacity: 0.7; }
.import-upload-area svg { width: 24px; height: 24px; }
.import-upload-hint { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.import-file-input { display: none; }
.import-spinner { width: 20px; height: 20px; border: 2px solid var(--color-border); border-top-color: var(--color-primary-500); border-radius: 50%; animation: import-spin 0.8s linear infinite; }
@keyframes import-spin { to { transform: rotate(360deg); } }
.import-result { padding: var(--space-3); background: var(--color-bg-page); border-radius: 8px; border: 1px solid var(--color-border); }
.import-result-header { display: flex; align-items: center; gap: var(--space-3); font-size: var(--text-sm); font-weight: 600; }
.result-success { color: var(--color-primary-600); }
.result-partial { color: var(--color-text-primary); }
.result-fail-count { color: var(--color-danger); }
.import-errors { margin-top: var(--space-3); max-height: 200px; overflow-y: auto; }
.import-error-item { font-size: var(--text-xs); color: var(--color-danger); padding: var(--space-1) 0; border-bottom: 1px solid var(--color-border-light); }
.import-error-item:last-child { border-bottom: none; }
.btn-cancel { height: 40px; padding: 0 var(--space-5); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
</style>
