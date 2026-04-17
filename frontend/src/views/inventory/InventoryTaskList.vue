<script setup lang="ts">
import { computed } from 'vue'
import {
  INVENTORY_STATUS_OPTIONS,
  INVENTORY_STATUS_COLORS,
  INVENTORY_STATUS_MAP,
  MISSED_RULE_LABELS,
  REPEAT_RULE_LABELS,
} from '@/constants'
import type { MissedRuleType, RepeatRuleType } from '@/types'

const props = defineProps<{
  loading: boolean
  tasks: any[]
  stats: { total: number; pending: number; inProgress: number; pendingReview: number }
  filters: { status: string; branch: string; keyword: string }
  branchOptions: { value: string; label: string }[]
}>()

const emit = defineEmits<{
  (e: 'update:filters', val: typeof props.filters): void
  (e: 'create'): void
  (e: 'view', task: any): void
  (e: 'start', task: any): void
  (e: 'delete', task: any): void
  (e: 'cancel', task: any): void
  (e: 'approve', task: any): void
  (e: 'reject', task: any): void
  (e: 'recount', task: any): void
  (e: 'recountAll', task: any): void
  (e: 'report', task: any): void
  (e: 'downloadTemplate', task: any): void
  (e: 'import', task: any): void
  (e: 'submit', task: any): void
}>()

const statusOptions = INVENTORY_STATUS_OPTIONS

const getStatusStyle = (status: string) => {
  const colorSet = INVENTORY_STATUS_COLORS[status as keyof typeof INVENTORY_STATUS_COLORS] || { bg: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }
  return { ...colorSet, border: colorSet.bg }
}

const getStatusLabel = (status: string) => INVENTORY_STATUS_MAP[status as keyof typeof INVENTORY_STATUS_MAP] || status
const getMissedRuleLabel = (rule: string) => MISSED_RULE_LABELS[rule as MissedRuleType] || '-'
const getRepeatRuleLabel = (rule: string) => REPEAT_RULE_LABELS[rule as RepeatRuleType] || '-'
const getBranchName = (branchId: string | null | undefined) => {
  if (!branchId) return '全部分公司'
  return props.branchOptions.find(b => b.value === branchId)?.label || branchId
}
const formatDate = (dateStr: string | null | undefined) => dateStr ? dateStr.slice(0, 10) : '-'
</script>

<template>
  <div>
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">资产盘点</h1>
        <p class="page-desc">管理盘点任务，追踪盘点进度</p>
      </div>
      <button class="btn-primary" @click="emit('create')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        创建盘点任务
      </button>
    </div>

    <!-- 快速统计 -->
    <div class="quick-stats">
      <div class="stat-item">
        <span class="stat-num">{{ stats.total }}</span>
        <span class="stat-label">全部任务</span>
      </div>
      <div class="stat-item">
        <span class="stat-num pending">{{ stats.pending }}</span>
        <span class="stat-label">待盘点</span>
      </div>
      <div class="stat-item">
        <span class="stat-num in-progress">{{ stats.inProgress }}</span>
        <span class="stat-label">盘点中</span>
      </div>
      <div class="stat-item">
        <span class="stat-num review">{{ stats.pendingReview }}</span>
        <span class="stat-label">待审核</span>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item search">
          <svg class="filter-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            :value="filters.keyword"
            @input="emit('update:filters', { ...filters, keyword: ($event.target as HTMLInputElement).value })"
            type="text"
            placeholder="搜索任务名称..."
            class="filter-input"
            aria-label="搜索盘点任务"
          />
        </div>
        <div class="filter-item">
          <select
            :value="filters.status"
            @change="emit('update:filters', { ...filters, status: ($event.target as HTMLSelectElement).value })"
            class="filter-select"
            aria-label="筛选任务状态"
          >
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- 任务列表表格 -->
    <div class="task-table-wrapper">
      <table class="task-table">
        <thead>
          <tr>
            <th>任务名称</th>
            <th>盘点范围</th>
            <th>状态</th>
            <th>漏盘规则</th>
            <th>重复规则</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="table-empty">加载中...</td>
          </tr>
          <tr v-else-if="tasks.length === 0">
            <td colspan="7" class="table-empty">暂无盘点任务</td>
          </tr>
          <tr v-for="task in tasks" :key="task.id" :class="[task.status]">
            <td class="cell-name">{{ task.name }}</td>
            <td>{{ getBranchName(task.branch) }}</td>
            <td>
              <span class="task-status" :style="getStatusStyle(task.status)">
                {{ getStatusLabel(task.status) }}
              </span>
            </td>
            <td>{{ getMissedRuleLabel(task.missedRule) }}</td>
            <td>{{ getRepeatRuleLabel(task.repeatRule) }}</td>
            <td>{{ formatDate(task.createdAt) }}</td>
            <td class="cell-actions">
              <template v-if="task.status === 'pending'">
                <button class="row-btn danger" title="删除" @click="emit('delete', task)">删除</button>
                <button class="row-btn secondary" @click="emit('cancel', task)">作废</button>
                <button class="row-btn primary" @click="emit('start', task)">开始盘点</button>
              </template>
              <template v-else-if="task.status === 'in_progress'">
                <button class="row-btn secondary" @click="emit('view', task)">查看进度</button>
                <button class="row-btn accent" @click="emit('downloadTemplate', task)">下载模板</button>
                <button class="row-btn accent" @click="emit('import', task)">导入盘点表</button>
                <button class="row-btn secondary" @click="emit('cancel', task)">作废</button>
                <button class="row-btn primary" @click="emit('submit', task)">提交审核</button>
              </template>
              <template v-else-if="task.status === 'pending_review'">
                <button class="row-btn secondary" @click="emit('view', task)">查看详情</button>
                <button class="row-btn danger" @click="emit('reject', task)">驳回</button>
                <button class="row-btn primary" @click="emit('approve', task)">审批通过</button>
              </template>
              <template v-else-if="task.status === 'rejected'">
                <button class="row-btn secondary" @click="emit('view', task)">查看原因</button>
                <button class="row-btn warning" @click="emit('recount', task)">重盘异常项</button>
                <button class="row-btn warning" @click="emit('recountAll', task)">全部重盘</button>
              </template>
              <template v-else-if="task.status === 'completed'">
                <button class="row-btn secondary" @click="emit('report', task)">查看报告</button>
              </template>
              <template v-else-if="task.status === 'cancelled'">
                <span class="row-btn disabled">已作废</span>
              </template>
              <template v-else>
                <button class="row-btn secondary" @click="emit('view', task)">查看详情</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { font-size: 24px; font-weight: 700; margin: 0; }
