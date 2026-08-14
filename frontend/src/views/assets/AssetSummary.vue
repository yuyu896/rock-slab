<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getAssetSummary } from '@/api/assets'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { AssetSummaryRow } from '@/types'

const loading = ref(false)
const rows = ref<AssetSummaryRow[]>([])

const totalCount = computed(() => rows.value.reduce((sum, r) => sum + r.total, 0))

async function fetchSummary() {
  loading.value = true
  try {
    const { data } = await getAssetSummary()
    rows.value = data || []
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

onMounted(fetchSummary)
</script>

<template>
  <div class="asset-summary-page">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">资产汇总</h1>
        <p class="page-desc">共{{ rows.length }}个分公司 / {{ totalCount }}项资产</p>
      </div>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>序号</th>
            <th>分公司</th>
            <th>编码</th>
            <th>资产总数</th>
            <th>编号起始</th>
            <th>编号截止</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && rows.length === 0">
            <td colspan="6" class="empty-cell">加载中...</td>
          </tr>
          <tr v-else-if="rows.length === 0">
            <td colspan="6" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-for="(row, index) in rows" :key="row.branchCode || row.branchName">
            <td>{{ index + 1 }}</td>
            <td class="branch-name">{{ row.branchName || '-' }}</td>
            <td>{{ row.branchCode || '-' }}</td>
            <td>{{ row.total }}</td>
            <td><span v-if="row.minCode" class="asset-code">{{ row.minCode }}</span><span v-else>-</span></td>
            <td><span v-if="row.maxCode" class="asset-code">{{ row.maxCode }}</span><span v-else>-</span></td>
          </tr>
        </tbody>
        <tfoot v-if="rows.length > 0">
          <tr>
            <td colspan="3">合计</td>
            <td>{{ totalCount }}</td>
            <td colspan="2"></td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>

<style scoped>
.asset-summary-page {
  max-width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.header-info {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.page-desc {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin: 0;
}

.table-container {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border);
  overflow-x: auto;
  overflow-y: auto;
  max-height: calc(100vh - 240px);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--color-bg-elevated);
}

.data-table th {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.data-table td {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: middle;
}

.data-table tbody tr {
  transition: background var(--transition-fast);
}

.data-table tbody tr:hover {
  background: var(--color-bg-elevated);
}

.data-table tfoot td {
  font-weight: 600;
  background: var(--color-bg-elevated);
  border-top: 1px solid var(--color-border);
  border-bottom: none;
}

.empty-cell {
  text-align: center;
  color: var(--color-text-tertiary);
  padding: var(--space-8) 0 !important;
}

.branch-name {
  font-weight: 500;
}

.asset-code {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  padding: 2px 8px;
  border-radius: 4px;
}
</style>
