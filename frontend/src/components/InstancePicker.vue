<script setup lang="ts">
import { ref, watch } from 'vue'
import { getFixedAssets } from '@/api/assets'
import type { FixedAsset } from '@/types'

/**
 * 实例点选器：按 分公司×品目×状态 拉可选实例，勾选集经 v-model（uuid 数组）上行。
 * 用于实例管理品目的领用/归还/调拨/回收明细行（P2 第二刀）；已选回显由父组件承担。
 */
const props = defineProps<{
  itemCode: string
  /** 合法前置状态：领用按来源 在库/回收库；归还/回收=在用；调拨=在库 */
  status: string
  /** 分公司名（为空则不限） */
  branchName?: string
  modelValue: string[]
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void
  (e: 'change', selected: FixedAsset[]): void
}>()

const options = ref<FixedAsset[]>([])
const loading = ref(false)
const expanded = ref(false)

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

function toggle(id: string) {
  const next = props.modelValue.includes(id)
    ? props.modelValue.filter(x => x !== id)
    : [...props.modelValue, id]
  emit('update:modelValue', next)
  emit('change', options.value.filter(o => next.includes(o.id)))
}

defineExpose({ reload: load })
</script>

<template>
  <div class="instance-picker">
    <button type="button" class="picker-toggle" @click="expanded = !expanded">
      {{ modelValue.length > 0 ? `已选 ${modelValue.length} 台` : '选择实例' }}
      <span class="picker-count">（{{ status }}态 · {{ itemCode }}）</span>
    </button>
    <div v-if="expanded" class="picker-panel">
      <div v-if="loading" class="picker-empty">加载中...</div>
      <div v-else-if="options.length === 0" class="picker-empty">无可选实例（{{ status }}态为空）</div>
      <label v-for="opt in options" :key="opt.id" class="picker-row">
        <input type="checkbox" :checked="modelValue.includes(opt.id)" @change="toggle(opt.id)" />
        <span class="row-code">{{ opt.内部编号 }}</span>
        <span class="row-serial">{{ opt.序列号 || '待补录' }}</span>
        <span class="row-branch">{{ opt.branchName }}</span>
      </label>
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
.picker-row input { width: 14px; height: 14px; }
.row-code { font-family: var(--font-mono); color: var(--color-primary-600); min-width: 110px; }
.row-serial { color: var(--color-text-secondary); flex: 1; }
.row-branch { color: var(--color-text-tertiary); }
</style>
