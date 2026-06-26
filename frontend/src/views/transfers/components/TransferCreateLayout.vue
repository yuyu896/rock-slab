<script setup lang="ts">
defineProps<{
  title: string
  submitText?: string
  loading?: boolean
}>()
const emit = defineEmits<{
  (e: 'submit'): void
  (e: 'back'): void
}>()
</script>

<template>
  <div class="create-page">
    <div class="page-header">
      <button class="back-btn" @click="emit('back')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回
      </button>
      <h1 class="page-title">{{ title }}</h1>
    </div>
    <div class="form-card">
      <div class="form-body">
        <slot />
      </div>
      <div class="form-footer">
        <button class="btn-cancel" @click="emit('back')">取消</button>
        <button class="btn-confirm" @click="emit('submit')" :disabled="loading">
          {{ loading ? '提交中...' : (submitText || '确定提交') }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-page { max-width: 960px; margin: 0 auto; min-width: 0; }
.page-header { display: flex; align-items: center; gap: var(--space-4); margin-bottom: var(--space-6); }
.back-btn { display: inline-flex; align-items: center; gap: var(--space-1); height: 36px; padding: 0 var(--space-3); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-secondary); cursor: pointer; }
.back-btn:hover { color: var(--color-primary-500); border-color: var(--color-primary-300); }
.back-btn svg { width: 16px; height: 16px; }
.page-title { font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.form-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 16px; overflow: hidden; }
.form-body { padding: var(--space-6); }
.form-footer { display: flex; justify-content: flex-end; gap: var(--space-3); padding: var(--space-4) var(--space-6); border-top: 1px solid var(--color-border); }
.btn-cancel { height: 40px; padding: 0 var(--space-5); background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.btn-cancel:hover { border-color: var(--color-primary-300); }
.btn-confirm { height: 40px; padding: 0 var(--space-5); background: var(--color-primary-500); border: none; border-radius: 8px; font-size: var(--text-sm); font-weight: 500; color: white; cursor: pointer; }
.btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }

.form-body :deep(.form-grid) { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); }
.form-body :deep(.form-item) { display: flex; flex-direction: column; gap: var(--space-2); }
.form-body :deep(.form-item.full) { grid-column: span 2; }
.form-body :deep(.form-label) { font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
.form-body :deep(.required) { color: var(--color-danger); }
.form-body :deep(.form-input),
.form-body :deep(.form-select) { height: 40px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); }
.form-body :deep(.form-textarea) { padding: var(--space-3); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); font-size: var(--text-sm); resize: vertical; }
@media (max-width: 768px) { .form-body :deep(.form-grid) { grid-template-columns: 1fr; } }
</style>
