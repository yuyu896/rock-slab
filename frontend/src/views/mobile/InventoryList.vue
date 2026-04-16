<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getInventoryTasks } from '@/api/inventories'
import { ElMessage } from 'element-plus'

const router = useRouter()
const tasks = ref<any[]>([])
const loading = ref(false)
const activeTab = ref<'in_progress' | 'pending' | 'completed'>('in_progress')

const statusLabels: Record<string, string> = {
  pending: '待盘点',
  in_progress: '盘点中',
  pending_review: '待审核',
  completed: '已完成',
  rejected: '已驳回',
  cancelled: '已作废',
}

const statusColors: Record<string, string> = {
  pending: 'var(--color-text-tertiary)',
  in_progress: 'var(--color-primary-500)',
  pending_review: 'var(--color-warning)',
  completed: 'var(--color-success)',
  rejected: 'var(--color-danger)',
  cancelled: 'var(--color-text-tertiary)',
}

async function fetchTasks() {
  loading.value = true
  try {
    const statusMap: Record<string, string> = {
      in_progress: 'pending,in_progress',
      pending: 'pending_review',
      completed: 'completed,rejected,cancelled',
    }
    const { data } = await getInventoryTasks({
      status: statusMap[activeTab.value],
      pageSize: 50,
    })
    tasks.value = data.results || []
  } catch (error) {
    ElMessage.error('获取盘点任务失败')
  } finally {
    loading.value = false
  }
}

function startInventory(task: any) {
  router.push(`/mobile/inventory/${task.id}`)
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  fetchTasks()
})
</script>

<template>
  <div class="inventory-list-page">
    <div class="page-header">
      <h1>盘点任务</h1>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button :class="{ active: activeTab === 'in_progress' }" @click="activeTab = 'in_progress'; fetchTasks()">
        进行中
      </button>
      <button :class="{ active: activeTab === 'pending' }" @click="activeTab = 'pending'; fetchTasks()">
        待审核
      </button>
      <button :class="{ active: activeTab === 'completed' }" @click="activeTab = 'completed'; fetchTasks()">
        已完成
      </button>
    </div>

    <!-- 任务列表 -->
    <div class="task-list">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="task-card"
        @click="startInventory(task)"
      >
        <div class="task-header">
          <span class="task-status" :style="{ color: statusColors[task.status] }">
            {{ statusLabels[task.status] }}
          </span>
          <span class="task-date">{{ formatDate(task.createdAt) }}</span>
        </div>
        <div class="task-body">
          <h3 class="task-name">{{ task.name }}</h3>
          <p class="task-branch">{{ task.branchName || '全部分公司' }}</p>
        </div>
        <div class="task-footer">
          <div class="progress-info">
            <span class="progress-text">{{ task.checkedCount || 0 }} / {{ task.totalCount || 0 }}</span>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{
                  width: `${task.totalCount ? (task.checkedCount / task.totalCount * 100) : 0}%`,
                  background: statusColors[task.status]
                }"
              />
            </div>
          </div>
          <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </div>
      </div>

      <div v-if="!tasks.length && !loading" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
        </svg>
        <p>暂无盘点任务</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inventory-list-page {
  padding: var(--space-4);
}

.page-header {
  margin-bottom: var(--space-4);
}

.page-header h1 {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.tab-bar {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.tab-bar button {
  flex: 1;
  height: 40px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.tab-bar button.active {
  background: var(--color-primary-500);
  color: white;
}

.task-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  cursor: pointer;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.task-status {
  font-size: 12px;
  font-weight: 500;
}

.task-date {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.task-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin: 0;
}

.task-branch {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 4px 0 0;
}

.task-footer {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.progress-info {
  flex: 1;
}

.progress-text {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.progress-bar {
  height: 4px;
  background: var(--color-bg-elevated);
  border-radius: 2px;
  margin-top: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s;
}

.arrow-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-tertiary);
}

.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin-bottom: var(--space-3);
}
</style>
