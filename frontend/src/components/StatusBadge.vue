<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  status: string
  statusMap?: Record<string, { label: string; type: 'success' | 'warning' | 'danger' | 'info' | 'primary' }>
}>(), {
  statusMap: () => ({
    '在库': { label: '在库', type: 'success' },
    '使用中': { label: '使用中', type: 'primary' },
    '维修中': { label: '维修中', type: 'warning' },
    '报废': { label: '报废', type: 'danger' },
    '待审批': { label: '待审批', type: 'warning' },
    '已通过': { label: '已通过', type: 'success' },
    '已驳回': { label: '已驳回', type: 'danger' },
    active: { label: '启用', type: 'success' },
    inactive: { label: '停用', type: 'info' },
  }),
})

const config = computed(() => {
  return props.statusMap[props.status] || { label: props.status, type: 'info' as const }
})
</script>

<template>
  <el-tag :type="config.type" size="small" effect="light">
    {{ config.label }}
  </el-tag>
</template>
