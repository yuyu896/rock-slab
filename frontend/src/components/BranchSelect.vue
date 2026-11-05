<script setup lang="ts">
import { ElOption, ElSelect } from 'element-plus'

defineProps<{
  modelValue: string
  options: { value: string; label: string }[]
  placeholder?: string
}>()

const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()
</script>

<template>
  <ElSelect
    :model-value="modelValue"
    filterable
    clearable
    :placeholder="placeholder ?? '请选择分公司'"
    class="branch-select"
    @update:model-value="(value) => emit('update:modelValue', value ?? '')"
  >
    <ElOption
      v-for="option in options"
      :key="option.value"
      :label="option.label"
      :value="option.value"
    />
  </ElSelect>
</template>

<style scoped>
.branch-select { width: 100%; }
.branch-select :deep(.el-select__wrapper) {
  box-sizing: border-box;
  height: 40px;
  min-height: 40px;
  border-radius: 8px;
  background: var(--color-bg-page);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  font-size: var(--text-sm);
}
.branch-select :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--color-primary-400) inset;
}
</style>
