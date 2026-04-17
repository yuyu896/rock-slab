<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as auditApi from '@/api/audit'
import type { AuditLog, AuditLogStats } from '@/api/audit'
import BasePagination from '@/components/BasePagination.vue'

const loading = ref(false)
const logs = ref<AuditLog[]>([])
const statistics = ref<AuditLogStats[]>([])
const actionStats = ref<any[]>([])
const resourceStats = ref<any[]>([])

const filters = ref({
  action: '',
  resourceType: '',
  isSuccess: undefined as boolean | undefined,
  dateRange: [] as string[],
  search: '',
})

const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const actionOptions = [
  { label: '全部', value: '' },
  { label: '登录', value: 'login' },
  { label: '登出', value: 'logout' },
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '审批通过', value: 'approve' },
  { label: '审批驳回', value: 'reject' },
  { label: '导出', value: 'export' },
  { label: '导入', value: 'import' },
]

const actionColors: Record<string, string> = {
  login: 'var(--color-success)',
  logout: 'var(--color-text-tertiary)',
  create: 'var(--color-primary-500)',
  update: 'var(--color-warning)',
  delete: 'var(--color-danger)',
  approve: 'var(--color-success)',
  reject: 'var(--color-danger)',
  export: 'var(--color-info)',
  import: 'var(--color-info)',
  view: 'var(--color-text-secondary)',
}

const filteredLogs = computed(() => {
  return logs.value
})

async function fetchLogs() {
  loading.value = true
  try {
    const params: any = {
    page: page.value,
    pageSize: pageSize.value,
    ...filters.value,
    }
    if (filters.value.dateRange && filters.value.dateRange.length === 2) {
    params.startDate = filters.value.dateRange[0]
    params.endDate = filters.value.dateRange[1]
  }
    const { data } = await auditApi.getAuditLogs(params)
    logs.value = data.results || []
    total.value = data.count || 0
  } catch (error: any) {
    ElMessage.error('获取审计日志失败')
  } finally {
    loading.value = false
  }
}

async function fetchStatistics() {
  try {
    const [statsRes, actionRes, resourceRes] = await Promise.all([
      auditApi.getAuditStatistics(),
      auditApi.getAuditByAction(),
      auditApi.getAuditByResource(),
    ])
    statistics.value = statsRes.data
    actionStats.value = actionRes.data
    resourceStats.value = resourceRes.data
  } catch (error) {
    console.error('获取统计数据失败', error)
  }
}

function handleSearch() {
  page.value = 1
  fetchLogs()
}

function handleReset() {
  filters.value = {
    action: '',
    resourceType: '',
    isSuccess: undefined,
    dateRange: [],
    search: '',
  }
  page.value = 1
  fetchLogs()
}

function handlePageChange(newPage: number, newPageSize: number) {
  page.value = newPage
  pageSize.value = newPageSize
  fetchLogs()
}

function getActionColor(action: string): string {
  return actionColors[action] || 'var(--color-text-secondary)'
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  fetchLogs()
  fetchStatistics()
})
</script>

