<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAssetStocks, getFixedAssets } from '@/api/assets'
import { ElMessage } from 'element-plus'
import type { AssetStock, FixedAsset } from '@/types'

/** 台账行详情（P2 第三刀：Asset 退役，移动端详情 = 分公司×品目 台账行 + 其实例） */
const route = useRoute()
const router = useRouter()

const stockId = computed(() => route.params.id as string)
const stock = ref<AssetStock | null>(null)
const instances = ref<FixedAsset[]>([])
const loading = ref(true)

async function fetchDetail() {
  loading.value = true
  try {
    const { data } = await getAssetStocks({ pageSize: 100 })
    const rows = data.results || []
    stock.value = rows.find(r => r.id === stockId.value) || null
    if (!stock.value) {
      ElMessage.error('台账行不存在')
      router.back()
      return
    }
    if (stock.value.管理方式 === 'instance') {
      const inst = await getFixedAssets({
        asset_code: stock.value.资产编号,
        branch: stock.value.branchName || undefined,
        pageSize: 100,
      })
      instances.value = inst.data.results || []
    }
  } catch (error) {
    ElMessage.error('获取台账行失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const statusText = computed(() => {
  if (!stock.value) return ''
  return stock.value.是否充足 === false ? '库存不足' : '库存正常'
})

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
      <h1>台账行详情</h1>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <span>加载中...</span>
    </div>

    <!-- 详情内容 -->
    <div v-else-if="stock" class="detail-content">
      <!-- 品目与状态 -->
      <div class="status-card">
        <div class="status-badge" :class="{ warn: stock.是否充足 === false }">
          {{ statusText }}
        </div>
        <div class="asset-names">
          <h2 class="asset-name">{{ stock.资产名称 }}</h2>
          <p class="asset-code">{{ stock.资产编号 }}</p>
        </div>
      </div>

      <!-- 数量四列 -->
      <div class="info-section">
        <h3 class="section-title">库存（{{ stock.branchName }}）</h3>
        <div class="info-grid">
          <div class="info-item"><span class="info-label">在库</span><span class="info-value">{{ stock.在库数量 }}</span></div>
          <div class="info-item"><span class="info-label">在用</span><span class="info-value">{{ stock.在用数量 }}</span></div>
          <div class="info-item"><span class="info-label">回收库</span><span class="info-value">{{ stock.回收库数量 }}</span></div>
          <div class="info-item"><span class="info-label">总量</span><span class="info-value">{{ stock.总量 ?? (stock.在库数量 + stock.在用数量 + stock.回收库数量) }}</span></div>
        </div>
      </div>

      <!-- 品目信息 -->
      <div class="info-section">
        <h3 class="section-title">品目信息</h3>
        <div class="info-grid">
          <div class="info-item"><span class="info-label">资产类目</span><span class="info-value">{{ stock.资产类目 || '-' }}</span></div>
          <div class="info-item"><span class="info-label">规格</span><span class="info-value">{{ stock.规格 || '-' }}</span></div>
          <div class="info-item"><span class="info-label">管理方式</span><span class="info-value">{{ stock.管理方式 === 'instance' ? '实例管理' : '数量管理' }}</span></div>
          <div class="info-item"><span class="info-label">警戒线</span><span class="info-value">{{ stock.生效警戒线 ?? '—' }}</span></div>
        </div>
      </div>

      <!-- 实例列表（实例管理品目） -->
      <div v-if="instances.length" class="info-section">
        <h3 class="section-title">实例档案（{{ instances.length }}）</h3>
        <div class="instance-list">
          <div v-for="inst in instances" :key="inst.id" class="instance-row">
            <span class="instance-code">{{ inst.内部编号 }}</span>
            <span class="instance-state">{{ inst.当前状态 }}</span>
            <span class="instance-user">{{ inst.使用人 || (inst.序列号 || '待补录') }}</span>
          </div>
        </div>
      </div>
      <p v-else-if="stock.管理方式 === 'instance'" class="dim-hint">该品目暂无实例档案（新采购入库后自动生成）</p>
    </div>
  </div>
</template>

<style scoped>
.asset-detail-page { min-height: 100vh; background: var(--color-bg-page); padding-bottom: 24px; }
.page-header { display: flex; align-items: center; gap: 12px; padding: 16px; background: var(--color-bg-card); border-bottom: 1px solid var(--color-border); }
.page-header h1 { margin: 0; font-size: 18px; font-weight: 600; color: var(--color-text-primary); }
.back-btn { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; color: var(--color-text-primary); cursor: pointer; }
.back-btn svg { width: 20px; height: 20px; }
.loading-state { display: flex; justify-content: center; padding: 48px 0; color: var(--color-text-tertiary); }
.detail-content { padding: 16px; display: flex; flex-direction: column; gap: 16px; }
.status-card { display: flex; align-items: center; gap: 14px; padding: 16px; background: var(--color-bg-card); border-radius: 12px; }
.status-badge { padding: 6px 12px; border-radius: 16px; font-size: 13px; font-weight: 600; color: white; background: var(--color-success); }
.status-badge.warn { background: var(--color-warning); }
.asset-names { min-width: 0; }
.asset-name { margin: 0; font-size: 17px; font-weight: 600; color: var(--color-text-primary); }
.asset-code { margin: 4px 0 0; font-family: var(--font-mono); font-size: 13px; color: var(--color-text-tertiary); }
.info-section { background: var(--color-bg-card); border-radius: 12px; padding: 16px; }
.section-title { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: var(--color-text-secondary); }
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 12px; color: var(--color-text-tertiary); }
.info-value { font-size: 15px; font-weight: 600; color: var(--color-text-primary); }
.instance-list { display: flex; flex-direction: column; }
.instance-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--color-border-light); font-size: 13px; }
.instance-row:last-child { border-bottom: none; }
.instance-code { font-family: var(--font-mono); color: var(--color-primary-600); min-width: 120px; }
.instance-state { color: var(--color-text-secondary); flex: 1; }
.instance-user { color: var(--color-text-tertiary); }
.dim-hint { margin: 0; font-size: 12px; color: var(--color-text-tertiary); text-align: center; }
</style>