.page-desc { font-size: 14px; color: var(--color-text-secondary); margin: 4px 0 0; }
.btn-primary { display: flex; align-items: center; gap: 8px; padding: 10px 20px; background: var(--color-primary); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn-primary svg { width: 18px; height: 18px; }
.quick-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-item { background: var(--color-bg-elevated); border-radius: 12px; padding: 16px 20px; text-align: center; border: 1px solid var(--color-border); }
.stat-num { display: block; font-size: 28px; font-weight: 700; }
.stat-num.pending { color: var(--color-warning); }
.stat-num.in-progress { color: var(--color-primary); }
.stat-num.review { color: #8b5cf6; }
.stat-label { font-size: 13px; color: var(--color-text-secondary); margin-top: 4px; display: block; }
.filter-section { margin-bottom: 20px; }
.filter-row { display: flex; gap: 12px; flex-wrap: wrap; }
.filter-item { position: relative; }
.filter-item.search { flex: 1; min-width: 200px; }
.filter-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; color: var(--color-text-secondary); pointer-events: none; }
.filter-input { width: 100%; padding: 10px 12px 10px 36px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg-elevated); outline: none; }
.filter-input:focus { border-color: var(--color-primary); }
.filter-select { padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg-elevated); outline: none; min-width: 140px; }
.task-table-wrapper { background: var(--color-bg-elevated); border-radius: 12px; border: 1px solid var(--color-border); overflow: hidden; }
.task-table { width: 100%; border-collapse: collapse; }
.task-table th { padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; color: var(--color-text-secondary); background: var(--color-bg); border-bottom: 1px solid var(--color-border); }
.task-table td { padding: 12px 16px; font-size: 14px; border-bottom: 1px solid var(--color-border); }
.table-empty { text-align: center; color: var(--color-text-secondary); padding: 40px 16px !important; }
.cell-name { font-weight: 600; }
.cell-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.task-status { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.row-btn { padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; border: 1px solid transparent; background: none; }
.row-btn.primary { color: var(--color-primary); border-color: var(--color-primary); }
.row-btn.secondary { color: var(--color-text-secondary); border-color: var(--color-border); }
.row-btn.danger { color: var(--color-danger); border-color: var(--color-danger); }
.row-btn.accent { color: #8b5cf6; border-color: #8b5cf6; }
.row-btn.warning { color: var(--color-warning); border-color: var(--color-warning); }
.row-btn.disabled { color: var(--color-text-secondary); cursor: default; border-color: var(--color-border); opacity: 0.6; }
</style>
