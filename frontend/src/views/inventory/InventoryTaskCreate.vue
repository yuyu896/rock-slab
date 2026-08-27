<template>
  <div class="create-page">
    <header class="page-header">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回
      </button>
      <h1>创建盘点任务</h1>
    </header>

    <section class="card">
      <div class="form-group">
        <label class="form-label">任务名称 <span class="required">*</span></label>
        <input v-model="form.name" type="text" class="form-input" placeholder="请输入任务名称" />
      </div>
      <div class="form-group">
        <label class="form-label">分公司 <span class="required">*</span></label>
        <select v-model="form.branchId" class="form-input" @change="onBranchChange">
          <option value="">请选择分公司</option>
          <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div class="form-group full">
        <label class="form-label">盘点方式 <span class="required">*</span></label>
        <div class="kind-row">
          <label class="kind-item" :class="{ active: form.kind === 'stock' }">
            <input type="radio" value="stock" v-model="form.kind" />
            <span>台账盘点（按数量核对库存）</span>
          </label>
          <label class="kind-item" :class="{ active: form.kind === 'instance' }">
            <input type="radio" value="instance" v-model="form.kind" />
            <span>部门实例盘点（按人逐台核对在用资产）</span>
          </label>
        </div>
      </div>
      <div v-if="form.kind === 'stock'" class="form-group">
        <label class="form-label">库别</label>
        <select v-model="form.stockBin" class="form-input">
          <option v-for="opt in stockBinOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div v-if="form.kind === 'instance'" class="form-group">
        <label class="form-label">盘点部门 <span class="required">*</span></label>
        <select v-model="form.departmentId" class="form-input">
          <option value="">请选择部门（需先选分公司）</option>
          <option v-for="d in departmentOptions" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">资产类目</label>
        <select v-model="form.categoryId" class="form-input">
          <option value="">请选择类目</option>
          <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div v-if="form.kind === 'stock'" class="form-group">
        <label class="form-label">漏盘规则</label>
        <select v-model="form.missedRule" class="form-input">
          <option v-for="opt in missedRuleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div v-if="form.kind === 'stock'" class="form-group">
        <label class="form-label">重复盘点规则</label>
        <select v-model="form.repeatRule" class="form-input">
          <option v-for="opt in repeatRuleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <p class="field-hint">{{ repeatRuleHint }}</p>
      </div>
      <div v-if="form.kind === 'stock'" class="form-group">
        <label class="form-label">漏盘规则说明</label>
        <p class="field-hint">清零处理：未盘品目按实盘 0 记盘亏；保持不变：未盘项不计差异。</p>
      </div>
      <div v-if="form.kind === 'instance'" class="form-group full">
        <label class="form-label">实例盘说明</label>
        <p class="field-hint instance-hint">
          清单为该部门名下「在用」实例（仅实例管理品目，一台一行），逐台核对（点选/扫码）；
          未核对项按漏盘规则处理（{{ form.missedRule === 'zero' ? '清零处理：未核对记缺失' : '保持不变：未核对单列' }}）。
          实例盘差异<b>不自动改账</b>：盘亏实例报告标记待跟进，人工决定后续（重新查找 / 发起回收处置单）。
        </p>
      </div>
      <div v-if="form.kind === 'instance'" class="form-group">
        <label class="form-label">漏盘规则</label>
        <select v-model="form.missedRule" class="form-input">
          <option v-for="opt in missedRuleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
    </section>

    <footer class="page-footer">
      <button class="btn-secondary" @click="goBack">取消</button>
      <button class="btn-primary" :disabled="creating" @click="submit">
        {{ creating ? '创建中...' : '创建任务' }}
      </button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createInventoryTask } from '@/api/inventories'
import { getBranches } from '@/api/branches'
import { getCategories } from '@/api/categories'
import { getDepartmentOptions, type Department } from '@/api/departments'
import { handleApiError } from '@/utils/request'
import {
  MISSED_RULE_LABELS, REPEAT_RULE_LABELS, REPEAT_RULE_HINTS, STOCK_BIN_OPTIONS,
} from '@/constants'
import { ElMessage } from 'element-plus'
import type { MissedRuleType, RepeatRuleType, StockBinType } from '@/types'

