<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { Asset } from '@/types'

const props = defineProps<{
  visible: boolean
  asset: Asset | null
  branchOptions: { value: string; label: string }[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'update', payload: Partial<Asset>): void
}>()

const form = ref<Partial<Asset>>({})
const saving = ref(false)

watch(() => props.asset, (val) => {
  if (val) {
    form.value = { ...val }
  }
}, { immediate: true })

function handleSubmit() {
  const a = form.value
  if (!a.资产名称) {
    ElMessage.warning('资产名称不能为空')
    return
  }
  saving.value = true
  emit('update', {
    资产名称: a.资产名称,
    资产类目: a.资产类目,
    物品分类: a.物品分类,
    规格: a.规格,
    数量: a.数量,
    单价: a.单价,
    供应商: a.供应商,
    是否租用: a.是否租用,
    所属部门: a.所属部门,
    使用人: a.使用人,
    备注: a.备注,
    警戒线: a.警戒线,
    当前状态: a.当前状态,
    branch: a.branch,
  })
  saving.value = false
}
</script>

<template>
  <div v-if="visible" class="drawer-overlay" @click.self="emit('close')">
    <div class="drawer-panel">
      <div class="drawer-header">
        <h3>编辑资产</h3>
        <button class="drawer-close" @click="emit('close')">&times;</button>
      </div>
      <div v-if="asset" class="drawer-body">
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">资产编号</label>
            <input :value="asset.资产编号" type="text" class="form-input" disabled />
          </div>
          <div class="form-item">
            <label class="form-label">分公司</label>
            <input :value="asset.分公司" type="text" class="form-input" disabled />
          </div>
          <div class="form-item">
            <label class="form-label">资产名称 <span class="required">*</span></label>
            <input v-model="form.资产名称" type="text" class="form-input" />
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
            <label class="form-label">规格</label>
            <input v-model="form.规格" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">数量</label>
            <input v-model.number="form.数量" type="number" class="form-input" min="1" />
          </div>
          <div class="form-item">
            <label class="form-label">单价</label>
            <input v-model.number="form.单价" type="number" class="form-input" min="0" step="0.01" />
          </div>
          <div class="form-item">
            <label class="form-label">供应商</label>
            <input v-model="form.供应商" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">所属部门</label>
            <input v-model="form.所属部门" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">使用人</label>
            <input v-model="form.使用人" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">警戒线</label>
            <input v-model.number="form.警戒线" type="number" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">当前状态</label>
            <select v-model="form.当前状态" class="form-select">
              <option value="在库">在库</option>
              <option value="使用中">使用中</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">采购方式</label>
            <div class="form-toggle">
              <label><input type="radio" :value="false" v-model="form.是否租用" /> 自购</label>
              <label><input type="radio" :value="true" v-model="form.是否租用" /> 租用</label>
            </div>
          </div>
          <div class="form-item full">
            <label class="form-label">备注</label>
            <textarea v-model="form.备注" class="form-textarea" rows="3"></textarea>
          </div>
        </div>
      </div>
      <div class="drawer-footer">
        <button class="btn-cancel" @click="emit('close')">取消</button>
        <button class="btn-confirm" @click="handleSubmit" :disabled="saving">{{ saving ? '保存中...' : '保存修改' }}</button>
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
.form-label { font-size: 14px; font-weight: 500; }
.required { color: var(--color-danger); }
.form-input, .form-select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg); outline: none; }
.form-input:focus, .form-select:focus { border-color: var(--color-primary); }
.form-input:disabled { opacity: 0.6; cursor: not-allowed; }
.form-textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg); outline: none; resize: vertical; }
.form-toggle { display: flex; gap: 16px; padding: 8px 0; }
.form-toggle label { display: flex; align-items: center; gap: 4px; font-size: 14px; cursor: pointer; }
.btn-cancel { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 14px; }
.btn-confirm { padding: 8px 20px; border-radius: 8px; border: none; background: var(--color-primary); color: #fff; cursor: pointer; font-size: 14px; }
.btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
