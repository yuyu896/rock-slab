<script setup lang="ts">
import { ref } from 'vue'
import { importAssets } from '@/api/assets'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'

defineProps<{ visible: boolean }>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'success'): void
}>()

const importFile = ref<File | null>(null)

function downloadTemplate() {
  const link = document.createElement('a')
  link.href = '/xx分公司行政资产盘点系统-模版.xlsx'
  link.download = 'xx分公司行政资产盘点系统-模版.xlsx'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0) {
    importFile.value = files[0]
  }
}

async function confirmImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择要导入的文件')
    return
  }
  try {
    const { data } = await importAssets(importFile.value)
    ElMessage.success(`导入成功：${data.imported}条`)
    emit('success')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content import-modal">
      <div class="modal-header">
        <h3 class="modal-title">模板导入</h3>
        <button class="modal-close" @click="emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <div class="download-section">
          <span class="download-text">请先下载导入模板</span>
          <button class="download-btn" @click="downloadTemplate">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            下载模板
          </button>
        </div>
        <div class="upload-area">
          <div class="upload-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <p class="upload-text">将文件拖拽到此处，或 <span class="upload-link">点击上传</span></p>
          <p class="upload-hint">支持 .xlsx, .xls 格式，单次最多 1000 条</p>
          <input type="file" accept=".xlsx,.xls" class="upload-input" @change="onFileChange" />
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-cancel" @click="emit('close')">取消</button>
        <button class="btn-confirm" @click="confirmImport">确认导入</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-card); border-radius: 16px; overflow: hidden; }
.import-modal { width: 500px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: var(--space-5); border-bottom: 1px solid var(--color-border); }
.modal-title { font-size: var(--text-lg); font-weight: 600; margin: 0; }
.modal-close { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; border-radius: 8px; color: var(--color-text-tertiary); cursor: pointer; }
.modal-close svg { width: 18px; height: 18px; }
.modal-body { padding: var(--space-5); }
.modal-footer { display: flex; justify-content: flex-end; gap: var(--space-3); padding: var(--space-5); border-top: 1px solid var(--color-border); }
.download-section { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4); background: var(--color-bg-page); border-radius: 8px; margin-bottom: var(--space-4); }
.download-text { font-size: var(--text-sm); color: var(--color-text-secondary); }
.download-btn { display: flex; align-items: center; gap: var(--space-2); background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 6px; padding: var(--space-2) var(--space-3); color: var(--color-primary-600); font-size: var(--text-sm); cursor: pointer; }
.download-btn svg { width: 16px; height: 16px; }
.upload-area { border: 2px dashed var(--color-border); border-radius: 12px; padding: var(--space-8); text-align: center; position: relative; }
.upload-input { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
.upload-icon { width: 48px; height: 48px; margin: 0 auto var(--space-4); background: var(--color-primary-50); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--color-primary-500); }
.upload-icon svg { width: 24px; height: 24px; }
.upload-text { font-size: var(--text-sm); color: var(--color-text-primary); margin-bottom: var(--space-2); }
.upload-link { color: var(--color-primary-500); cursor: pointer; }
.upload-hint { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.btn-cancel { height: 40px; padding: 0 var(--space-5); border-radius: 8px; font-size: var(--text-sm); font-weight: 500; cursor: pointer; background: var(--color-bg-card); border: 1px solid var(--color-border); color: var(--color-text-primary); }
.btn-confirm { height: 40px; padding: 0 var(--space-5); border-radius: 8px; font-size: var(--text-sm); font-weight: 500; cursor: pointer; background: var(--color-primary-500); border: none; color: white; }
</style>