const router = useRouter()
const creating = ref(false)

const form = reactive({
  name: '',
  branchId: '',
  categoryId: '',
  kind: 'stock' as 'stock' | 'instance',
  stockBin: 'stock' as StockBinType,
  departmentId: '',
  missedRule: 'keep' as MissedRuleType,
  repeatRule: 'last' as RepeatRuleType,
})

const branchOptions = ref<{ value: string; label: string }[]>([])
const categoryOptions = ref<{ value: string; label: string }[]>([])
const departmentOptions = ref<Department[]>([])
const stockBinOptions = STOCK_BIN_OPTIONS
const missedRuleOptions = Object.entries(MISSED_RULE_LABELS).map(([value, label]) => ({ value, label }))
const repeatRuleOptions = Object.entries(REPEAT_RULE_LABELS).map(([value, label]) => ({ value, label }))

const repeatRuleHint = computed(() =>
  `场景：${REPEAT_RULE_HINTS[form.repeatRule]}`)

function goBack() {
  router.replace('/inventory')
}

async function fetchDepartments(branchId: string) {
  if (!branchId) {
    departmentOptions.value = []
    return
  }
  try {
    const { data } = await getDepartmentOptions({ branch_id: branchId })
    departmentOptions.value = Array.isArray(data) ? data : (data as any).results ?? []
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

function onBranchChange() {
  form.departmentId = ''
  void fetchDepartments(form.branchId)
}

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  if (!form.branchId) {
    ElMessage.warning('请选择分公司')
    return
  }
  if (form.kind === 'instance' && !form.departmentId) {
    ElMessage.warning('部门实例盘点需选择盘点部门')
    return
  }
  creating.value = true
  try {
    await createInventoryTask({
      name: form.name,
      branch: form.branchId,
      category: form.categoryId || undefined,
      stock_bin: form.kind === 'stock' ? form.stockBin : undefined,
      department: form.kind === 'instance' ? form.departmentId : undefined,
      missed_rule: form.missedRule,
      repeat_rule: form.repeatRule,
    } as any)
    ElMessage.success('盘点任务创建成功')
    router.replace('/inventory')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  try {
    const [br, ca] = await Promise.all([getBranches(), getCategories({ pageSize: 500 })])
    branchOptions.value = br.data.map((b: any) => ({ value: b.id, label: b.name }))
    const categories = (ca.data as any).results ?? ca.data
    categoryOptions.value = categories.map((c: any) => ({ value: c.id, label: c.资产名称 }))
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
})
</script>

<style scoped>
.create-page { min-width: 0; }
.page-header { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-5); }
.back-btn { display: flex; align-items: center; gap: 4px; background: none; border: none; color: var(--color-text-secondary); cursor: pointer; font-size: var(--text-sm); }
.back-btn svg { width: 18px; height: 18px; }
.page-header h1 { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); margin: 0; }
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-6); display: grid; grid-template-columns: repeat(2, minmax(0, 640px)); gap: var(--space-4); }
.card .form-group.full { grid-column: 1 / -1; }
.card .form-group:first-child { grid-column: 1 / -1; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: var(--text-sm); font-weight: 500; }
.required { color: var(--color-danger); }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-bg-elevated); outline: none; box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary-400); }
.kind-row { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.kind-item { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-md); cursor: pointer; font-size: var(--text-sm); }
.kind-item.active { border-color: var(--color-primary-400); background: var(--color-primary-50); }
.field-hint { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; }
.instance-hint { padding: var(--space-2) var(--space-3); background: var(--color-bg-page); border: 1px dashed var(--color-border); border-radius: var(--radius-md); }
.page-footer { display: flex; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-5); }
.btn-secondary { padding: var(--space-2) var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg-elevated); cursor: pointer; font-size: var(--text-sm); color: var(--color-text-primary); }
.btn-primary { padding: var(--space-2) var(--space-5); border: none; border-radius: var(--radius-md); background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: var(--text-sm); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
@media (max-width: 768px) { .card { grid-template-columns: 1fr; } .card .form-group.full, .card .form-group:first-child { grid-column: auto; } }
</style>
