<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAssets } from '@/api/assets'
import { ElMessage } from 'element-plus'
import type { Asset } from '@/types'

const router = useRouter()
const searchQuery = ref('')
const assets = ref<Asset[]>([])
const loading = ref(false)
const recentSearches = ref<string[]>([])

const statusColors: Record<string, string> = {
  '在库': 'var(--color-success)',
  '使用中': 'var(--color-primary-500)',
  '维修中': 'var(--color-warning)',
  '报废': 'var(--color-danger)',
}

async function handleSearch() {
  if (!searchQuery.value.trim()) return
  loading.value = true
  try {
    const { data } = await getAssets({
    keyword: searchQuery.value.trim(),
    pageSize: 20,
  })
    assets.value = data.results || []
    if (assets.value.length > 0) {
    const query = searchQuery.value.trim()
    if (!recentSearches.value.includes(query)) {
      recentSearches.value.unshift(query)
      recentSearches.value = recentSearches.value.slice(0, 10)
    }
  }
  } catch (error: any) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

function handleScan() {
  router.push('/mobile/scan')
}

function viewAsset(asset: Asset) {
  router.push(`/mobile/assets/${asset.id}`)
}

function formatTime(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="asset-search-page">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <div class="search-input-wrapper">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <input
          v-model="searchQuery"
          type="search"
          placeholder="输入资产编号或名称..."
          @keyup.enter="handleSearch"
        />
      </div>
      <button class="scan-btn" @click="handleScan">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
          <line x1="7" y1="12" x2="17" y2="12"/>
        </svg>
      </button>
    </div>

    <!-- 搜索历史 -->
    <div v-if="!searchQuery && recentSearches.length" class="recent-section">
      <h3>最近搜索</h3>
      <div class="recent-tags">
        <span
          v-for="term in recentSearches"
          :key="term"
          class="recent-tag"
          @click="searchQuery = term; handleSearch()"
        >
          {{ term }}
        </span>
      </div>
    </div>

    <!-- 搜索结果 -->
    <div v-if="assets.length" class="result-list">
      <div
        v-for="asset in assets"
        :key="asset.id"
        class="asset-card"
        @click="viewAsset(asset)"
      >
        <div class="asset-image">
          <img v-if="asset.图片" :src="asset.图片" />
          <div v-else class="asset-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
            </svg>
          </div>
        </div>
        <div class="asset-info">
          <div class="asset-code">{{ asset.资产编号 }}</div>
          <div class="asset-name">{{ asset.资产名称 }}</div>
          <div class="asset-meta">
            <span class="asset-branch">{{ asset.分公司 }}</span>
            <span
              class="asset-status"
              :style="{ background: statusColors[asset.当前状态] || 'var(--color-text-tertiary)' }"
            >
              {{ asset.当前状态 }}
            </span>
          </div>
        </div>
        <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="searchQuery && !loading" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="11" cy="11" r="8"/>
        <path d="M21 21l-4.35-4.35"/>
      </svg>
      <p>未找到匹配的资产</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <span>搜索中...</span>
    </div>
  </div>
</template>

<style scoped>
.asset-search-page {
  padding: var(--space-4);
}

.search-bar {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.search-input-wrapper {
  flex: 1;
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: var(--color-text-tertiary);
}

.search-input-wrapper input {
  width: 100%;
  height: 44px;
  padding: 0 var(--space-4) 0 40px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-card);
  font-size: 15px;
}

.search-input-wrapper input:focus {
  outline: none;
  border-color: var(--color-primary-500);
}

.scan-btn {
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: var(--color-primary-500);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.scan-btn svg {
  width: 22px;
  height: 22px;
}

.recent-section {
  margin-bottom: var(--space-4);
}

.recent-section h3 {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-2);
}

.recent-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.recent-tag {
  padding: 6px 12px;
  background: var(--color-bg-elevated);
  border-radius: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.asset-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--space-3);
  margin-bottom: var(--space-3);
  cursor: pointer;
}

.asset-image {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.asset-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.asset-placeholder {
  width: 100%;
  height: 100%;
  background: var(--color-bg-elevated);
  display: flex;
  align-items: center;
  justify-content: center;
}

.asset-placeholder svg {
  width: 24px;
  height: 24px;
  color: var(--color-text-tertiary);
}

.asset-info {
  flex: 1;
  min-width: 0;
}

.asset-code {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--color-text-tertiary);
}

.asset-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin-top: 2px;
}

.asset-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: 4px;
}

.asset-branch {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.asset-status {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  color: white;
}

.arrow-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.empty-state,
.loading-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin-bottom: var(--space-3);
}
</style>
