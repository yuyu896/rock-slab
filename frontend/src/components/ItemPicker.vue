<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElSelect, ElOption } from 'element-plus'
import { MANAGEMENT_TYPE_LABELS } from '@/constants'
import { getCategories } from '@/api/categories'
import { getAssetStocks } from '@/api/assets'
import type { ItemSummary } from '@/types'

/** 品目点选：按编号/名称远程检索，选中回显规格/类目/管理方式（禁手抄编号）。
 *  双数据源：传 stockColumn 时以所选分公司的台账行为源（对应列>0 才可选，
 *  选项行显示可用数量）——写单页"只给能选的"；否则维持全量字典检索。 */
const props = defineProps<{
  modelValue: string
  placeholder?: string
  /** 分公司名称（台账检索前置条件，空则禁用） */
  branch?: string
  /** 扣数列（有值走台账检索）：领用新品库/调拨=在库，领用回收库=回收库，回收=在用 */
  stockColumn?: '在库数量' | '在用数量' | '回收库数量'
  /** 剔除消耗品（回收库来源：领出即耗用品目不得走回收库） */
  excludeConsumable?: boolean
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'change', item: ItemSummary | null): void
}>()

const options = ref<ItemSummary[]>([])
const loading = ref(false)

const COLUMN_LABELS: Record<string, string> = {
  在库数量: '在库',
  在用数量: '在用',
  回收库数量: '回收库',
}

const usesLedger = computed(() => Boolean(props.stockColumn))
const columnLabel = computed(() => COLUMN_LABELS[props.stockColumn ?? ''] ?? '')
const disabled = computed(() => usesLedger.value && !props.branch)
const placeholder = computed(() => {
  if (disabled.value) return '请先选择分公司'
  return props.placeholder || '输入编号或名称检索品目'
})

let searchSeq = 0
async function remoteSearch(query: string) {
  if (disabled.value) return
  const seq = ++searchSeq
  loading.value = true
  try {
    if (usesLedger.value) {
      const { data } = await getAssetStocks({
        branch: props.branch,
        keyword: query || undefined,
        positive_column: props.stockColumn,
        pageSize: 50,
      })
      if (seq !== searchSeq) return
      // 台账接口输出中文键，映射为 ItemSummary；qty 供选项行展示可用数量
      options.value = ((data as any).results ?? [])
        .filter((c: any) => !(props.excludeConsumable && c.管理方式 === 'consumable'))
        .map((c: any) => ({
          id: c.item,
          asset_code: c.资产编号,
          asset_name: c.资产名称,
          specification: c.规格,
          unit: c.计量单位,
          assetCategory: c.资产类目,
          itemCategory: c.物品分类,
          managementType: c.管理方式,
          qty: c[props.stockColumn ?? ''] as number | undefined,
        }))
    } else {
      const { data } = await getCategories({ keyword: query || undefined, pageSize: 50 })
      if (seq !== searchSeq) return
      const results = (data as any).results ?? data
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
    }
  } catch {
    if (seq === searchSeq) options.value = []
  } finally {
    if (seq === searchSeq) loading.value = false
  }
}

/** 分公司/扣数列变化后旧选项失效，清空待重查 */
watch(
  () => [props.branch, props.stockColumn],
  () => {
    options.value = []
  },
)

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
    :disabled="disabled"
    :remote-method="remoteSearch"
    :loading="loading"
    :placeholder="placeholder"
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
        <span v-if="usesLedger && opt.qty !== undefined" class="item-qty">
          {{ columnLabel }} {{ opt.qty }}
        </span>
      </div>
    </ElOption>
  </ElSelect>
</template>

<style scoped>
.item-option { display: flex; align-items: center; gap: 8px; min-width: 0; }
.item-code { font-family: var(--font-mono); font-size: 12px; color: var(--color-primary-600); }
.item-name { font-size: 13px; }
.item-meta { font-size: 12px; color: var(--color-text-tertiary); }
.item-qty { margin-left: auto; font-size: 12px; color: var(--color-primary-600); flex-shrink: 0; }
</style>
