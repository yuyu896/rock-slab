<script setup lang="ts">
import { ref, watch } from 'vue'

export interface FilterField {
  key: string
  label: string
  type: 'select' | 'input' | 'date-range'
  options?: { label: string; value: string | number }[]
  placeholder?: string
}

const props = defineProps<{
  fields: FilterField[]
  modelValue: Record<string, any>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: Record<string, any>): void
  (e: 'search'): void
  (e: 'reset'): void
}>()

const filters = ref<Record<string, any>>({ ...props.modelValue })

watch(() => props.modelValue, (val) => {
  filters.value = { ...val }
}, { deep: true })

function handleSearch() {
  emit('update:modelValue', { ...filters.value })
  emit('search')
}

function handleReset() {
  filters.value = {}
  emit('update:modelValue', {})
  emit('reset')
}
</script>

<template>
  <div class="filter-panel">
    <div class="filter-fields">
      <template v-for="field in fields" :key="field.key">
        <el-select
          v-if="field.type === 'select'"
          v-model="filters[field.key]"
          :placeholder="field.placeholder || field.label"
          clearable
          style="width: 160px"
        >
          <el-option
            v-for="opt in field.options"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <el-input
          v-else-if="field.type === 'input'"
          v-model="filters[field.key]"
          :placeholder="field.placeholder || field.label"
          clearable
          style="width: 200px"
        />

        <el-date-picker
          v-else-if="field.type === 'date-range'"
          v-model="filters[field.key]"
          type="daterange"
          range-separator="-"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px"
        />
      </template>
    </div>
    <div class="filter-actions">
      <el-button type="primary" @click="handleSearch">搜索</el-button>
      <el-button @click="handleReset">重置</el-button>
    </div>
  </div>
</template>

<style scoped>
.filter-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding: 16px 0;
}
.filter-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}
.filter-actions {
  display: flex;
  gap: 8px;
}
</style>
