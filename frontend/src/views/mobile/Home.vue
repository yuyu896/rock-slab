<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { useNotificationStore } from '@/store/notification'
import { getPendingTransfers, getTransfers } from '@/api/transfers'
import { getInventoryTasks } from '@/api/inventories'

const router = useRouter()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

const loading = ref(true)
const pendingApprovals = ref(0)
const pendingInventories = ref(0)

const userName = computed(() => userStore.profile?.name || '用户')
const userRole = computed(() => userStore.profile?.role || '')

const roleLabels: Record<string, string> = {
  admin: '超级管理员',
  manager: '行政经理',
  supervisor: '行政主管',
  leader: '行政组长',
  staff: '行政专员',
}

const quickActions = [
  { key: 'scan', label: '扫码查询', icon: 'scan', path: '/mobile/scan' },
  { key: 'purchase', label: '提交入库', icon: 'purchase', path: '/mobile/purchase' },
  { key: 'transfer', label: '提交调拨', icon: 'transfer', path: '/mobile/submit/transfer' },
  { key: 'assign', label: '提交领用', icon: 'assign', path: '/mobile/submit/assign' },
  { key: 'inventory', label: '盘点任务', icon: 'inventory', path: '/mobile/inventory' },
]

const statistics = ref([
  { label: '待审批', value: 0, color: 'warning' },
  { label: '待盘点', value: 0, color: 'primary' },
  { label: '今日操作', value: 0, color: 'success' },
])

async function fetchData() {
  loading.value = true
  try {
    // 获取今天日期字符串
    const today = new Date().toISOString().split('T')[0]
    const [transfersRes, inventoriesRes, todayOpsRes] = await Promise.all([
      getPendingTransfers({ pageSize: 1 }).catch(() => ({ data: { count: 0 } })),
      getInventoryTasks({ status: 'pending,in_progress', pageSize: 1 }).catch(() => ({ data: { count: 0 } })),
      getTransfers({ createdAt__gte: today, pageSize: 1 }).catch(() => ({ data: { count: 0 } })),
    ])
    pendingApprovals.value = transfersRes.data?.count || 0
    pendingInventories.value = inventoriesRes.data?.count || 0
    statistics.value[0].value = pendingApprovals.value
    statistics.value[1].value = pendingInventories.value
    statistics.value[2].value = todayOpsRes.data?.count || 0
  } finally {
    loading.value = false
  }
}

function navigateTo(path: string) {
  router.push(path)
}

onMounted(() => {
  fetchData()
  notificationStore.init()
})
</script>

<template>
  <div class="mobile-home">
    <!-- 用户信息 -->
    <div class="user-section">
      <div class="user-avatar">{{ userName.charAt(0) }}</div>
      <div class="user-info">
        <div class="user-name">{{ userName }}</div>
        <div class="user-role">{{ roleLabels[userRole] || userRole }}</div>
      </div>
      <div class="notification-badge" @click="navigateTo('/mobile/approval')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <span v-if="notificationStore.unreadCount > 0" class="badge">
          {{ notificationStore.unreadCount > 99 ? '99+' : notificationStore.unreadCount }}
        </span>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div
        v-for="stat in statistics"
        :key="stat.label"
        class="stat-card"
        :class="stat.color"
      >
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions-section">
      <h3 class="section-title">快捷操作</h3>
      <div class="quick-actions-grid">
        <button
          v-for="action in quickActions"
          :key="action.key"
          class="quick-action-btn"
          @click="navigateTo(action.path)"
        >
          <div class="action-icon">
            <!-- Scan icon -->
            <svg v-if="action.icon === 'scan'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 7V5a2 2 0 0 1 2-2h2m17 3h2a2 2 0 0 1-2 2h2M17 3h2a2 2 0 0 1-2 2h2"/>
              <line x1="7" y1="12" x2="17" y2="12"/>
            </svg>
            <!-- purchase icon -->
            <svg v-else-if="action.icon === 'purchase'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
              <line x1="12" y1="12" x2="12" y2="22"/>
              <line x1="12" y1="12" x2="21" y2="7"/>
            </svg>
            <!-- transfer icon -->
            <svg v-else-if="action.icon === 'transfer'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 1l4 4-4 4 4M7 3h2m17 3h2a2 2 0 0 1-2-2h2m17 3h2a2 2 0 0 1-2 2h2"/>
              <path d="M17 17v2a2 2 0 0 1-2-2h-2M7 3h2a2 2 0 0 1-2 2h2"/>
            </svg>
            <!-- assign icon -->
            <svg v-else-if="action.icon === 'assign'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4 4H5a73 21a2 2 0 0 1-3.46 0"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <!-- inventory icon -->
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
              <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2"/>
              <line x1="7" y1="12" x2="17" y2="12"/>
            </svg>
          </div>
          <span class="action-label">{{ action.label }}</span>
        </button>
      </div>
    </div>

    <!-- 待办事项 -->
    <div class="pending-section">
      <h3 class="section-title">待办事项</h3>
      <div v-if="pendingApprovals > 0" class="pending-item" @click="navigateTo('/mobile/approval')">
        <div class="pending-icon approval">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4.5 4.5"/>
          </svg>
        </div>
        <div class="pending-info">
          <div class="pending-title">待审批单据</div>
          <div class="pending-desc">{{ pendingApprovals }} 条待处理</div>
        </div>
        <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>

      <div v-if="pendingInventories > 0" class="pending-item" @click="navigateTo('/mobile/inventory')">
        <div class="pending-icon inventory">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
          <line x1="7" y1="12" x2="17" y2="12"/>
          </svg>
        </div>
        <div class="pending-info">
          <div class="pending-title">盘点任务</div>
          <div class="pending-desc">{{ pendingInventories }} 个进行中</div>
        </div>
        <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>

      <div v-if="pendingApprovals === 0 && pendingInventories === 0" class="empty-pending">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <p>暂无待办事项</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mobile-home {
  padding: var(--space-4);
  padding-top: var(--space-6);
}

.user-section {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}

.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
}

.user-info {
  flex: 1;
}

.user-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.user-role {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.notification-badge {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--color-bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  cursor: pointer;
}

.notification-badge svg {
  width: 22px;
  height: 22px;
  color: var(--color-text-secondary);
}

.notification-badge .badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  background: var(--color-danger);
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-4);
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 4px;
}

.stat-card.warning .stat-value {
  color: var(--color-warning);
}

.stat-card.primary .stat-value {
  color: var(--color-primary-500);
}

.stat-card.success .stat-value {
  color: var(--color-success);
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.quick-actions-section,
.pending-section {
  margin-bottom: var(--space-6);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-3);
}

.quick-action-btn {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-4) var(--space-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

.action-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--color-primary-50);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary-500);
}

.action-icon svg {
  width: 18px;
  height: 18px;
}

.action-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.pending-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  cursor: pointer;
}

.pending-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pending-icon.approval {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.pending-icon.inventory {
  background: var(--color-primary-50);
  color: var(--color-primary-500);
}

.pending-icon svg {
  width: 20px;
  height: 20px;
}

.pending-info {
  flex: 1;
}

.pending-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.pending-desc {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.arrow-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-tertiary);
}

.empty-pending {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-pending svg {
  width: 48px;
  height: 48px;
  margin-bottom: var(--space-3);
}
</style>
