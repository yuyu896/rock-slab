<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import ItemPicker from '@/components/ItemPicker.vue'
import InstancePicker from '@/components/InstancePicker.vue'
import { getDepartmentOptions, type Department } from '@/api/departments'
import { getSuppliers, type Supplier } from '@/api/suppliers'
import { getAssetStocks } from '@/api/assets'
import { emptyDraft, type LineDraft } from './lineDrafts'
import type { TransferType } from '@/constants'
import type { FixedAsset } from '@/types'

const props = defineProps<{
  modelValue: LineDraft[]
  type: TransferType
  /** 领用行部门/实例选择联动分公司（uuid） */
  branchId?: string
  /** 分公司名（实例点选器按分公司过滤） */
  branchName?: string
  /** 领用来源（stock=新品库 扣在库 / recycle_bin=回收库 扣回收库），仅 assign */
  assignSource?: 'stock' | 'recycle_bin'
  /** 回收去向（restock=仅实例在用 / dispose=在库在用双源、数量行扣在库），仅 recovery */
  recoveryDest?: 'restock' | 'dispose'
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: LineDraft[]): void
}>()

const drafts = ref<LineDraft[]>(props.modelValue.length ? props.modelValue : [emptyDraft()])
watch(
  () => props.modelValue,
  (value) => {
    if (value !== drafts.value) drafts.value = value
  },
)

function touch() {
  emit('update:modelValue', drafts.value)
}

function addRow() {
  drafts.value.push(emptyDraft())
  touch()
}

function removeRow(index: number) {
  drafts.value.splice(index, 1)
  if (drafts.value.length === 0) drafts.value = [emptyDraft()]
  touch()
}

function onItemPicked(index: number, item: any) {
  drafts.value[index].item = item
  // 换品目后既有实例引用失效，清空重选
  if (drafts.value[index].instances.length) {
    drafts.value[index].instances = []
    drafts.value[index].数量 = 1
  }
  if (props.type === 'recovery') loadStockRow(item.asset_code)
  touch()
}

/** 绑定类单据（采购为生成制）：实例管理品目行必须点选实例；归还页接入后补 'return' */
const BINDING_TYPES: TransferType[] = ['assign', 'transfer', 'recovery']
function isInstanceRow(draft: LineDraft): boolean {
  return draft.item?.managementType === 'instance' && BINDING_TYPES.includes(props.type)
}

/** 实例选择器要求的合法前置状态（与后端矩阵一致） */
function pickerStatus(): string {
  if (props.type === 'assign') return props.assignSource === 'recycle_bin' ? '回收库' : '在库'
  if (props.type === 'transfer') return '在库'
  if (props.type === 'recovery') return props.recoveryDest === 'dispose' ? '在库,在用' : '在用'
  return '在用' // return
}

/** 本单全部行已选实例 id：跨行去重下传（本行已选在组件内保留勾选回显） */
const pickedInstanceIds = computed(() =>
  drafts.value.reduce<string[]>((acc, d) => acc.concat(d.instances.map((i) => i.id)), []),
)

/** 同屏互斥：当前展开面板的行 key（null = 全收起） */
const expandedRow = ref<number | null>(null)
function onRowExpand(key: number, value: boolean) {
  expandedRow.value = value ? key : null
}

function onInstancesChange(index: number, selected: FixedAsset[]) {
  drafts.value[index].instances = selected.map((s) => ({ id: s.id, code: s.内部编号 }))
  // 实例行数量 = 选中台数（锁定联动）；领用单台模式恒 1（一行一使用人一实例）
  drafts.value[index].数量 = props.type === 'assign' ? 1 : (selected.length || 1)
  touch()
}

