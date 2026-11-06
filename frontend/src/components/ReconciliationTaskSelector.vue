<template>
  <div class="recon-task-selector">
    <template v-if="taskOptions.length > 0">
      <span class="selector-label">当前任务：</span>
      <el-select
        :model-value="currentTaskId"
        placeholder="请选择对账任务"
        filterable
        class="task-select"
        @change="handleChange"
      >
        <el-option
          v-for="opt in taskOptions"
          :key="opt.value"
          :value="opt.value"
          :label="opt.label"
        />
      </el-select>
      <span v-if="currentTask" class="version-badge">
        版本 v{{ currentTask.currentVersion ?? 1 }}
      </span>
    </template>
    <template v-else-if="loaded">
      <span class="selector-empty">请先在订单页导入供应商订单</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElSelect, ElOption } from 'element-plus'
import { useReconciliationTask } from '@/composables/useReconciliationTask'

const { currentTaskId, currentTask, taskOptions, loadTaskOptions, setTask } = useReconciliationTask()

const loaded = ref(false)

async function handleChange(id: string) {
  await setTask(id)
}

onMounted(async () => {
  await loadTaskOptions()
  loaded.value = true
})
</script>

<style scoped>
.recon-task-selector {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
  font-size: var(--text-sm);
}

.selector-label {
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.task-select {
  width: 280px;
}

.version-badge {
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-primary-100);
  color: var(--color-primary-700);
  font-size: var(--text-xs);
  font-weight: 500;
  white-space: nowrap;
}

.selector-empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
