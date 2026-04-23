<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getOverview, getByBranch, getByStatus } from '@/api/reports'
import { getTransfers } from '@/api/transfers'
import { getInventoryTasks } from '@/api/inventories'
import { useUserStore } from '@/store/user'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { BranchStat, StatusStat } from '@/types'

const router = useRouter()
const userStore = useUserStore()

// 加载状态
const loading = ref(false)

const stats = ref({
  totalAssets: 0,
  activeAssets: 0,
  pendingApproval: 0,
  lowStock: 0,
  growthRate: 0,
  pendingInventory: 0,
})

const categoryDistribution = ref<StatusStat[]>([])
const categoryStats = ref<{category: string; count: number; percentage: number}[]>([])
const branchStats = ref<BranchStat[]>([])
const pendingTasks = ref<any[]>([])
const pendingInventoryTasks = ref<any[]>([])
const recentActivities = ref<any[]>([])

// 根据用户角色构建数据范围参数
function buildScopeParams(): Record<string, string> {
  const user = userStore.profile
  if (!user) return {}
  const role = user.role
  if (role === 'admin' || role === 'manager') return {}
  if (role === 'supervisor') {
    return user.region ? { region: user.region } : {}
  }
  // leader / staff
  return user.branch ? { branch: user.branch } : {}
}

// 动态问候语
function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return '凌晨好'
  if (hour < 9) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}

// 动态日期
function getDateString(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  const day = now.getDate()
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  const weekday = weekdays[now.getDay()]
  return `${year}年${month}月${day}日 星期${weekday}`
}

// 获取待办任务真实类型名称
function getTransferTypeName(actionType?: string): string {
  const typeMap: Record<string, string> = {
    assign: '领用出库',
    return: '资产归还',
    transfer: '调拨申请',
  }
  return typeMap[actionType || ''] || '流转单据'
}

// 获取仪表板数据
async function fetchDashboardData() {
  loading.value = true
  try {
    const scope = buildScopeParams()
    const [overviewRes, branchRes, statusRes, transfersRes, inventoriesRes] = await Promise.all([
      getOverview(scope),
      getByBranch(scope),
      getByStatus(scope),
      getTransfers({ status: '待审批', pageSize: 5, ...scope }),
      getInventoryTasks({ status: 'pending,in_progress', pageSize: 5, ...scope }).catch(() => ({ data: { count: 0, results: [] } })),
    ])
    const overview = overviewRes.data
    stats.value = {
      totalAssets: overview.totalAssets,
      activeAssets: Math.floor(overview.totalAssets * overview.activeRate / 100),
      pendingApproval: overview.pendingApproval || transfersRes.data.count || 0,
      lowStock: overview.lowStockCount || 0,
      growthRate: overview.growthRate || 0,
      pendingInventory: overview.pendingInventory || inventoriesRes.data?.count || 0,
    }
    branchStats.value = branchRes.data.slice(0, 5)
    categoryDistribution.value = statusRes.data
    categoryStats.value = []

    // 待办任务：来自流转记录
    const transferTasks = transfersRes.data.results?.slice(0, 4).map((t: any) => ({
      id: t.id,
      type: getTransferTypeName(t.action_type),
      title: t.调出分公司 && t.调入分公司
        ? `${t.调出分公司}→${t.调入分公司} ${t.资产名称}`
        : `${t.资产名称} ${t.调拨数量}件`,
      submitter: t.创建人,
      time: t.createdAt,
      actionType: t.action_type,
    })) || []

    // 待办任务：来自盘点任务
    const inventoryTasks = inventoriesRes.data?.results?.slice(0, 2).map((t: any) => ({
      id: t.id,
      type: '资产盘点',
      title: t.name,
      submitter: t.createdBy,
      time: t.createdAt,
      actionType: 'inventory',
    })) || []

    pendingTasks.value = [...transferTasks, ...inventoryTasks]
    pendingInventoryTasks.value = inventoriesRes.data?.results || []

    recentActivities.value = transfersRes.data.results?.slice(0, 5).map((t: any) => ({
      id: t.id,
      action: getTransferTypeName(t.action_type).replace('申请', '').replace('出库', '').replace('归还', '归还'),
      asset: t.资产名称,
      branch: t.调出分公司 && t.调入分公司 ? `${t.调出分公司}→${t.调入分公司}` : '',
      time: t.createdAt,
    })) || []
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

const maxBranchValue = computed(() => {
  if (branchStats.value.length === 0) return 1
  return Math.max(...branchStats.value.map(d => d.value))
})
const totalCategoryValue = computed(() => categoryDistribution.value.reduce((sum: number, d) => sum + d.count, 0))
const totalAssetCategoryValue = computed(() => categoryStats.value.reduce((sum: number, d) => sum + d.count, 0))

// 分类颜色
const categoryColors: Record<string, string> = {
  '固定资产类': 'var(--color-primary-500)',
  '低值易耗品类': 'var(--color-success)',
  '无形资产类': 'var(--color-warning)',
  '文档资料类': '#8b5cf6',
  '特殊设备类': '#f97316',
  '其他资产': 'var(--color-text-tertiary)',
}

// 状态颜色映射
const statusColors: Record<string, string> = {
  '在库': 'var(--color-primary-500)',
  '使用中': 'var(--color-success)',
  '维修中': 'var(--color-warning)',
  '报废': 'var(--color-danger)',
}

const getTaskTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    '采购入库': 'var(--color-success)',
    '领用出库': 'var(--color-warning)',
    '资产盘点': 'var(--color-info)',
    '调拨申请': 'var(--color-primary-500)',
    '资产归还': '#06b6d4',
  }
  return colors[type] || 'var(--color-text-tertiary)'
}

