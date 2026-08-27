<script setup lang="ts">
import { ref } from 'vue'
import { ElSelect, ElOption } from 'element-plus'
import { MANAGEMENT_TYPE_LABELS } from '@/constants'
import { getCategories } from '@/api/categories'
import type { ItemSummary } from '@/types'

/** 品目字典点选：按编号/名称远程检索，选中回显规格/类目/管理方式（禁手抄编号） */
const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'change', item: ItemSummary | null): void
}>()

const options = ref<ItemSummary[]>([])
const loading = ref(false)

let searchSeq = 0
async function remoteSearch(query: string) {
  const seq = ++searchSeq
  loading.value = true
  try {
    const { data } = await getCategories({ keyword: query || undefined, pageSize: 50 })
    if (seq !== searchSeq) return
    const results = (data as any).results ?? data
    // 字典接口输出中文键，映射为 ItemSummary
    options.value = (results as any[]).map((c) => ({
      id: c.id,
      asset_code: c.资产编号,
      asset_name: c.资产名称,
      specification: c.规格,
      unit: c.计量单位,
      assetCategory: c.资产类目,
      itemCategory: c.物品分类,
      managementType: c.管理方式,
    }))
  } catch {
    if (seq === searchSeq) options.value = []
  } finally {
    if (seq === searchSeq) loading.value = false
  }
}

function onChange(value: string) {
  const picked = options.value.find((o) => o.id === value) ?? null
  emit('change', picked)
}
</script>

<template>
  <ElSelect
    :model-value="props.modelValue"
    filterable
    remote
    clearable
    :remote-method="remoteSearch"
    :loading="loading"
    :placeholder="props.placeholder || '输入编号或名称检索品目'"
    style="width: 100%"
    @update:model-value="(v: string) => emit('update:modelValue', v)"
    @change="onChange"
    @visible-change="(open: boolean) => open && !options.length && remoteSearch('')"
  >
    <ElOption v-for="opt in options" :key="opt.id" :value="opt.id" :label="`${opt.asset_code} ${opt.asset_name}`">
      <div class="item-option">
        <span class="item-code">{{ opt.asset_code }}</span>
        <span class="item-name">{{ opt.asset_name }}</span>
        <span v-if="opt.specification" class="item-meta">{{ opt.specification }}</span>
        <span class="item-meta">{{ opt.assetCategory }}/{{ opt.itemCategory }}</span>
        <span class="item-meta">{{ MANAGEMENT_TYPE_LABELS[opt.managementType ?? ''] || opt.managementType }}</span>
      </div>
    </ElOption>
  </ElSelect>
</template>

<style scoped>
.item-option { display: flex; align-items: center; gap: 8px; min-width: 0; }
.item-code { font-family: var(--font-mono); font-size: 12px; color: var(--color-primary-600); }
.item-name { font-size: 13px; }
.item-meta { font-size: 12px; color: var(--color-text-tertiary); }
</style>
