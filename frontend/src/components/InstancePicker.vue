<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getFixedAssets } from '@/api/assets'
import type { FixedAsset } from '@/types'

/**
 * 实例点选器（单选）：按 分公司×品目×状态 拉可选实例，点选即定并收起、再点换选。
 * 一行一台、多台走多行（instance-single-pick-and-timeline-zh：多选勾选模式退役）。
 * excludedIds 剔除本单他行已选（跨行去重）；展开态受控（v-model:expanded，编辑器做同屏互斥）。
 */
const props = defineProps<{
  itemCode: string
  /** 合法前置状态：领用按来源 在库/回收库；归还=在用；调拨/回收处置=在库或用（逗号多值） */
  status: string
  /** 分公司名（为空则不限） */
  branchName?: string
  modelValue: string[]
  /** 本单其他行已选实例 id（候选剔除；本行已选保留高亮回显） */
  excludedIds?: string[]
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void
  (e: 'change', selected: FixedAsset[]): void
}>()

const expanded = defineModel<boolean>('expanded', { default: false })

const options = ref<FixedAsset[]>([])
const loading = ref(false)

/** 候选 = 拉取结果 − 他行已选 ∪ 本行已选（高亮回显） */
const candidates = computed(() => {
  const excluded = new Set(props.excludedIds || [])
  return options.value.filter(o => !excluded.has(o.id) || props.modelValue.includes(o.id))
})

async function load() {
  loading.value = true
  try {
    const { data } = await getFixedAssets({
      page: 1,
      pageSize: 100,
      asset_code: props.itemCode,
      status: props.status,
      branch: props.branchName || undefined,
    })
    options.value = data.results
  } finally {
    loading.value = false
  }
}

watch(expanded, (v) => { if (v) load() })
watch(() => [props.itemCode, props.status, props.branchName], () => {
  if (expanded.value) load()
})

/** 点选即定（换选覆盖）并收起面板 */
function pickSingle(id: string) {
  emit('update:modelValue', [id])
  emit('change', options.value.filter(o => o.id === id))
  expanded.value = false
}

defineExpose({ reload: load })
</script>

<template>
  <div class="instance-picker">
    <button type="button" class="picker-toggle" @click="expanded = !expanded">
      {{ modelValue.length > 0 ? '已选 1 台' : '点选实例' }}
      <span class="picker-count">（{{ status }}态 · {{ itemCode }}）</span>
    </button>
    <div v-if="expanded" class="picker-panel">
      <div v-if="loading" class="picker-empty">加载中...</div>
      <div v-else-if="candidates.length === 0" class="picker-empty">无可选实例（{{ status }}态为空或已被其他行选中）</div>
      <div
        v-for="opt in candidates" :key="opt.id" class="picker-row"
        :class="{ picked: modelValue.includes(opt.id) }"
        @click="pickSingle(opt.id)"
      >
        <span class="row-dot" :class="{ on: modelValue.includes(opt.id) }"></span>
        <span class="row-code">{{ opt.内部编号 }}</span>
        <span class="row-serial">{{ opt.序列号 || '待补录' }}</span>
        <span class="row-branch">{{ opt.branchName }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.instance-picker { display: flex; flex-direction: column; gap: 4px; }
.picker-toggle { display: flex; align-items: center; gap: 6px; height: 32px; padding: 0 10px; background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 6px; color: var(--color-primary-600); font-size: 13px; cursor: pointer; }
.picker-toggle:hover { background: var(--color-primary-100); }
.picker-count { font-size: 11px; color: var(--color-text-tertiary); }
.picker-panel { max-height: 220px; overflow-y: auto; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-bg-card); }
.picker-empty { padding: 12px; font-size: 12px; color: var(--color-text-tertiary); text-align: center; }
.picker-row { display: flex; align-items: center; gap: 8px; padding: 6px 10px; font-size: 12px; cursor: pointer; border-bottom: 1px solid var(--color-border-light); }
.picker-row:last-child { border-bottom: none; }
.picker-row:hover { background: var(--color-bg-elevated); }
.row-dot { width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--color-border); background: var(--color-bg-card); flex-shrink: 0; }
.row-dot.on { border-color: var(--color-primary-500); background: var(--color-primary-500); box-shadow: inset 0 0 0 3px var(--color-bg-card); }
.picker-row.picked { background: var(--color-primary-50); }
.row-code { font-family: var(--font-mono); color: var(--color-primary-600); min-width: 110px; }
.row-serial { color: var(--color-text-secondary); flex: 1; }
.row-branch { color: var(--color-text-tertiary); }
</style>
