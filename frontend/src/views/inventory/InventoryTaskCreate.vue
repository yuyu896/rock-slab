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
        <label class="form-label">分公司</label>
        <select v-model="form.branchId" class="form-input">
          <option value="">请选择分公司</option>
          <option v-for="opt in branchOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">资产类目</label>
        <select v-model="form.categoryId" class="form-input">
          <option value="">请选择类目</option>
          <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">漏盘规则</label>
        <select v-model="form.missedRule" class="form-input">
          <option v-for="opt in missedRuleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">重复盘点规则</label>
        <select v-model="form.repeatRule" class="form-input">
          <option v-for="opt in repeatRuleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createInventoryTask } from '@/api/inventories'
import { getBranches } from '@/api/branches'
import { getCategories } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { MISSED_RULE_LABELS, REPEAT_RULE_LABELS } from '@/constants'
import { ElMessage } from 'element-plus'
import type { MissedRuleType, RepeatRuleType } from '@/types'

const router = useRouter()
const creating = ref(false)

const form = reactive({
  name: '',
  branchId: '',
  categoryId: '',
  missedRule: 'keep' as MissedRuleType,
  repeatRule: 'last' as RepeatRuleType,
})

const branchOptions = ref<{ value: string; label: string }[]>([])
const categoryOptions = ref<{ value: string; label: string }[]>([])
const missedRuleOptions = Object.entries(MISSED_RULE_LABELS).map(([value, label]) => ({ value, label }))
const repeatRuleOptions = Object.entries(REPEAT_RULE_LABELS).map(([value, label]) => ({ value, label }))

function goBack() {
  router.replace('/inventory')
}

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  creating.value = true
  try {
    await createInventoryTask({
      name: form.name,
      branch: form.branchId || undefined,
      category: form.categoryId || undefined,
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
.create-page { max-width: 640px; margin: 0 auto; padding: var(--space-6); }
.page-header { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-5); }
.back-btn { display: flex; align-items: center; gap: 4px; background: none; border: none; color: var(--color-text-secondary); cursor: pointer; font-size: var(--text-sm); }
.back-btn svg { width: 18px; height: 18px; }
.page-header h1 { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); margin: 0; }
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-6); display: flex; flex-direction: column; gap: var(--space-4); }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: var(--text-sm); font-weight: 500; }
.required { color: var(--color-danger); }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-bg-elevated); outline: none; box-sizing: border-box; }
.form-input:focus { border-color: var(--color-primary-400); }
.page-footer { display: flex; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-5); }
.btn-secondary { padding: var(--space-2) var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg-elevated); cursor: pointer; font-size: var(--text-sm); color: var(--color-text-primary); }
.btn-primary { padding: var(--space-2) var(--space-5); border: none; border-radius: var(--radius-md); background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: var(--text-sm); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