const getActionColor = (action: string) => {
  const colors: Record<string, string> = {
    '入库': 'var(--color-success)',
    '出库': 'var(--color-warning)',
    '调拨': 'var(--color-primary-500)',
    '盘点': 'var(--color-info)',
    '归还': '#06b6d4',
  }
  return colors[action] || 'var(--color-text-tertiary)'
}

// 获取用户名
const userName = computed(() => userStore.profile?.name || '用户')

// 格式化增长率
const growthDisplay = computed(() => {
  const rate = stats.value.growthRate
  if (rate > 0) return `+${rate.toFixed(1)}%`
  if (rate < 0) return `${rate.toFixed(1)}%`
  return '0%'
})

// 导航函数
function goToPendingApprovals() {
  router.push('/assets/transfer')
}

function goToTransferList() {
  router.push('/assets/transfer')
}

function goToInventory() {
  router.push('/inventory')
}

function handleTask(task: any) {
  if (task.actionType === 'inventory') {
    router.push(`/inventory`)
  } else {
    router.push('/assets/transfer')
  }
}

function goToReports() {
  router.push('/reports')
}

// 初始化
onMounted(() => {
  fetchDashboardData()
})
</script>

<template>
  <div class="dashboard">
    <div class="welcome-section">
      <div class="welcome-content">
        <h1 class="welcome-title">{{ getGreeting() }}，{{ userName }}</h1>
        <p class="welcome-subtitle">今天是{{ getDateString() }}，您有{{ pendingTasks.length }}项待办事项需要处理</p>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon assets"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.totalAssets.toLocaleString() }}</span>
          <span class="stat-label">资产总数</span>
        </div>
        <div class="stat-trend" :class="{ up: stats.growthRate >= 0, down: stats.growthRate < 0 }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg>
          <span>{{ growthDisplay }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon active"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.activeAssets.toLocaleString() }}</span>
          <span class="stat-label">使用中</span>
        </div>
        <div class="stat-percentage">{{ stats.totalAssets ? Math.round(stats.activeAssets / stats.totalAssets * 100) : 0 }}%</div>
      </div>

      <div class="stat-card clickable" @click="goToPendingApprovals">
        <div class="stat-icon pending"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.pendingApproval }}</span>
          <span class="stat-label">待审批</span>
        </div>
        <div class="stat-arrow"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></div>
      </div>

      <div class="stat-card warning">
        <div class="stat-icon warning"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
        <div class="stat-content">
          <span class="stat-value">{{ stats.lowStock }}</span>
          <span class="stat-label">库存不足</span>
        </div>
        <div class="stat-badge">需关注</div>
      </div>
    </div>

    <div class="main-grid">
      <div class="card distribution-card">
        <div class="card-header">
          <h3 class="card-title">资产状态分布</h3>
        </div>
        <div class="card-body">
          <div class="distribution-list">
            <div v-for="item in categoryDistribution" :key="item.status" class="distribution-item">
              <div class="distribution-header">
                <span class="distribution-name">{{ item.status }}</span>
                <span class="distribution-value">{{ item.count.toLocaleString() }}</span>
              </div>
              <div class="distribution-bar">
                <div class="distribution-fill" :style="{ width: totalCategoryValue ? (item.count / totalCategoryValue * 100) + '%' : '0%', background: statusColors[item.status] || 'var(--color-primary-500)' }" />
              </div>
              <span class="distribution-percent">{{ totalCategoryValue ? (item.count / totalCategoryValue * 100).toFixed(1) : 0 }}%</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card tasks-card">
        <div class="card-header">
          <h3 class="card-title">待办任务</h3>
          <a class="card-link" @click="goToTransferList">查看全部</a>
        </div>
        <div class="card-body">
          <div class="tasks-list">
            <div v-for="task in pendingTasks" :key="task.id" class="task-item" @click="handleTask(task)">
              <div class="task-indicator" :style="{ background: getTaskTypeColor(task.type) }" />
              <div class="task-content">
                <div class="task-type">{{ task.type }}</div>
                <div class="task-title">{{ task.title }}</div>
                <div class="task-meta"><span>{{ task.submitter }}</span><span class="dot">·</span><span>{{ task.time }}</span></div>
              </div>
              <button class="task-action" @click.stop="handleTask(task)">处理</button>
            </div>
            <div v-if="pendingTasks.length === 0" class="tasks-empty">
              <span>暂无待办任务</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="categoryStats.length > 0" class="card category-card">
        <div class="card-header">
          <h3 class="card-title">资产类目分布</h3>
          <a class="card-link" @click="goToReports">查看详情</a>
        </div>
        <div class="card-body">
          <div class="distribution-list">
            <div v-for="item in categoryStats" :key="item.category" class="distribution-item">
              <div class="distribution-header">
                <span class="distribution-name">{{ item.category }}</span>
                <span class="distribution-value">{{ item.count.toLocaleString() }}</span>
              </div>
              <div class="distribution-bar">
                <div class="distribution-fill" :style="{ width: totalAssetCategoryValue ? (item.count / totalAssetCategoryValue * 100) + '%' : '0%', background: categoryColors[item.category] || 'var(--color-primary-500)' }" />
              </div>
              <span class="distribution-percent">{{ totalAssetCategoryValue ? (item.count / totalAssetCategoryValue * 100).toFixed(1) : 0 }}%</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card branches-card">
        <div class="card-header">
          <h3 class="card-title">分公司资产排行</h3>
          <a class="card-link" @click="goToReports">查看更多</a>
        </div>
        <div class="card-body">
          <div class="branches-list">
            <div v-for="(branch, index) in branchStats" :key="branch.name" class="branch-item">
              <span class="branch-rank" :class="{ top: index < 3 }">{{ index + 1 }}</span>
              <div class="branch-info">
                <span class="branch-name">{{ branch.name }}</span>
                <div class="branch-bar"><div class="branch-fill" :style="{ width: (branch.value / maxBranchValue * 100) + '%' }" /></div>
              </div>
              <div class="branch-stats">
                <span class="branch-total">{{ branch.value.toLocaleString() }}</span>
                <span class="branch-active">占比 {{ branch.percentage }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="activity-section">
      <div class="section-header">
        <h3 class="section-title">最近动态</h3>
        <a class="section-link" @click="goToTransferList">查看全部</a>
      </div>
      <div class="activity-list">
        <div v-for="activity in recentActivities" :key="activity.id" class="activity-item">
          <div class="activity-dot" :style="{ background: getActionColor(activity.action) }" />
          <div class="activity-content">
            <span class="activity-action" :style="{ color: getActionColor(activity.action) }">{{ activity.action }}</span>
            <span class="activity-asset">{{ activity.asset }}</span>
            <span class="activity-branch">{{ activity.branch }}</span>
          </div>
          <span class="activity-time">{{ activity.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1400px; margin: 0 auto; }
.welcome-section { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-6); }
.welcome-title { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); margin: 0 0 var(--space-2) 0; }
.welcome-subtitle { font-size: var(--text-base); color: var(--color-text-secondary); margin: 0; }
.welcome-actions { display: flex; gap: var(--space-3); }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); margin-bottom: var(--space-6); }
.stat-card { background: var(--color-bg-card); border-radius: 12px; padding: var(--space-5); display: flex; align-items: center; gap: var(--space-4); border: 1px solid var(--color-border); transition: all var(--transition-fast); }
.stat-card:hover { box-shadow: var(--shadow-sm); transform: translateY(-2px); }
.stat-card.clickable { cursor: pointer; }
.stat-card.warning { background: linear-gradient(135deg, var(--color-bg-card) 0%, oklch(0.98 0.03 85) 100%); border-color: oklch(0.85 0.06 85); }
.stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.stat-icon svg { width: 24px; height: 24px; }
.stat-icon.assets { background: var(--color-primary-100); color: var(--color-primary-600); }
.stat-icon.active { background: oklch(0.92 0.08 145); color: var(--color-success); }
.stat-icon.pending { background: oklch(0.94 0.06 85); color: var(--color-warning); }
.stat-icon.warning { background: oklch(0.92 0.10 25); color: var(--color-danger); }
.stat-content { flex: 1; display: flex; flex-direction: column; }
.stat-value { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); line-height: 1.2; }
.stat-label { font-size: var(--text-sm); color: var(--color-text-tertiary); margin-top: var(--space-1); }
.stat-trend { display: flex; align-items: center; gap: var(--space-1); font-size: var(--text-sm); font-weight: 500; }
.stat-trend.up { color: var(--color-success); }
.stat-trend.down { color: var(--color-danger); }
.stat-trend svg { width: 16px; height: 16px; }
.stat-percentage { font-size: var(--text-lg); font-weight: 600; color: var(--color-success); }
.stat-arrow { width: 32px; height: 32px; border-radius: 8px; background: var(--color-bg-elevated); display: flex; align-items: center; justify-content: center; color: var(--color-text-tertiary); }
.stat-arrow svg { width: 18px; height: 18px; }
.stat-badge { background: oklch(0.92 0.10 25); color: var(--color-danger); font-size: var(--text-xs); font-weight: 600; padding: var(--space-1) var(--space-2); border-radius: 6px; }
.main-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-4); margin-bottom: var(--space-6); }
.card { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); }
.card-header { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--color-border); }
.card-title { font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.card-link { font-size: var(--text-sm); color: var(--color-primary-500); cursor: pointer; text-decoration: none; }
.card-link:hover { color: var(--color-primary-600); }
.card-body { padding: var(--space-5); }
.distribution-list { display: flex; flex-direction: column; gap: var(--space-4); }
.distribution-item { display: grid; grid-template-columns: 1fr 2fr 60px; align-items: center; gap: var(--space-3); }
.distribution-header { display: flex; justify-content: space-between; }
.distribution-name { font-size: var(--text-sm); color: var(--color-text-secondary); }
.distribution-value { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.distribution-bar { height: 8px; background: var(--color-bg-elevated); border-radius: 4px; overflow: hidden; }
.distribution-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease-out; }
.distribution-percent { font-size: var(--text-sm); color: var(--color-text-tertiary); text-align: right; }
.tasks-list { display: flex; flex-direction: column; gap: var(--space-3); }
.tasks-empty { text-align: center; padding: var(--space-6) 0; color: var(--color-text-tertiary); font-size: var(--text-sm); }
.task-item { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); border-radius: 8px; background: var(--color-bg-page); transition: all var(--transition-fast); cursor: pointer; }
.task-item:hover { background: var(--color-bg-elevated); }
.task-indicator { width: 4px; height: 40px; border-radius: 2px; flex-shrink: 0; }
.task-content { flex: 1; min-width: 0; }
.task-type { font-size: var(--text-xs); color: var(--color-text-tertiary); margin-bottom: var(--space-1); }
.task-title { font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-meta { font-size: var(--text-xs); color: var(--color-text-tertiary); margin-top: var(--space-1); }
.task-meta .dot { margin: 0 var(--space-1); }
.task-action { padding: var(--space-2) var(--space-4); font-size: var(--text-sm); font-weight: 500; color: var(--color-primary-500); background: var(--color-primary-50); border: none; border-radius: 6px; cursor: pointer; }
.task-action:hover { background: var(--color-primary-100); color: var(--color-primary-600); }
.branches-list { display: flex; flex-direction: column; gap: var(--space-3); }
.branch-item { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); border-radius: 8px; transition: background var(--transition-fast); }
.branch-item:hover { background: var(--color-bg-page); }
.branch-rank { width: 24px; height: 24px; border-radius: 6px; background: var(--color-bg-elevated); color: var(--color-text-tertiary); font-size: var(--text-sm); font-weight: 600; display: flex; align-items: center; justify-content: center; }
.branch-rank.top { background: var(--color-primary-500); color: white; }
.branch-info { flex: 1; min-width: 0; }
.branch-name { font-size: var(--text-sm); color: var(--color-text-primary); display: block; margin-bottom: var(--space-2); }
.branch-bar { height: 6px; background: var(--color-bg-elevated); border-radius: 3px; overflow: hidden; }
.branch-fill { height: 100%; background: var(--color-primary-400); border-radius: 3px; transition: width 0.5s ease-out; }
.branch-stats { text-align: right; }
.branch-total { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); display: block; }
.branch-active { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.activity-section { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); padding: var(--space-5); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4); }
.section-title { font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); margin: 0; }
.section-link { font-size: var(--text-sm); color: var(--color-primary-500); cursor: pointer; }
.activity-list { display: flex; flex-direction: column; }
.activity-item { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-3) 0; border-bottom: 1px solid var(--color-border-light); }
.activity-item:last-child { border-bottom: none; }
.activity-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.activity-content { flex: 1; display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); }
.activity-action { font-weight: 500; }
.activity-asset { color: var(--color-text-primary); }
.activity-branch { color: var(--color-text-tertiary); }
.activity-time { font-size: var(--text-sm); color: var(--color-text-tertiary); }
@media (max-width: 1200px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } .main-grid { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .welcome-section { flex-direction: column; align-items: flex-start; gap: var(--space-4); } .stats-grid { grid-template-columns: 1fr; } }
</style>
