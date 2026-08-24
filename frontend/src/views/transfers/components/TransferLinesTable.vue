<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { TransferLine } from '@/types'
import type { TransferType } from '@/constants'

/** 单据明细表（只读）：Excel 式朴素表格，列按单据类型裁剪；实例列可跳转实例生平 */
const props = defineProps<{
  lines: TransferLine[]
  type: TransferType
}>()

const router = useRouter()

function specOf(line: TransferLine) {
  return line.本批规格 || line.itemSpec || '-'
}

/** 绑定类单据展示实例列（采购为生成制，实例在生效时自动生成也可展示） */
function hasInstances(line: TransferLine): boolean {
  return line.managementType === 'instance' && (line.instances?.length ?? 0) > 0
}

function goTimeline(code: string) {
  router.push({ path: '/fixed-assets', query: { keyword: code } })
}
</script>

<template>
  <div class="lines-table-wrap">
    <table class="lines-table">
      <thead>
        <tr>
          <th>#</th>
          <th>编号</th>
          <th>名称</th>
          <th>规格</th>
          <th>单位</th>
          <th v-if="type === 'purchase'">资产类目</th>
          <th v-if="type === 'assign'" class="col-user">使用人</th>
          <th v-if="type === 'assign'" class="col-user">领用部门</th>
          <th v-if="type === 'purchase'">单价</th>
          <th v-if="type === 'purchase'">金额</th>
          <th v-if="type === 'recovery'" class="col-loc">存放位置</th>
          <th class="col-inst">实例</th>
          <th class="col-qty">数量</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="line in lines" :key="line.id">
          <td class="mono">{{ line.行号 }}</td>
          <td><span class="code-chip">{{ line.itemCode }}</span></td>
          <td class="name">{{ line.itemName }}</td>
          <td>{{ specOf(line) }}</td>
          <td>{{ line.unit || '-' }}</td>
          <td v-if="type === 'purchase'">{{ line.assetCategory }}/{{ line.itemCategory }}</td>
          <td v-if="type === 'assign'">{{ line.使用人 || '-' }}</td>
          <td v-if="type === 'assign'">{{ line.departmentName || '-' }}</td>
          <td v-if="type === 'purchase'">{{ line.单价 ?? '-' }}</td>
          <td v-if="type === 'purchase'">{{ line.金额 ?? '-' }}</td>
          <td v-if="type === 'recovery'">{{ line.存放位置 || '-' }}</td>
          <td class="col-inst">
            <template v-if="hasInstances(line)">
              <a
                v-for="inst in line.instances"
                :key="inst.id"
                class="inst-link"
                title="查看实例生平"
                @click.prevent="goTimeline(inst.code)"
              >{{ inst.code }}</a>
            </template>
            <span v-else class="mono">-</span>
          </td>
          <td class="qty">{{ line.数量 }}</td>
        </tr>
        <tr class="total-row">
          <td :colspan="type === 'purchase' ? 10 : type === 'assign' ? 9 : 7" class="total-label">合计</td>
          <td class="qty">{{ lines.reduce((sum, line) => sum + (line.数量 || 0), 0) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.lines-table-wrap { border: 1px solid var(--color-border); border-radius: 8px; overflow: auto; }
.lines-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.lines-table th { background: var(--color-bg-elevated); padding: var(--space-2) var(--space-3); text-align: left; font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); white-space: nowrap; }
.lines-table td { padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--color-border-light); color: var(--color-text-primary); vertical-align: middle; }
.lines-table tbody tr:last-child td { border-bottom: none; }
.mono { font-family: var(--font-mono); color: var(--color-text-secondary); }
.code-chip { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-primary-600); background: var(--color-primary-50); padding: 2px 6px; border-radius: 4px; }
.name { font-weight: 500; }
.qty { font-weight: 600; text-align: right; }
th.col-qty, td.qty { text-align: right; }
.total-row td { background: var(--color-bg-elevated); font-weight: 600; }
.total-label { text-align: right; color: var(--color-text-secondary); }
.col-user, .col-loc { min-width: 90px; }
.col-inst { min-width: 110px; }
.inst-link { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--color-primary-600); cursor: pointer; margin-right: 6px; }
.inst-link:hover { text-decoration: underline; }
</style>
