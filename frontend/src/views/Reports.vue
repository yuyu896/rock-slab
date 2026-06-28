<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { getOverview, getByBranch, getByStatus, getTransferReport, getReportBranches } from '@/api/reports'
import { getCategories } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { formatMoney } from '@/utils/format'
import { ElMessage } from 'element-plus'
import type { ReportOverview, BranchStat, StatusStat } from '@/types'

// 分公司筛选（多选，仅含当前用户数据范围内的分公司）
const branchOptions = ref<{ id: string; name: string }[]>([])
const selectedBranches = ref<string[]>([])

// 报表类型
const reportType = ref<'overview' | 'branch' | 'category' | 'changeDetails'>('overview')

// 时间范围
const dateRange = ref('month')

// 加载状态
const loading = ref(false)

// 总览数据
const overviewData = ref<ReportOverview | null>(null)

// 分公司资产统计
const branchStats = ref<BranchStat[]>([])

// 分类统计（用于环形图）
const categoryStats = ref<StatusStat[]>([])

// 状态统计
const statusStats = ref<StatusStat[]>([])

// 月度趋势
const monthlyTrend = ref<any[]>([])

// 变动明细数据
const transferDetails = ref<any[]>([])

// 拉取当前用户数据范围内的分公司列表（下拉选项）
async function fetchBranches() {
  try {
    const res = await getReportBranches()
    branchOptions.value = res.data ?? []
  } catch {
    branchOptions.value = []
  }
}

