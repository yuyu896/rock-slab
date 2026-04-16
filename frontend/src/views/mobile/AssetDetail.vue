<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAsset } from '@/api/assets'
import { ElMessage } from 'element-plus'
import type { Asset } from '@/types'

const route = useRoute()
const router = useRouter()

const assetId = computed(() => route.params.id as string)
const asset = ref<Asset | null>(null)
const loading = ref(true)

const statusColors: Record<string, string> = {
  '在库': 'var(--color-success)',
  '使用中': 'var(--color-primary-500)',
  '维修中': 'var(--color-warning)',
  '报废': 'var(--color-danger)',
}

const statusLabels: Record<string, string> = {
  '在库': '在库',
  '使用中': '使用中',
  '维修中': '维修中',
  '报废': '报废',
}

async function fetchDetail() {
  loading.value = true
  try {
    const { data } = await getAsset(assetId.value)
    asset.value = data
  } catch (error) {
    ElMessage.error('获取资产详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function formatCurrency(value: number | undefined | null): string {
  if (value == null || value === undefined) return '-'
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
  }).format(value)
}

onMounted(() => {
  fetchDetail()
})
</script>

<template>
  <div class="asset-detail-page">
    <!-- 头部导航 -->
    <div class="page-header">
      <button class="back-btn" @click="router.back()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
      <h1>资产详情</h1>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <span>加载中...</span>
    </div>

    <!-- 详情内容 -->
    <div v-else-if="asset" class="detail-content">
      <!-- 资产图片 -->
      <div class="asset-image-section">
        <img v-if="asset.图片" :src="asset.图片" />
        <div v-else class="asset-placeholder">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
          </svg>
        </div>
      </div>

      <!-- 状态卡片 -->
      <div class="status-card">
        <div class="status-badge" :style="{ background: statusColors[asset.当前状态] }">
          {{ statusLabels[asset.当前状态] }}
        </div>
        <div class="asset-names">
          <h2 class="asset-name">{{ asset.资产名称 }}</h2>
          <p class="asset-code">{{ asset.资产编号 }}</p>
        </div>
      </div>

      <!-- 基本信息 -->
      <div class="info-section">
        <h3 class="section-title">基本信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">资产类目</span>
            <span class="value">{{ asset.资产类目 }}</span>
          </div>
          <div class="info-item">
            <span class="label">物品分类</span>
            <span class="value">{{ asset.物品分类 }}</span>
          </div>
          <div class="info-item">
            <span class="label">规格型号</span>
            <span class="value">{{ asset.规格 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">供应商</span>
            <span class="value">{{ asset.供应商 || '-' }}</span>
          </div>
        </div>
      </div>

      <!-- 位置信息 -->
      <div class="info-section">
        <h3 class="section-title">位置信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">分公司</span>
            <span class="value">{{ asset.分公司 }}</span>
          </div>
          <div class="info-item">
            <span class="label">所属部门</span>
            <span class="value">{{ asset.所属部门 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">使用人</span>
            <span class="value">{{ asset.使用人 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">是否充足</span>
            <span class="value" :class="{ warning: asset.是否充足 === false }">
              {{ asset.是否充足 ? '充足' : '不足' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 数量与金额 -->
      <div class="info-section">
        <h3 class="section-title">数量与金额</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">数量</span>
            <span class="value">{{ asset.数量 }}</span>
          </div>
          <div class="info-item">
            <span class="label">警戒线</span>
            <span class="value">{{ asset.警戒线 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">单价</span>
            <span class="value">{{ asset.单价 ? formatCurrency(asset.单价) : '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">购入金额</span>
            <span class="value">{{ asset.购入金额 ? formatCurrency(asset.购入金额) : '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">采购方式</span>
            <span class="value">{{ asset.是否租用 ? '租用' : '自购' }}</span>
          </div>
        </div>
      </div>

      <!-- 日期信息 -->
      <div class="info-section">
        <h3 class="section-title">日期信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">入库日期</span>
            <span class="value">{{ formatDate(asset.入库日期) }}</span>
          </div>
          <div class="info-item">
            <span class="label">出库日期</span>
            <span class="value">{{ formatDate(asset.出库日期) }}</span>
          </div>
        </div>
      </div>

      <!-- 备注 -->
      <div v-if="asset.备注" class="info-section">
        <h3 class="section-title">备注</h3>
        <p class="remarks">{{ asset.备注 }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.asset-detail-page {
  padding: var(--space-4);
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.back-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 10px;
  background: var(--color-bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.back-btn svg {
  width: 20px;
  height: 20px;
  color: var(--color-text-secondary);
}

.page-header h1 {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.loading-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-tertiary);
}

.asset-image-section {
  width: 100%;
  height: 200px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: var(--space-4);
  display: flex;
  align-items: center;
  justify-content: center;
}

.asset-image-section img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.asset-placeholder {
  width: 80px;
  height: 80px;
  color: var(--color-text-tertiary);
}

.asset-placeholder svg {
  width: 100%;
  height: 100%;
}

.status-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.status-badge {
  padding: var(--space-2) var(--space-3);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: white;
}

.asset-names {
  flex: 1;
}

.asset-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.asset-code {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--color-text-tertiary);
  margin: 4px 0 0;
}

.info-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  margin-bottom: var(--space-3);
  overflow: hidden;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-elevated);
  margin: 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  padding: var(--space-4);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.info-item .value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.info-item .value.warning {
  color: var(--color-danger);
}

.remarks {
  padding: var(--space-4);
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}
</style>
