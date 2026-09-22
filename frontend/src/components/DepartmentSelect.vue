<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDepartmentOptions, type Department } from '@/api/departments'

/**
 * 部门输入：下拉选项来自全集团扁平部门字典（department-dictionary-flatten），
 * 允许自由输入字典外新值（P1 口径）。
 */
const props = defineProps<{
  modelValue?: string
  placeholder?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const options = ref<Department[]>([])
const listId = `dept-list-${Math.random().toString(36).slice(2, 8)}`

onMounted(async () => {
  try {
    const { data } = await getDepartmentOptions()
    options.value = data
  } catch {
    options.value = []
  }
})

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="dept-select">
    <input
      :value="modelValue ?? ''"
      :list="listId"
      type="text"
      class="dept-input"
      :placeholder="placeholder || '选择或输入部门'"
      @input="onInput"
    />
    <datalist :id="listId">
      <option v-for="d in options" :key="d.id" :value="d.name" />
    </datalist>
  </div>
</template>

<style scoped>
.dept-select {
  width: 100%;
}

.dept-select .form-input,
.dept-select input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  font-size: var(--text-sm);
  background: var(--color-bg-elevated);
  outline: none;
  box-sizing: border-box;
}

.dept-select input:focus {
  border-color: var(--color-primary-400);
}
</style>
