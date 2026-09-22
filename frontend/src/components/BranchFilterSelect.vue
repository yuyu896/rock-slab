<script setup lang="ts">
import { computed } from 'vue'
import { ElSelect, ElOption } from 'element-plus'
import { sortBranchesByName } from '@/utils/sortBranchesByName'

/**
 * 分公司筛选共用组件（多选，branch-order-and-multi-filter）：
 * 可键入搜索、一键清空；值语义 string[]，空数组 = 不过滤；选项按名称拼音排序。
 * options 由父级传（数据源与权限口径在父级），值口径沿各页现状（名称/编号/id）。
 */
const props = defineProps<{
  modelValue: string[]
  options: { value: string; label: string }[]
  /** 空值提示文案（默认「全部分公司」；调拨/领用列表按调出/调入语义定制） */
  allLabel?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string[]): void }>()

const sortedOptions = computed(() => sortBranchesByName(props.options))
</script>

<template>
  <ElSelect
    :model-value="modelValue"
    multiple
    collapse-tags
    collapse-tags-tooltip
    filterable
    clearable
    :placeholder="allLabel ?? '全部分公司'"
    class="branch-filter-select"
    @update:model-value="(v) => emit('update:modelValue', v ?? [])"
    @clear="emit('update:modelValue', [])"
  >
    <ElOption v-for="opt in sortedOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
  </ElSelect>
</template>

<style scoped>
.branch-filter-select { width: 220px; }
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
