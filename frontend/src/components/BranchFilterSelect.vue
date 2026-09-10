<script setup lang="ts">
import { ElSelect, ElOption } from 'element-plus'

/**
 * 分公司筛选共用组件：可键入搜索（名称包含匹配）、一键清空；内置「全部分公司」空值项。
 * 值语义与原生下拉一致：'' = 不过滤，其余 = 分公司名；options 由父级传（数据源与权限口径在父级）。
 */
defineProps<{
  modelValue: string
  options: { value: string; label: string }[]
  /** 空值项文案（默认「全部分公司」；调拨/领用列表按调出/调入语义定制） */
  allLabel?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()
</script>

<template>
  <ElSelect
    :model-value="modelValue"
    filterable
    clearable
    :placeholder="allLabel ?? '全部分公司'"
    class="branch-filter-select"
    @update:model-value="(v) => emit('update:modelValue', v ?? '')"
    @clear="emit('update:modelValue', '')"
  >
    <ElOption value="" :label="allLabel ?? '全部分公司'" />
    <ElOption v-for="opt in options" :key="opt.value" :value="opt.value" :label="opt.label" />
  </ElSelect>
</template>

<style scoped>
.branch-filter-select { width: 180px; }
.branch-filter-select :deep(.el-select__wrapper) {
  min-height: 38px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: none;
  font-size: var(--text-sm);
  cursor: pointer;
}
.branch-filter-select :deep(.el-select__wrapper.is-focused) { border-color: var(--color-primary-400); }
.branch-filter-select :deep(.el-select__wrapper.is-hovering:not(.is-focused)) { border-color: var(--color-primary-300); }
.branch-filter-select :deep(.el-select__selection) { color: var(--color-text-primary); }
.branch-filter-select :deep(.el-select__placeholder) { color: var(--color-text-secondary); }
</style>
