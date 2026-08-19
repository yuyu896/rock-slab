<script setup lang="ts">
import { useId } from 'vue'
import { DEPARTMENT_PRESETS } from '@/constants'

defineProps<{
  modelValue?: string
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const listId = useId()
</script>

<template>
  <input
    :value="modelValue ?? ''"
    :list="listId"
    type="text"
    class="dept-input"
    :placeholder="placeholder || '选择或输入部门'"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
  <datalist :id="listId">
    <option v-for="d in DEPARTMENT_PRESETS" :key="d" :value="d" />
  </datalist>
</template>

<style scoped>
.dept-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 14px;
  background: var(--color-bg-page);
  outline: none;
  box-sizing: border-box;
  color: var(--color-text-primary);
}

.dept-input:focus {
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}
</style>
