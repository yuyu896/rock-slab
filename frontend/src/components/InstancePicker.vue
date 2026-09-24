<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { getFixedAssets } from '@/api/assets'
import request from '@/utils/request'
import type { FixedAsset } from '@/types'

/**
 * 实例点选器（单选）：按 分公司×品目×状态 拉可选实例，点选即定并收起、再点换选。
 * 一行一台、多台走多行（instance-single-pick-and-timeline-zh）。
 * instance-picker-completeness：未选分公司禁用；候选滚动加载（破 100 截断）+
 * 内部编号/序列号搜索；未生效单据占用行置灰标注单号（预检才是权威闸门）。
 * excludedIds 剔除本单他行已选；展开态受控（编辑器做同屏互斥）。
 */
const props = defineProps<{
  itemCode: string
  /** 合法前置状态：领用按来源 在库/回收库；归还=在用；调拨/回收处置=在库或用（逗号多值） */
  status: string
  /** 分公司名（未选则禁用） */
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
const page = ref(1)
const hasMore = ref(false)
const search = ref('')
const occupancy = ref(new Map<string, { docNo: string; docStatus: string }>())

const disabled = computed(() => !props.branchName)

/** 候选 = 拉取结果 − 他行已选 − 占用置灰不剔除（标注可见）∪ 本行已选（高亮回显） */
const candidates = computed(() => {
  const excluded = new Set(props.excludedIds || [])
  return options.value.filter(o => !excluded.has(o.id) || props.modelValue.includes(o.id))
})

const occOf = (id: string) => occupancy.value.get(id)

function occLabel(id: string): string {
  const occ = occupancy.value.get(id)
  return occ ? `${occ.docStatus}单 ${occ.docNo} 占用` : ''
}

async function loadOccupancy() {
  occupancy.value = new Map()
  if (!props.branchName || !props.itemCode) return
  try {
    const { data } = await request.get('/api/transfers/instance-occupancy', {
      params: { branch: props.branchName, asset_code: props.itemCode },
    })
    occupancy.value = new Map(
      ((data as any[]) || []).map(o => [o.instanceId, { docNo: o.docNo, docStatus: o.docStatus }]),
    )
  } catch { /* 占用标注失败不阻断点选（预检为权威闸门） */ }
}

async function load(reset = false) {
  if (disabled.value) return
  if (reset) {
    page.value = 1
    options.value = []
  }
  loading.value = true
  const currentPage = page.value
  try {
    const { data } = await getFixedAssets({
      page: currentPage,
      pageSize: 100,
      asset_code: props.itemCode,
      status: props.status,
      branch: props.branchName || undefined,
      inner_keyword: search.value || undefined,
    } as any)
    options.value = reset ? data.results : [...options.value, ...data.results]
    hasMore.value = Boolean(data.next)
    if (reset) loadOccupancy()
  } finally {
    loading.value = false
  }
}

/** 面板滚动触底翻页（破 100 条截断） */
function onPanelScroll(e: Event) {
  const el = e.target as HTMLElement
  if (loading.value || !hasMore.value) return
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 30) {
    page.value += 1
    load()
  }
}

watch(expanded, (v) => { if (v) load(true) })
watch(() => [props.itemCode, props.status, props.branchName], () => {
  if (expanded.value) load(true)
})
watch(search, () => {
  if (expanded.value) load(true)
})

/** 点选即定（换选覆盖）并收起面板；占用实例不可选 */
function pickSingle(opt: FixedAsset) {
  if (occupancy.value.has(opt.id)) return
  emit('update:modelValue', [opt.id])
  emit('change', [opt])
  expanded.value = false
}

defineExpose({ reload: () => load(true) })
</script>

