<script setup lang="ts">
import { formatMoney } from '@/utils/format'
import StatusBadge from '@/components/StatusBadge.vue'
import type { Asset, Transfer } from '@/types'

defineProps<{
  asset: Asset | null
  transfers: Transfer[]
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const actionLabel = (type: string) => {
  const map: Record<string, string> = { assign: '领用', return: '归还', transfer: '调拨', repair: '维修', scrap: '报废', purchase: '采购入库' }
  return map[type] || type
}
</script>

<template>
  <div class="drawer-overlay" @click.self="emit('close')">
    <div class="drawer-panel">
      <div class="drawer-header">
        <h3>资产详情</h3>
        <button class="drawer-close" @click="emit('close')">&times;</button>
      </div>
      <div v-if="asset" class="drawer-body">
        <!-- 基本信息 -->
        <div class="detail-section">
          <h4 class="detail-section-title">基本信息</h4>
          <div class="detail-grid">
            <div class="detail-field"><span class="detail-label">资产编号</span><span class="detail-value code">{{ asset.资产编号 }}</span></div>
            <div class="detail-field"><span class="detail-label">资产名称</span><span class="detail-value">{{ asset.资产名称 }}</span></div>
            <div class="detail-field"><span class="detail-label">资产类目</span><span class="detail-value">{{ asset.资产类目 }}</span></div>
            <div class="detail-field"><span class="detail-label">物品分类</span><span class="detail-value">{{ asset.物品分类 }}</span></div>
            <div class="detail-field"><span class="detail-label">规格</span><span class="detail-value">{{ asset.规格 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">供应商</span><span class="detail-value">{{ asset.供应商 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">采购方式</span><span class="detail-value">{{ asset.是否租用 ? '租用' : '自购' }}</span></div>
            <div class="detail-field"><span class="detail-label">分公司</span><span class="detail-value">{{ asset.分公司 }}</span></div>
            <div class="detail-field"><span class="detail-label">所属部门</span><span class="detail-value">{{ asset.所属部门 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">使用人</span><span class="detail-value">{{ asset.使用人 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">当前状态</span><span class="detail-value"><StatusBadge :status="asset.当前状态" /></span></div>
            <div class="detail-field"><span class="detail-label">是否充足</span><span class="detail-value">{{ asset.是否充足 ? '充足' : '不足' }}</span></div>
          </div>
        </div>
        <!-- 数量与价值 -->
        <div class="detail-section">
          <h4 class="detail-section-title">数量与价值</h4>
          <div class="detail-grid">
            <div class="detail-field"><span class="detail-label">数量</span><span class="detail-value">{{ asset.数量 }}</span></div>
            <div class="detail-field"><span class="detail-label">警戒线</span><span class="detail-value">{{ asset.警戒线 ?? '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">单价</span><span class="detail-value">{{ formatMoney(asset.单价 ?? 0) }}</span></div>
            <div class="detail-field"><span class="detail-label">购入金额</span><span class="detail-value">{{ formatMoney(asset.购入金额 ?? 0) }}</span></div>
          </div>
        </div>
        <!-- 日期信息 -->
        <div class="detail-section">
          <h4 class="detail-section-title">日期信息</h4>
          <div class="detail-grid">
            <div class="detail-field"><span class="detail-label">入库日期</span><span class="detail-value">{{ asset.入库日期 || '-' }}</span></div>
            <div class="detail-field"><span class="detail-label">出库日期</span><span class="detail-value">{{ asset.出库日期 || '-' }}</span></div>
          </div>
        </div>
        <!-- 图片 -->
        <div v-if="asset.图片" class="detail-section">
          <h4 class="detail-section-title">资产图片</h4>
          <img :src="asset.图片" alt="资产图片" class="detail-image" />
        </div>
        <!-- 备注 -->
        <div v-if="asset.备注" class="detail-section">
          <h4 class="detail-section-title">备注</h4>
          <p class="detail-remarks">{{ asset.备注 }}</p>
        </div>
        <!-- 流转历史 -->
        <div class="detail-section">
          <h4 class="detail-section-title">流转历史</h4>
          <div v-if="loading" class="detail-loading">加载中...</div>
          <div v-else-if="transfers.length === 0" class="detail-empty">暂无流转记录</div>
          <div v-else class="transfer-timeline">
            <div v-for="t in transfers" :key="t.id" class="timeline-item">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <div class="timeline-header">
                  <span class="timeline-type">{{ actionLabel(t.action_type) }}</span>
                  <span class="timeline-date">{{ t.createdAt }}</span>
                </div>
                <div class="timeline-detail">{{ t.资产名称 }} × {{ t.调拨数量 }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drawer-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; display: flex; justify-content: flex-end; }
.drawer-panel { width: 480px; max-width: 90vw; background: var(--color-bg-elevated); height: 100vh; overflow-y: auto; box-shadow: -4px 0 20px rgba(0,0,0,0.1); }
.drawer-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); }
.drawer-header h3 { margin: 0; font-size: 18px; }
.drawer-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--color-text-secondary); }
.drawer-body { padding: 24px; }
.detail-section { margin-bottom: 24px; }
.detail-section-title { font-size: 15px; font-weight: 600; margin: 0 0 12px; color: var(--color-text-primary); border-bottom: 1px solid var(--color-border); padding-bottom: 8px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.detail-field { display: flex; flex-direction: column; gap: 2px; }
.detail-label { font-size: 12px; color: var(--color-text-secondary); }
.detail-value { font-size: 14px; font-weight: 500; }
.detail-value.code { font-family: monospace; color: var(--color-primary); }
.detail-image { max-width: 100%; border-radius: 8px; }
.detail-remarks { font-size: 14px; color: var(--color-text-secondary); margin: 0; white-space: pre-line; }
.detail-loading, .detail-empty { text-align: center; padding: 20px; color: var(--color-text-secondary); font-size: 14px; }
.transfer-timeline { position: relative; padding-left: 20px; }
.timeline-item { position: relative; padding-bottom: 16px; display: flex; gap: 12px; }
.timeline-dot { position: absolute; left: -20px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background: var(--color-primary); }
.timeline-content { flex: 1; }
.timeline-header { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
.timeline-type { font-weight: 600; }
.timeline-date { color: var(--color-text-secondary); }
.timeline-detail { font-size: 13px; color: var(--color-text-secondary); }
</style>