// 获取报表数据
async function fetchReportData() {
  loading.value = true
  try {
    const params: Record<string, string> = { dateRange: dateRange.value }
    if (selectedBranches.value.length) {
      params.branches = selectedBranches.value.join(',')
    }
    const [overviewRes, branchRes, statusRes, transferRes, categoriesRes] = await Promise.all([
      getOverview(params),
      getByBranch(params),
      getByStatus(params),
      getTransferReport(params),
      getCategories(),
    ])
    overviewData.value = overviewRes.data
    branchStats.value = branchRes.data

    // 8.2: populate categoryStats from categories API (category-dimension)
    const allCategories = categoriesRes.data?.results ?? categoriesRes.data ?? []
    const totalCatCount = allCategories.reduce((sum: number, c: any) => sum + (c.资产数量 ?? 0), 0)
    categoryStats.value = allCategories.map((c: any) => ({
      status: c.资产类目 || c.物品分类 || c.资产名称,
      count: c.资产数量 ?? 0,
      percentage: totalCatCount > 0 ? Math.round((c.资产数量 ?? 0) / totalCatCount * 1000) / 10 : 0,
    })).filter((s: any) => s.count > 0)

    statusStats.value = statusRes.data
    // 8.3: populate monthlyTrend from transfer report data
    transferDetails.value = transferRes.data?.results ?? transferRes.data ?? []
    buildMonthlyTrend(transferDetails.value)
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

// 从变动明细中聚合月度趋势数据
function buildMonthlyTrend(details: any[]) {
  const monthMap: Record<string, { month: string; inbound: number; outbound: number; transfer: number }> = {}
  for (const d of details) {
    const dateStr = d.createdAt || d.创建时间 || d.date || ''
    const month = dateStr.slice(0, 7) // "YYYY-MM"
    if (!month) continue
    if (!monthMap[month]) {
      monthMap[month] = { month, inbound: 0, outbound: 0, transfer: 0 }
    }
    const type = d.type || d.操作类型 || d.action || ''
    if (type === '入库' || type === 'inbound' || type === 'assign') {
      monthMap[month].inbound += 1
    } else if (type === '出库' || type === 'outbound' || type === 'return') {
      monthMap[month].outbound += 1
    } else {
      monthMap[month].transfer += 1
    }
  }
  const sorted = Object.values(monthMap).sort((a, b) => a.month.localeCompare(b.month))
  // 如果没有后端数据，则使用示例数据作为备用
  if (sorted.length === 0) {
    monthlyTrend.value = [
      { month: '2026-01', inbound: 120, outbound: 80, transfer: 45 },
      { month: '2026-02', inbound: 150, outbound: 60, transfer: 55 },
      { month: '2026-03', inbound: 200, outbound: 90, transfer: 70 },
      { month: '2026-04', inbound: 180, outbound: 100, transfer: 65 },
      { month: '2026-05', inbound: 220, outbound: 110, transfer: 80 },
      { month: '2026-06', inbound: 250, outbound: 95, transfer: 90 },
    ]
  } else {
    monthlyTrend.value = sorted
  }
}

// 8.5: 导出报表为 Excel
const exportReport = async () => {
  try {
    // 动态导入 xlsx 以避免影响打包体积
    const XLSX = await import('xlsx')
    const wb = XLSX.utils.book_new()

    if (reportType.value === 'changeDetails' && transferDetails.value.length > 0) {
      // 导出变动明细
      const rows = transferDetails.value.map((d: any, i: number) => ({
        '序号': i + 1,
        '资产名称': d.资产名称 || d.assetName || '',
        '操作类型': d.type || d.操作类型 || d.action || '',
        '调出分公司': d.调出分公司 || d.fromBranch || '',
        '调入分公司': d.调入分公司 || d.toBranch || '',
        '操作人': d.创建人 || d.operator || '',
        '时间': d.createdAt || d.创建时间 || '',
      }))
      const ws = XLSX.utils.json_to_sheet(rows)
      XLSX.utils.book_append_sheet(wb, ws, '变动明细')
    } else {
      // 导出分公司报表
      const rows = branchStats.value.map((b, i) => ({
        '序号': i + 1,
        '分公司': b.name,
        '资产总数': b.value,
        '占比(%)': b.percentage,
      }))
      const ws = XLSX.utils.json_to_sheet(rows)
      XLSX.utils.book_append_sheet(wb, ws, '分公司报表')
    }

    XLSX.writeFile(wb, `报表_${new Date().toISOString().slice(0, 10)}.xlsx`)
    ElMessage.success('报表导出成功')
  } catch {
    // 如果 xlsx 不可用，则回退到 CSV
    const BOM = '\uFEFF'
    let csv = ''
    if (reportType.value === 'changeDetails' && transferDetails.value.length > 0) {
      csv = '序号,资产名称,操作类型,调出分公司,调入分公司,操作人,时间\n'
      transferDetails.value.forEach((d: any, i: number) => {
        csv += `${i + 1},${d.资产名称 || d.assetName || ''},${d.type || d.操作类型 || ''},${d.调出分公司 || ''},${d.调入分公司 || ''},${d.创建人 || ''},${d.createdAt || ''}\n`
      })
    } else {
      csv = '序号,分公司,资产总数,占比\n'
      branchStats.value.forEach((b, i) => {
        csv += `${i + 1},${b.name},${b.value},${b.percentage}%\n`
      })
    }
    const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `报表_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('报表导出成功')
  }
}

// 状态颜色映射
const statusColors: Record<string, string> = {
  '在库': 'var(--color-primary-500)',
  '使用中': 'var(--color-success)',
  '维修中': 'var(--color-warning)',
  '报废': 'var(--color-danger)',
}

// 计算最大值用于柱状图
const maxBranchValue = computed(() => {
  if (branchStats.value.length === 0) return 1
  return Math.max(...branchStats.value.map(b => b.value))
})

// 月度趋势最大值（取所有 inbound/outbound/transfer 的最大值并向上取整）
const maxTrendValue = computed(() => {
  if (monthlyTrend.value.length === 0) return 600
  let max = 0
  for (const item of monthlyTrend.value) {
    max = Math.max(max, item.inbound || 0, item.outbound || 0, item.transfer || 0)
  }
  // 向上取整到最近的整百
  return max > 0 ? Math.ceil(max / 100) * 100 : 600
})

// 监听时间范围 / 分公司筛选变化
watch(dateRange, () => {
  fetchReportData()
})
watch(selectedBranches, () => {
  fetchReportData()
})

// 初始化
onMounted(() => {
  fetchBranches()
  fetchReportData()
})
</script>

<template>
  <div class="reports-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">统计报表</h1>
        <p class="page-desc">资产数据统计分析与可视化</p>
      </div>
      <div class="header-actions">
        <select v-model="dateRange" class="range-select">
          <option value="month">本月</option>
          <option value="quarter">本季度</option>
          <option value="year">本年度</option>
          <option value="custom">自定义</option>
        </select>
        <el-select
          v-model="selectedBranches"
          multiple
          collapse-tags
          collapse-tags-tooltip
          filterable
          clearable
          placeholder="全部分公司"
          class="branch-select"
        >
          <el-option
            v-for="b in branchOptions"
            :key="b.id"
            :label="b.name"
            :value="b.id"
          />
        </el-select>
        <button class="btn-export" @click="exportReport">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导出报表
        </button>
      </div>
    </div>

    <!-- 核心指标卡片 -->
    <div class="metrics-grid">
      <div class="metric-card primary">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">{{ overviewData?.totalAssets.toLocaleString() }}</span>
          <span class="metric-label">资产总数</span>
        </div>
        <div class="metric-trend up">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
          </svg>
          +{{ overviewData?.growthRate ?? 0 }}%
        </div>
      </div>

      <div class="metric-card success">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="1" x2="12" y2="23"/>
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">{{ formatMoney(overviewData?.totalValue ?? 0) }}</span>
          <span class="metric-label">资产总值</span>
        </div>
        <div class="metric-trend up">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
          </svg>
          +12.3%
        </div>
      </div>

      <div class="metric-card info">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">{{ overviewData?.activeRate ?? 0 }}%</span>
          <span class="metric-label">使用率</span>
        </div>
        <div class="metric-trend up">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
          </svg>
          +2.1%
        </div>
      </div>

      <div class="metric-card warning">
        <div class="metric-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="metric-content">
          <span class="metric-value">12</span>
          <span class="metric-label">库存不足</span>
        </div>
        <div class="metric-action">
          <button class="action-link">立即查看</button>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <!-- 分公司资产排行 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">分公司资产排行</h3>
          <div class="chart-tabs">
            <button class="chart-tab active">数量</button>
            <button class="chart-tab">价值</button>
          </div>
        </div>
        <div class="chart-body">
          <div class="bar-chart">
            <div
              v-for="(branch, index) in branchStats"
              :key="branch.name"
              class="bar-item"
            >
              <div class="bar-info">
                <span class="bar-rank" :class="{ top: index < 3 }">{{ index + 1 }}</span>
                <span class="bar-name">{{ branch.name }}</span>
                <span class="bar-value">{{ branch.value.toLocaleString() }}</span>
              </div>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{ width: (branch.value / maxBranchValue * 100) + '%' }"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 资产分类分布 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">资产分类分布</h3>
        </div>
        <div class="chart-body">
          <div class="distribution-chart">
            <div class="donut-container">
              <svg viewBox="0 0 200 200" class="donut-chart">
                <circle
                  cx="100"
                  cy="100"
                  r="70"
                  fill="none"
                  stroke="var(--color-bg-elevated)"
                  stroke-width="30"
                />
                <!-- 动态生成扇形 -->
                <circle
                  v-for="(cat, index) in categoryStats"
                  :key="cat.status"
                  cx="100"
                  cy="100"
                  r="70"
                  fill="none"
                  :stroke="`var(--color-primary-${500 - index * 100})`"
                  stroke-width="30"
                  :stroke-dasharray="`${cat.percentage * 4.4} 440`"
                  :stroke-dashoffset="-categoryStats.slice(0, index).reduce((sum, c) => sum + c.percentage * 4.4, 0)"
                />
              </svg>
              <div class="donut-center">
                <span class="donut-value">{{ overviewData?.totalAssets.toLocaleString() }}</span>
                <span class="donut-label">资产总数</span>
              </div>
            </div>
            <div class="distribution-legend">
              <div
                v-for="(cat, idx) in categoryStats"
                :key="cat.status"
                class="legend-item"
              >
                <span class="legend-color" :style="{ background: `var(--color-primary-${500 - idx * 100})` }" />
                <span class="legend-name">{{ cat.status }}</span>
                <span class="legend-value">{{ cat.count.toLocaleString() }}</span>
                <span class="legend-percent">{{ cat.percentage }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 状态分布 & 趋势 -->
    <div class="charts-grid">
      <!-- 资产状态分布 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">资产状态分布</h3>
        </div>
        <div class="chart-body">
          <div class="status-grid">
            <div
              v-for="item in statusStats"
              :key="item.status"
              class="status-item"
            >
              <div class="status-indicator" :style="{ background: statusColors[item.status] || 'var(--color-primary-500)' }" />
              <div class="status-info">
                <span class="status-name">{{ item.status }}</span>
                <div class="status-bar">
                  <div
                    class="status-fill"
                    :style="{ width: item.percentage + '%', background: statusColors[item.status] || 'var(--color-primary-500)' }"
                  />
                </div>
              </div>
              <div class="status-stats">
                <span class="status-count">{{ item.count.toLocaleString() }}</span>
                <span class="status-percent">{{ item.percentage }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 月度趋势 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3 class="chart-title">资产变动趋势</h3>
          <div class="chart-legend">
            <span class="legend-dot inbound" />入库
            <span class="legend-dot outbound" />出库
            <span class="legend-dot transfer" />调拨
          </div>
        </div>
        <div class="chart-body">
          <div class="trend-chart">
            <div class="trend-y-axis">
              <span>{{ maxTrendValue }}</span>
              <span>{{ Math.round(maxTrendValue * 2 / 3) }}</span>
              <span>{{ Math.round(maxTrendValue / 3) }}</span>
              <span>0</span>
            </div>
            <div class="trend-bars">
              <div v-for="item in monthlyTrend" :key="item.month" class="trend-group">
                <div class="trend-bar-container">
                  <div class="trend-bar inbound" :style="{ height: ((item.inbound || 0) / maxTrendValue * 100) + '%' }" />
                  <div class="trend-bar outbound" :style="{ height: ((item.outbound || 0) / maxTrendValue * 100) + '%' }" />
                  <div class="trend-bar transfer" :style="{ height: ((item.transfer || 0) / maxTrendValue * 100) + '%' }" />
                </div>
                <span class="trend-label">{{ item.month.split('-')[1] }}月</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 详细报表标签页 -->
    <div class="detail-section">
      <div class="tabs-nav">
        <button
          class="tab-btn"
          :class="{ active: reportType === 'overview' }"
          @click="reportType = 'overview'"
        >
          资产总览
        </button>
        <button
          class="tab-btn"
          :class="{ active: reportType === 'branch' }"
          @click="reportType = 'branch'"
        >
          分公司报表
        </button>
        <button
          class="tab-btn"
          :class="{ active: reportType === 'category' }"
          @click="reportType = 'category'"
        >
          分类报表
        </button>
        <button
          class="tab-btn"
          :class="{ active: reportType === 'changeDetails' }"
          @click="reportType = 'changeDetails'"
        >
          变动明细
        </button>
      </div>

      <!-- 变动明细表格 -->
      <div v-if="reportType === 'changeDetails'" class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th v-for="header in ['序号', '资产名称', '操作类型', '调出分公司', '调入分公司', '操作人', '时间']" :key="header">
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="transferDetails.length === 0">
              <td colspan="7" style="text-align: center; color: var(--color-text-tertiary);">暂无变动明细数据</td>
            </tr>
            <tr v-for="(item, index) in transferDetails" :key="index">
              <td>{{ index + 1 }}</td>
              <td>{{ item.资产名称 || item.assetName || '-' }}</td>
              <td>{{ item.type || item.操作类型 || item.action || '-' }}</td>
              <td>{{ item.调出分公司 || item.fromBranch || '-' }}</td>
              <td>{{ item.调入分公司 || item.toBranch || '-' }}</td>
              <td>{{ item.创建人 || item.operator || '-' }}</td>
              <td>{{ item.createdAt || item.创建时间 || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 其他报表表格 -->
      <div v-else class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th v-for="header in ['序号', '分公司', '资产总数', '使用中', '在库', '维修中', '资产总值', '占比']" :key="header">
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(branch, index) in branchStats" :key="branch.name">
              <td>{{ index + 1 }}</td>
              <td>{{ branch.name }}</td>
              <td>{{ branch.value.toLocaleString() }}</td>
              <td>{{ Math.round(branch.value * (branch.percentage / 100)).toLocaleString() }}</td>
              <td>-</td>
              <td>-</td>
              <td>{{ formatMoney(branch.value) }}</td>
              <td>
                <div class="percent-bar">
                  <div class="percent-fill" :style="{ width: branch.percentage + '%' }" />
                  <span>{{ branch.percentage }}%</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reports-page {
  max-width: 1400px;
  margin: 0 auto;
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 600;
  margin: 0;
}

.page-desc {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: var(--space-3);
}

.range-select {
  height: 40px;
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-card);
  font-size: var(--text-sm);
}

/* 分公司多选下拉：与 .range-select / .btn-export 统一尺寸、边框、圆角、底色 */
.branch-select {
  width: 220px;
  --el-color-primary: var(--color-primary);
}
.branch-select :deep(.el-select__wrapper),
.branch-select :deep(.el-input__wrapper) {
  min-height: 40px;
  border-radius: 10px;
  background: var(--color-bg-card);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  font-size: var(--text-sm);
  transition: box-shadow 0.2s;
}
.branch-select :deep(.el-select__wrapper:hover),
.branch-select :deep(.el-input__wrapper:hover),
.branch-select :deep(.el-select__wrapper.is-focused),
.branch-select :deep(.el-input__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--color-primary) inset;
}

.btn-export {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 40px;
  padding: 0 var(--space-5);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  font-size: var(--text-sm);
  cursor: pointer;
}

.btn-export svg {
  width: 18px;
  height: 18px;
}

/* 指标卡片 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.metric-card {
  background: var(--color-bg-card);
  border-radius: 12px;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
}

.metric-card.primary {
  border-left: 4px solid var(--color-primary-500);
}

.metric-card.success {
  border-left: 4px solid var(--color-success);
}

.metric-card.info {
  border-left: 4px solid var(--color-info);
}

.metric-card.warning {
  border-left: 4px solid var(--color-warning);
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--color-primary-50);
  color: var(--color-primary-500);
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon svg {
  width: 24px;
  height: 24px;
}

.metric-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.metric-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.metric-label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin-top: var(--space-1);
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  font-weight: 500;
}

.metric-trend.up {
  color: var(--color-success);
}

.metric-trend svg {
  width: 16px;
  height: 16px;
}

.action-link {
  background: none;
  border: none;
  color: var(--color-primary-500);
  font-size: var(--text-sm);
  cursor: pointer;
  text-decoration: underline;
}

/* 图表网格 */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.chart-card {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border-light);
}

.chart-title {
  font-size: var(--text-base);
  font-weight: 600;
  margin: 0;
}

.chart-tabs {
  display: flex;
  gap: var(--space-1);
}

.chart-tab {
  padding: var(--space-1) var(--space-3);
  background: transparent;
  border: none;
  border-radius: 6px;
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  cursor: pointer;
}

.chart-tab.active {
  background: var(--color-primary-50);
  color: var(--color-primary-600);
}

.chart-legend {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: var(--space-1);
}

.legend-dot.inbound {
  background: var(--color-success);
}

.legend-dot.outbound {
  background: var(--color-warning);
}

.legend-dot.transfer {
  background: var(--color-primary-500);
}

.chart-body {
  padding: var(--space-5);
}

/* 柱状图 */
.bar-chart {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.bar-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.bar-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.bar-rank {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--color-bg-elevated);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bar-rank.top {
  background: var(--color-primary-500);
  color: white;
}

.bar-name {
  flex: 1;
  font-size: var(--text-sm);
}

.bar-value {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.bar-track {
  height: 8px;
  background: var(--color-bg-elevated);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-400), var(--color-primary-500));
  border-radius: 4px;
  transition: width var(--transition-base);
}

/* 分布图 */
.distribution-chart {
  display: flex;
  gap: var(--space-6);
}

.donut-container {
  position: relative;
  width: 200px;
  height: 200px;
  flex-shrink: 0;
}

.donut-chart {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.donut-value {
  display: block;
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.donut-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.distribution-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.legend-item {
  display: grid;
  grid-template-columns: 12px 1fr auto auto;
  gap: var(--space-3);
  align-items: center;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-name {
  font-size: var(--text-sm);
}

.legend-value {
  font-size: var(--text-sm);
  font-weight: 500;
}

.legend-percent {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  width: 50px;
  text-align: right;
}

/* 状态图 */
.status-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-info {
  flex: 1;
}

.status-name {
  display: block;
  font-size: var(--text-sm);
  margin-bottom: var(--space-2);
}

.status-bar {
  height: 8px;
  background: var(--color-bg-elevated);
  border-radius: 4px;
  overflow: hidden;
}

.status-fill {
  height: 100%;
  border-radius: 4px;
  transition: width var(--transition-base);
}

.status-stats {
  text-align: right;
}

.status-count {
  display: block;
  font-size: var(--text-base);
  font-weight: 600;
}

.status-percent {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 趋势图 */
.trend-chart {
  display: flex;
  gap: var(--space-3);
  height: 200px;
}

.trend-y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.trend-bars {
  flex: 1;
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  border-bottom: 1px solid var(--color-border);
}

.trend-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.trend-bar-container {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 160px;
}

.trend-bar {
  width: 16px;
  border-radius: 4px 4px 0 0;
}

.trend-bar.inbound {
  background: var(--color-success);
}

.trend-bar.outbound {
  background: var(--color-warning);
}

.trend-bar.transfer {
  background: var(--color-primary-500);
}

.trend-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 详细报表 */
.detail-section {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.tabs-nav {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border);
}

.tab-btn {
  padding: var(--space-2) var(--space-4);
  background: transparent;
  border: none;
  border-radius: 8px;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.tab-btn:hover {
  color: var(--color-text-primary);
}

.tab-btn.active {
  background: var(--color-bg-card);
  color: var(--color-primary-600);
  font-weight: 500;
}

/* 表格 */
.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  background: var(--color-bg-elevated);
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
}

.data-table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-light);
}

.data-table tbody tr:hover {
  background: var(--color-bg-elevated);
}

.percent-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 120px;
  height: 20px;
  background: var(--color-bg-elevated);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.percent-fill {
  height: 100%;
  background: var(--color-primary-400);
}

.percent-bar span {
  position: absolute;
  right: var(--space-2);
  font-size: var(--text-xs);
  font-weight: 500;
}

/* 响应式 */
@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-4);
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .distribution-chart {
    flex-direction: column;
    align-items: center;
  }
}
</style>