<template>
  <div class="instance-picker">
    <button
      type="button" class="picker-toggle" :disabled="disabled"
      :title="disabled ? '请先选择所属分公司' : ''"
      @click="!disabled && (expanded = !expanded)"
    >
      {{ disabled ? '请先选择所属分公司' : (modelValue.length > 0 ? '已选 1 台' : '点选实例') }}
      <span v-if="!disabled" class="picker-count">（{{ status }}态 · {{ itemCode }}）</span>
    </button>
    <div v-if="expanded && !disabled" class="picker-panel" @scroll.passive="onPanelScroll">
      <div class="picker-search">
        <input
          v-model="search" type="text" class="search-input"
          placeholder="搜内部编号 / 序列号" @click.stop
        >
      </div>
      <div v-if="loading && options.length === 0" class="picker-empty">加载中...</div>
      <div v-else-if="candidates.length === 0" class="picker-empty">无可选实例（{{ status }}态为空或已被其他行选中）</div>
      <div
        v-for="opt in candidates" :key="opt.id" class="picker-row"
        :class="{ picked: modelValue.includes(opt.id), occupied: occOf(opt.id) }"
        @click="pickSingle(opt)"
      >
        <span class="row-dot" :class="{ on: modelValue.includes(opt.id) }"></span>
        <span class="row-code">{{ opt.内部编号 }}</span>
        <span class="row-serial">{{ opt.序列号 || '待补录' }}</span>
        <span class="row-branch">{{ opt.branchName }}</span>
        <span v-if="occOf(opt.id)" class="row-occ" title="不可选">{{ occLabel(opt.id) }}</span>
      </div>
      <div v-if="loading && options.length > 0" class="picker-empty">加载更多...</div>
      <div v-else-if="!hasMore && options.length > 0" class="picker-end">共 {{ options.length }} 台</div>
    </div>
  </div>
</template>

<style scoped>
.instance-picker { display: flex; flex-direction: column; gap: 4px; }
.picker-toggle { display: flex; align-items: center; gap: 6px; height: 32px; padding: 0 10px; background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 6px; color: var(--color-primary-600); font-size: 13px; cursor: pointer; }
.picker-toggle:disabled { background: var(--color-bg-elevated); color: var(--color-text-tertiary); cursor: not-allowed; border-color: var(--color-border); }
.picker-toggle:hover:not(:disabled) { background: var(--color-primary-100); }
.picker-count { font-size: 11px; color: var(--color-text-tertiary); }
.picker-panel { max-height: 260px; overflow-y: auto; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-bg-card); }
.picker-search { position: sticky; top: 0; padding: 6px; background: var(--color-bg-card); border-bottom: 1px solid var(--color-border-light); z-index: 1; }
.search-input { width: 100%; height: 28px; padding: 0 8px; border: 1px solid var(--color-border); border-radius: 4px; font-size: 12px; box-sizing: border-box; }
.search-input:focus { outline: none; border-color: var(--color-primary-400); }
.picker-empty, .picker-end { padding: 10px; font-size: 12px; color: var(--color-text-tertiary); text-align: center; }
.picker-row { display: flex; align-items: center; gap: 8px; padding: 6px 10px; font-size: 12px; cursor: pointer; border-bottom: 1px solid var(--color-border-light); }
.picker-row:last-child { border-bottom: none; }
.picker-row:hover { background: var(--color-bg-elevated); }
.picker-row input { width: 14px; height: 14px; }
.row-dot { width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--color-border); background: var(--color-bg-card); flex-shrink: 0; }
.row-dot.on { border-color: var(--color-primary-500); background: var(--color-primary-500); box-shadow: inset 0 0 0 3px var(--color-bg-card); }
.picker-row.picked { background: var(--color-primary-50); }
.picker-row.occupied { opacity: 0.55; cursor: not-allowed; }
.row-occ { flex-shrink: 0; font-size: 11px; color: var(--color-text-tertiary); }
.row-code { font-family: var(--font-mono); color: var(--color-primary-600); min-width: 110px; }
.row-serial { color: var(--color-text-secondary); flex: 1; }
.row-branch { color: var(--color-text-tertiary); }
</style>
