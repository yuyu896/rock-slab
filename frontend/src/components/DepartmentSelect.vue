<script setup lang="ts">
import { ref, watch } from 'vue'
import { getDepartmentOptions, type Department } from '@/api/departments'

/**
 * 部门输入（P1）：下拉选项来自部门字典（按分公司过滤），允许自由输入字典外新值。
 * P2 随领用单绑部门 FK 化时收紧为强约束。
 */
const props = defineProps<{
  modelValue?: string
  branch?: string
  branchId?: string
  placeholder?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const options = ref<Department[]>([])
const listId = `dept-list-${Math.random().toString(36).slice(2, 8)}`

watch(
  () => [props.branch, props.branchId],
  async () => {
    if (!props.branch && !props.branchId) {
      options.value = []
      return
    }
    try {
      const { data } = await getDepartmentOptions({
        branch: props.branch || undefined,
        branch_id: props.branchId || undefined,
      })
      options.value = data
    } catch {
      options.value = []
    }
  },
  { immediate: true },
)

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