function normalizeNum(value: unknown): number | null {
  if (value === '' || value === null || value === undefined) return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

/** 采购行金额留空自动 = 单价 × 数量；手填不覆盖，清空后回到自动 */
function autoFillAmount(draft: LineDraft) {
  if (draft.金额 === null && draft.单价 !== null) {
    draft.金额 = Number((draft.单价 * draft.数量).toFixed(2))
  }
}

function onQtyChange(index: number) {
  if (props.type === 'purchase') autoFillAmount(drafts.value[index])
  touch()
}

function onPriceChange(index: number) {
  const draft = drafts.value[index]
  draft.单价 = normalizeNum(draft.单价)
  draft.金额 = normalizeNum(draft.金额)
  autoFillAmount(draft)
  touch()
}

function onAmountChange(index: number) {
  drafts.value[index].金额 = normalizeNum(drafts.value[index].金额)
  touch()
}

// 领用行的部门字典（全集团扁平；department 为字典 FK）
const departments = ref<Department[]>([])
watch(
  () => props.type,
  async (type) => {
    if (type !== 'assign') {
      departments.value = []
      return
    }
    try {
      const { data } = await getDepartmentOptions()
      departments.value = data
    } catch {
      departments.value = []
    }
  },
  { immediate: true },
)

// 采购行的供应商字典（全集团扁平；行上存名称文本，字典只做选择来源）
const suppliers = ref<Supplier[]>([])
watch(
  () => props.type,
  async (type) => {
    if (type !== 'purchase') {
      suppliers.value = []
      return
    }
    try {
      const { data } = await getSuppliers({ pageSize: 100 })
      suppliers.value = data.results
    } catch {
      suppliers.value = []
    }
  },
  { immediate: true },
)

const hasInstanceColumn = computed(() => BINDING_TYPES.includes(props.type))

/** 品目点选扣数列收口：领用按来源、调拨在库、回收在用；采购生成制不收口（全量字典） */
const itemStockColumn = computed<string | undefined>(() => {
  if (props.type === 'assign') return props.assignSource === 'recycle_bin' ? '回收库数量' : '在库数量'
  if (props.type === 'transfer') return '在库数量'
  if (props.type === 'recovery') {
    // 处置向双源：品目有在库或在用即可选；重新入库维持仅实例在用
    return props.recoveryDest === 'dispose' ? '在库数量,在用数量' : '在用数量'
  }
  return undefined
})
/** 回收库来源剔除消耗品（领出即耗用品目不得走回收库，与提交校验口径一致） */
const excludeConsumable = computed(() => itemStockColumn.value === '回收库数量')

/** 回收台账行缓存（品目编号 → {stock, inUse}）：点选逐条拉取，切分公司整体失效重拉 */
const stockRowMap = ref(new Map<string, { stock: number; inUse: number }>())

async function loadStockRow(code: string) {
  if (!props.branchName || stockRowMap.value.has(code)) return
  stockRowMap.value.set(code, { stock: -1, inUse: -1 }) // -1 = 拉取中
  try {
    const { data } = await getAssetStocks({ branch: props.branchName, asset_code: code, pageSize: 1 })
    const row = data.results[0]
    stockRowMap.value.set(code, {
      stock: row?.在库数量 ?? 0,
      inUse: row?.在用数量 ?? 0,
    })
  } catch {
    stockRowMap.value.delete(code)
  }
}

watch(
  () => props.branchName,
  () => {
    stockRowMap.value = new Map()
    if (props.type === 'recovery') {
      drafts.value.forEach((d) => d.item && loadStockRow(d.item.asset_code))
    }
  },
)

function stockRowOf(code: string): { stock: number; inUse: number } | null {
  const value = stockRowMap.value.get(code)
  return value && value.stock >= 0 ? value : null
}

function inUseOf(code: string): number | null {
  return stockRowOf(code)?.inUse ?? null
}

function stockOf(code: string): number | null {
  return stockRowOf(code)?.stock ?? null
}

/** 回收数量品行充足软预检（缓存未知的品目放行，终检在后端台账行锁内）：
 *  处置向合并计量超在库即拒；重新入库向出现数量品行直接拒（无重新入库概念）。 */
function recoveryQuantityIssue(): string | null {
  if (props.recoveryDest !== 'dispose') {
    const bad = drafts.value.find((d) => d.item && d.item.managementType !== 'instance')
    if (bad?.item) return `品目 ${bad.item.asset_code} 数量品物无重新入库概念（回库请走归还单；处置请改选「直接处置」）`
    return null
  }
  const merged = new Map<string, number>()
  drafts.value.forEach((d) => {
    if (d.item && d.item.managementType !== 'instance' && stockOf(d.item.asset_code) !== null) {
      merged.set(d.item.asset_code, (merged.get(d.item.asset_code) ?? 0) + Number(d.数量))
    }
  })
  for (const [code, total] of merged) {
    if (total > (stockOf(code) ?? 0)) {
      return `品目 ${code} 合计处置 ${total} 超出当前在库 ${stockOf(code)}；若有在用余量请先走归还单`
    }
  }
  return null
}

/** 校验失败时的具体提示（回收在用预检专用；基础校验失败时为空，由页面给通用提示） */
const validateMessage = ref('')

/** 校验：每行已选品目且数量 ≥1；领用行使用人/部门必填（不分管理方式）；实例行选满实例 */
function validate(): boolean {
  validateMessage.value = ''
  const ok = drafts.value.every((d) => {
    if (d.item === null || Number(d.数量) < 1) return false
    if (props.type === 'assign' && (!d.使用人.trim() || !d.department)) return false
    if (isInstanceRow(d) && d.instances.length !== Number(d.数量)) return false
    return true
  })
  if (!ok) return false
  if (props.type === 'recovery') {
    const issue = recoveryQuantityIssue()
    if (issue) {
      validateMessage.value = issue
      return false
    }
  }
  return true
}

defineExpose({ validate, validateMessage })
</script>

<template>
  <div class="lines-editor">
    <div class="section-header">
      <h3 class="section-title">明细行</h3>
      <button class="add-row-btn" type="button" @click="addRow">+ 添加行</button>
    </div>
    <div class="lines-table">
      <div class="lines-header" :data-type="type">
        <span>品目 <span class="req">*</span></span>
        <span>数量 <span class="req">*</span></span>
        <span v-if="type === 'purchase' || type === 'transfer' || type === 'recovery'">本批规格</span>
        <span v-if="type === 'purchase'">供应商</span>
        <span v-if="type === 'purchase'">单价</span>
        <span v-if="type === 'purchase'">金额</span>
        <span v-if="type === 'assign'">使用人 <span class="req">*</span></span>
        <span v-if="type === 'assign'">领用部门 <span class="req">*</span></span>
        <span v-if="type === 'recovery'">存放位置</span>
        <span v-if="hasInstanceColumn">实例（实例管理品目必选）</span>
        <span></span>
      </div>
      <div v-for="(draft, index) in drafts" :key="draft.key" class="lines-row" :data-type="type">
        <div class="cell item-cell">
          <ItemPicker
            :model-value="draft.item?.id ?? ''"
            :branch="branchName"
            :stock-column="itemStockColumn"
            :exclude-consumable="excludeConsumable"
            @change="(item) => onItemPicked(index, item)"
          />
          <div v-if="draft.item" class="picked-meta">{{ draft.item.asset_name }}{{ draft.item.specification ? ` · ${draft.item.specification}` : '' }}{{ draft.item.unit ? ` · ${draft.item.unit}` : '' }}</div>
          <div v-if="draft.item?.managementType === 'consumable'" class="picked-meta consumable-meta">
            消耗品{{ type === 'assign' ? '：领出即耗用（在库扣减、总量降），不进在用、不可回收' : '' }}
          </div>
        </div>
        <div class="cell">
          <input
            v-model.number="draft.数量"
            type="number"
            class="row-input qty"
            min="1"
            :disabled="isInstanceRow(draft)"
            title="实例行数量随勾选台数联动"
            @change="onQtyChange(index)"
          />
          <div
            v-if="type === 'recovery' && recoveryDest === 'dispose' && draft.item
              && draft.item.managementType !== 'instance'
              && stockOf(draft.item.asset_code) !== null"
            class="in-use"
            :class="{ 'in-use-short': Number(draft.数量) > (stockOf(draft.item.asset_code) ?? 0) }"
          >在库 {{ stockOf(draft.item.asset_code) }}</div>
        </div>
        <div v-if="type === 'purchase' || type === 'transfer' || type === 'recovery'" class="cell"><input v-model="draft.本批规格" type="text" class="row-input" placeholder="记录性" @change="touch" /></div>
        <div v-if="type === 'purchase'" class="cell">
          <select v-model="draft.行供应商" class="row-input" @change="touch">
            <option value="">{{ suppliers.length ? '选择供应商（选填）' : '暂无供应商（管理员维护）' }}</option>
            <option v-for="sp in suppliers" :key="sp.id" :value="sp.name">{{ sp.name }}</option>
          </select>
        </div>
        <div v-if="type === 'purchase'" class="cell"><input v-model.number="draft.单价" type="number" class="row-input num" min="0" step="0.01" @change="onPriceChange(index)" /></div>
        <div v-if="type === 'purchase'" class="cell"><input v-model.number="draft.金额" type="number" class="row-input num" min="0" step="0.01" @change="onAmountChange(index)" /></div>
        <div v-if="type === 'assign'" class="cell"><input v-model="draft.使用人" type="text" class="row-input" placeholder="使用人姓名" @change="touch" /></div>
        <div v-if="type === 'assign'" class="cell">
          <select v-model="draft.department" class="row-input" @change="touch">
            <option :value="null">请选择部门</option>
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">{{ dept.name }}</option>
          </select>
        </div>
        <div v-if="type === 'recovery'" class="cell"><input v-model="draft.存放位置" type="text" class="row-input" placeholder="存放位置" @change="touch" /></div>
        <div v-if="hasInstanceColumn" class="cell instance-cell">
          <template v-if="isInstanceRow(draft) && draft.item">
            <InstancePicker
              :expanded="expandedRow === draft.key"
              :model-value="draft.instances.map((i) => i.id)"
              :item-code="draft.item.asset_code"
              :status="pickerStatus()"
              :branch-name="branchName"
              :excluded-ids="pickedInstanceIds"
              :single="type === 'assign'"
              @update:expanded="(v) => onRowExpand(draft.key, v)"
              @change="(selected) => onInstancesChange(index, selected)"
            />
            <div v-if="draft.instances.length" class="picked-meta">
              {{ draft.instances.map((i) => i.code).join('、') }}
            </div>
          </template>
          <span v-else class="instance-none">—</span>
        </div>
        <div class="cell ops"><button class="remove-btn" type="button" @click="removeRow(index)">删除</button></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.lines-editor { margin-top: var(--space-4); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2); }
