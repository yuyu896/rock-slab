<script setup lang="ts">
import { ref } from 'vue'
import { getInventoryReport } from '@/api/inventories'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import { INVENTORY_RESULT_MAP } from '@/constants'

defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
}>()

const reportLoading = ref(false)
const reportData = ref<any>(null)

const getResultLabel = (result: string) => INVENTORY_RESULT_MAP[result as keyof typeof INVENTORY_RESULT_MAP] ?? result

async function open(taskId: string) {
  emit('update:visible', true)
  reportLoading.value = true
  try {
    const { data } = await getInventoryReport(taskId)
    reportData.value = data
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    reportLoading.value = false
  }
}

function close() {
  emit('update:visible', false)
}

defineExpose({ open })
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal-dialog modal-lg">
      <div class="modal-header">
        <h3 class="modal-title">盘点报告</h3>
        <button class="modal-close" @click="close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <div v-if="reportLoading" class="report-loading">加载中...</div>
        <div v-else-if="reportData" class="report-content">
          <!-- 报告统计 -->
          <div class="report-stats">
            <div class="report-stat-item">
              <span class="report-stat-value">{{ reportData.progress?.totalItems ?? 0 }}</span>
              <span class="report-stat-label">应盘数量</span>
            </div>
            <div class="report-stat-item">
              <span class="report-stat-value success">{{ reportData.progress?.checkedItems ?? 0 }}</span>
              <span class="report-stat-label">已盘点</span>
            </div>
            <div class="report-stat-item">
              <span class="report-stat-value warning">{{ reportData.progress?.surplusCount ?? 0 }}</span>
              <span class="report-stat-label">盘盈</span>
            </div>
            <div class="report-stat-item">
              <span class="report-stat-value danger">{{ reportData.progress?.missingCount ?? 0 }}</span>
              <span class="report-stat-label">盘亏</span>
            </div>
          </div>
          <!-- 差异率 -->
          <div class="report-stats" v-if="reportData.progress?.checkedItems">
            <div class="report-stat-item">
              <span class="report-stat-value success">{{ reportData.progress?.matchRate ?? 0 }}%</span>
              <span class="report-stat-label">正常率</span>
            </div>
            <div class="report-stat-item">
              <span class="report-stat-value warning">{{ reportData.progress?.surplusRate ?? 0 }}%</span>
              <span class="report-stat-label">盘盈率</span>
            </div>
            <div class="report-stat-item">
              <span class="report-stat-value danger">{{ reportData.progress?.missingRate ?? 0 }}%</span>
              <span class="report-stat-label">盘亏率</span>
            </div>
          </div>
          <!-- 盘点明细列表 -->
          <div v-if="reportData.items?.length" class="report-table-wrapper">
            <table class="report-table">
              <thead>
                <tr>
                  <th>资产编号</th>
                  <th>资产名称</th>
                  <th>账面数量</th>
                  <th>实际数量</th>
                  <th>变动</th>
                  <th>结果</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in reportData.items" :key="item.id">
                  <td>{{ item.assetId }}</td>
                  <td>{{ item.assetName ?? '-' }}</td>
                  <td>{{ item.expectedQty }}</td>
                  <td>{{ item.actualQty ?? '-' }}</td>
                  <td :style="{ color: (item.actualQty ?? 0) > item.expectedQty ? 'var(--color-success)' : (item.actualQty ?? 0) < item.expectedQty ? 'var(--color-danger)' : '' }">
                    {{ item.actualQty != null ? (item.actualQty - item.expectedQty >= 0 ? '+' : '') + (item.actualQty - item.expectedQty) : '-' }}
                  </td>
                  <td>{{ getResultLabel(item.result) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="report-empty">暂无盘点明细</div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" @click="close">关闭</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-dialog { background: var(--color-bg-elevated); border-radius: 12px; width: 90%; max-width: 800px; max-height: 90vh; display: flex; flex-direction: column; }
.modal-dialog.modal-lg { max-width: 1000px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); }
.modal-title { font-size: 18px; font-weight: 600; margin: 0; }
.modal-close { background: none; border: none; cursor: pointer; padding: 4px; color: var(--color-text-secondary); }
.modal-close svg { width: 20px; height: 20px; }
.modal-body { padding: 24px; overflow-y: auto; flex: 1; }
.modal-footer { padding: 16px 24px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.report-loading { text-align: center; padding: 40px; color: var(--color-text-secondary); }
.report-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.report-stat-item { text-align: center; padding: 12px; background: var(--color-bg); border-radius: 8px; }
.report-stat-value { display: block; font-size: 24px; font-weight: 700; }
.report-stat-value.success { color: var(--color-success); }
.report-stat-value.warning { color: var(--color-warning); }
.report-stat-value.danger { color: var(--color-danger); }
.report-stat-label { font-size: 13px; color: var(--color-text-secondary); }
.report-table-wrapper { overflow-x: auto; }
.report-table { width: 100%; border-collapse: collapse; }
.report-table th, .report-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--color-border); font-size: 14px; }
.report-table th { font-weight: 600; color: var(--color-text-secondary); background: var(--color-bg); }
.report-empty { text-align: center; padding: 40px; color: var(--color-text-secondary); }
.btn-secondary { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 14px; }
</style>