<template>
  <div class="audit-log-page">
    <!-- 统计卡片 -->
    <div class="stats-section">
      <div class="stats-card">
        <h4>操作趋势（最近7天）</h4>
        <div class="chart-placeholder">
          <div v-for="stat in statistics" :key="stat.date" class="chart-bar">
            <div class="bar" :style="{ height: `${stat.total * 2}px` }"></div>
            <span class="label">{{ stat.date.slice(5) }}</span>
          </div>
        </div>
      </div>

      <div class="stats-card">
        <h4>操作类型分布</h4>
        <div class="action-list">
          <div v-for="stat in actionStats.slice(0, 8)" :key="stat.action" class="action-item">
            <span class="action-name">{{ stat.action }}</span>
            <span class="action-count">{{ stat.count }}</span>
          </div>
        </div>
      </div>

      <div class="stats-card">
        <h4>资源类型分布</h4>
        <div class="resource-list">
          <div v-for="stat in resourceStats.slice(0, 6)" :key="stat.resourceType" class="resource-item">
            <span class="resource-name">{{ stat.resourceType }}</span>
            <span class="resource-count">{{ stat.count }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item">
          <label>操作类型</label>
          <select v-model="filters.action" @change="handleSearch">
            <option v-for="opt in actionOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="filter-item">
          <label>资源类型</label>
          <input v-model="filters.resourceType" placeholder="如 Asset, Transfer" @change="handleSearch" />
        </div>

        <div class="filter-item">
          <label>状态</label>
          <select v-model="filters.isSuccess" @change="handleSearch">
            <option :value="undefined">全部</option>
            <option :value="true">成功</option>
            <option :value="false">失败</option>
          </select>
        </div>

        <div class="filter-item">
          <label>搜索</label>
          <input v-model="filters.search" placeholder="操作人/资源名称" @keyup.enter="handleSearch" />
        </div>

        <button class="reset-btn" @click="handleReset">重置</button>
      </div>
    </div>

    <!-- 日志列表 -->
    <div class="log-table-container">
      <table class="log-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>操作人</th>
            <th>操作类型</th>
            <th>资源</th>
            <th>描述</th>
            <th>IP地址</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in filteredLogs" :key="log.id">
            <td class="time-cell">{{ formatTime(log.createdAt) }}</td>
            <td class="user-cell">
              <div class="user-info">
                <span class="user-name">{{ log.userName }}</span>
                <span class="user-phone">{{ log.userPhone }}</span>
              </div>
            </td>
            <td>
              <span class="action-tag" :style="{ background: getActionColor(log.action) }">
                {{ log.actionDisplay || log.action }}
              </span>
            </td>
            <td>
              <div class="resource-info">
                <span class="resource-type">{{ log.resourceType }}</span>
                <span class="resource-name">{{ log.resourceName || '-' }}</span>
              </div>
            </td>
            <td class="description-cell">{{ log.description || '-' }}</td>
            <td class="ip-cell">{{ log.ipAddress || '-' }}</td>
            <td>
              <span class="status-tag" :class="{ success: log.isSuccess, failed: !log.isSuccess }">
                {{ log.isSuccess ? '成功' : '失败' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="loading" class="loading-overlay">
        <span>加载中...</span>
      </div>

      <div v-if="!loading && filteredLogs.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M9 12h6m-6 4.5m4.5m6-6" />
          <circle cx="12" cy="12" r="9" />
        </svg>
        <p>暂无审计日志</p>
      </div>
    </div>

    <!-- 分页 -->
    <BasePagination
      :total="total"
      :current-page="page"
      :page-size="pageSize"
      @change="handlePageChange"
    />
  </div>
</template>

<style scoped>
.audit-log-page {
  padding: var(--space-6);
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stats-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-4);
}

.stats-card h4 {
  font-size: var(--text-sm);
  font-weight: 600;
  margin: 0 0 var(--space-3);
  color: var(--color-text-secondary);
}

.chart-placeholder {
  display: flex;
  gap: var(--space-2);
  height: 120px;
  align-items: flex-end;
}

.chart-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.chart-bar .bar {
  width: 24px;
  background: var(--color-primary-500);
  border-radius: 4px 4px 0 0;
  min-height: 4px;
}

.chart-bar .label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  margin-top: var(--space-1);
}

.action-list, .resource-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.action-item, .resource-item {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-elevated);
  border-radius: 6px;
  font-size: var(--text-sm);
}

.action-name, .resource-name {
  color: var(--color-text-primary);
}

.action-count, .resource-count {
  font-weight: 600;
  color: var(--color-primary-500);
}

.filter-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.filter-row {
  display: flex;
  gap: var(--space-4);
  align-items: flex-end;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.filter-item label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.filter-item input,
.filter-item select {
  height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-page);
  font-size: var(--text-sm);
  min-width: 120px;
}

.reset-btn {
  height: 36px;
  padding: 0 var(--space-4);
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: var(--text-sm);
  cursor: pointer;
}

.reset-btn:hover {
  background: var(--color-bg-page);
}

.log-table-container {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  min-height: 400px;
}

.log-table {
  width: 100%;
  border-collapse: collapse;
}

.log-table th {
  background: var(--color-bg-elevated);
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
}

.log-table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.time-cell {
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
}

.user-cell .user-info {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-weight: 500;
  color: var(--color-text-primary);
}

.user-phone {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.action-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: var(--text-xs);
  color: white;
}

.resource-info {
  display: flex;
  flex-direction: column;
}

.resource-type {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.resource-name {
  font-weight: 500;
}

.description-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ip-cell {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: var(--text-xs);
}

.status-tag.success {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.status-tag.failed {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
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

.pagination-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) 0;
}

.total-count {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.pagination-controls button {
  height: 32px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
  cursor: pointer;
}

.pagination-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-controls button:hover:not(:disabled) {
  background: var(--color-bg-elevated);
}

.current-page {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}
</style>