.section-title { font-size: 15px; font-weight: 600; margin: 0; }
.req { color: var(--color-danger); }
.add-row-btn { padding: 6px 12px; background: var(--color-primary-50); border: 1px solid var(--color-primary-200); border-radius: 6px; color: var(--color-primary-600); font-size: 13px; cursor: pointer; }
.lines-table { border: 1px solid var(--color-border); border-radius: 8px; overflow: hidden; }
.lines-header, .lines-row { display: grid; gap: 8px; padding: 8px 12px; align-items: center; }
.lines-header { background: var(--color-bg-elevated); font-size: 13px; color: var(--color-text-secondary); }
.lines-row { border-top: 1px solid var(--color-border); }
.lines-header[data-type='purchase'] , .lines-row[data-type='purchase'] { grid-template-columns: 2fr 0.55fr 1fr 1fr 0.85fr 0.85fr 56px; }
.lines-header[data-type='assign'] , .lines-row[data-type='assign'] { grid-template-columns: 2fr 0.55fr 1fr 1.1fr 1.6fr 56px; }
.lines-header[data-type='transfer'] , .lines-row[data-type='transfer'] { grid-template-columns: 2.2fr 0.6fr 1.1fr 1.5fr 56px; }
.lines-header[data-type='recovery'] , .lines-row[data-type='recovery'] { grid-template-columns: 1.9fr 0.55fr 0.9fr 1fr 1.5fr 56px; }
.cell { min-width: 0; }
.item-cell { display: flex; flex-direction: column; gap: 4px; }
.instance-cell { display: flex; flex-direction: column; gap: 4px; }
.instance-none { color: var(--color-text-tertiary); text-align: center; }
.picked-meta { font-size: 12px; color: var(--color-text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.consumable-meta { color: var(--color-warning, #b8860b); white-space: normal; }
.row-input { width: 100%; height: 36px; padding: 0 8px; border: 1px solid var(--color-border); border-radius: 6px; font-size: 13px; background: var(--color-bg-page); outline: none; box-sizing: border-box; }
.row-input:disabled { opacity: 0.7; cursor: not-allowed; background: var(--color-bg-elevated); }
.row-input.qty, .row-input.num { text-align: center; }
.in-use { font-size: 12px; color: var(--color-text-tertiary); text-align: center; }
.in-use-short { color: var(--color-danger); }
.remove-btn { height: 36px; width: 100%; border: 1px solid var(--color-border); border-radius: 6px; background: transparent; color: var(--color-danger); font-size: 13px; cursor: pointer; }
.remove-btn:hover { border-color: var(--color-danger); }
@media (max-width: 768px) {
  .lines-header { display: none; }
  .lines-header[data-type] , .lines-row[data-type] { grid-template-columns: 1fr; }
  .lines-row { position: relative; padding-bottom: 32px; }
  .cell.ops { position: absolute; right: 12px; bottom: 8px; width: 64px; }
}
</style>
