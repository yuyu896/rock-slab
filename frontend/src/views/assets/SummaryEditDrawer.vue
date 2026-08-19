<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { AssetStock } from '@/types'

const props = defineProps<{
  visible: boolean
  stock: AssetStock | null
  branchOptions: { value: string; label: string }[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', payload: Partial<AssetStock>, id?: string): void
}>()

const isEdit = computed(() => !!props.stock)

function defaultForm(): Partial<AssetStock> {
  return {
    分公司: '',
    资产编号: '',
    资产类目: '',
    物品分类: '',
    资产名称: '',
    规格: '',
    数量: 1,
    警戒线: undefined,
  }
}

const form = ref<Partial<AssetStock>>(defaultForm())

watch(
  () => props.stock,
  (val) => {
    form.value = val ? { ...val } : defaultForm()
  },
  { immediate: true },
)

function handleSubmit() {
  const f = form.value
  if (!f.分公司 || !f.资产编号 || !f.资产名称) {
    ElMessage.warning('请填写分公司、资产编号、资产名称')
    return
  }
  emit('submit', {
    分公司: f.分公司,
    资产编号: f.资产编号,
    资产类目: f.资产类目 || '',
    物品分类: f.物品分类 || '',
    资产名称: f.资产名称,
    规格: f.规格 || '',
    数量: f.数量 ?? 0,
    警戒线: f.警戒线 ?? null,
  }, props.stock?.id)
}
</script>

<template>
  <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
    <div class="drawer-panel">
      <div class="drawer-header">
        <h3>{{ isEdit ? '编辑台账行' : '新增台账行' }}</h3>
        <button class="drawer-close" @click="emit('close')">&times;</button>
      </div>
      <div class="drawer-body">
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">分公司 <span class="required">*</span></label>
            <select v-model="form.分公司" class="form-select" :disabled="isEdit">
              <option value="">{{ isEdit ? '' : '请选择' }}</option>
              <option v-for="b in branchOptions.filter(b => b.value)" :key="b.value" :value="b.value">{{ b.label }}</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">资产编号 <span class="required">*</span></label>
            <input v-model="form.资产编号" type="text" class="form-input" :disabled="isEdit" placeholder="如：A-a00001" />
          </div>
          <div class="form-item">
            <label class="form-label">资产类目</label>
            <input v-model="form.资产类目" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">物品分类</label>
            <input v-model="form.物品分类" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">资产名称 <span class="required">*</span></label>
            <input v-model="form.资产名称" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">规格</label>
            <input v-model="form.规格" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">数量</label>
            <input v-model.number="form.数量" type="number" class="form-input" min="0" />
          </div>
          <div class="form-item">
            <label class="form-label">警戒线</label>
            <input v-model.number="form.警戒线" type="number" class="form-input" min="0" placeholder="留空视为充足" />
          </div>
          <div class="form-item full">
            <span class="form-hint">「是否充足」由系统按 数量 ≥ 警戒线 自动计算</span>
          </div>
        </div>
      </div>
      <div class="drawer-footer">
        <button class="btn-cancel" @click="emit('close')">取消</button>
        <button class="btn-confirm" @click="handleSubmit">{{ isEdit ? '保存修改' : '确定新增' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drawer-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; display: flex; justify-content: flex-end; }
.drawer-panel { width: 480px; max-width: 90vw; background: var(--color-bg-elevated); height: 100vh; overflow-y: auto; box-shadow: -4px 0 20px rgba(0,0,0,0.1); display: flex; flex-direction: column; }
.drawer-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); }
.drawer-header h3 { margin: 0; font-size: 18px; }
.drawer-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--color-text-secondary); }
.drawer-body { flex: 1; padding: 24px; }
.drawer-footer { padding: 16px 24px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full { grid-column: 1 / -1; }
.form-label { font-size: 14px; font-weight: 500; color: var(--color-text-primary); }
.required { color: var(--color-danger); }
.form-hint { font-size: 12px; color: var(--color-text-tertiary); }
.form-input, .form-select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg); outline: none; color: var(--color-text-primary); }
.form-input:focus, .form-select:focus { border-color: var(--color-primary); }
.form-input:disabled, .form-select:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-cancel { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 14px; }
.btn-confirm { padding: 8px 20px; border-radius: 8px; border: none; background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: 14px; }
</style>
