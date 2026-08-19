<script setup lang="ts">
import { ref, watch } from 'vue'
import { createAsset, createFixedAsset } from '@/api/assets'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import DepartmentSelect from '@/components/DepartmentSelect.vue'
import type { AssetStock } from '@/types'

const props = defineProps<{
  visible: boolean
  stock: AssetStock | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

type FillTarget = 'detail' | 'fixed'

const target = ref<FillTarget>('detail')
const submitting = ref(false)

const form = ref({
  所属部门: '',
  使用人: '',
  数量: 1,
  入库日期: new Date().toISOString().slice(0, 10),
  序列号: '',
  备注: '',
})

watch(
  () => props.visible,
  (val) => {
    if (val) {
      target.value = 'detail'
      form.value = {
        所属部门: '',
        使用人: '',
        数量: 1,
        入库日期: new Date().toISOString().slice(0, 10),
        序列号: '',
        备注: '',
      }
    }
  },
)

async function handleSubmit() {
  const s = props.stock
  if (!s) return
  const f = form.value
  if (target.value === 'detail') {
    if (!f.所属部门) {
      ElMessage.warning('请填写所属部门')
      return
    }
    if (!f.数量 || f.数量 < 1) {
      ElMessage.warning('数量至少为 1')
      return
    }
  } else {
    if (!f.序列号) {
      ElMessage.warning('请填写电脑序列号')
      return
    }
  }

  submitting.value = true
  try {
    if (target.value === 'detail') {
      await createAsset({
        分公司: s.分公司,
        branch: s.branch,
        资产编号: s.资产编号,
        资产类目: s.资产类目 || '',
        物品分类: s.物品分类 || '',
        资产名称: s.资产名称 || s.资产编号,
        规格: s.规格 || '',
        警戒线: s.警戒线 ?? undefined,
        数量: f.数量,
        所属部门: f.所属部门,
        使用人: f.使用人,
        入库日期: f.入库日期,
        当前状态: '在库',
        是否租用: false,
        备注: f.备注,
      })
      ElMessage.success(`已填入资产明细（台账库存不变）`)
    } else {
      await createFixedAsset({
        分公司: s.分公司,
        branch: s.branch,
        资产编号: s.资产编号,
        资产类目: s.资产类目 || '',
        物品分类: s.物品分类 || '',
        资产名称: s.资产名称 || s.资产编号,
        规格: s.规格 || '',
        序列号: f.序列号,
        数量: f.数量,
        所属部门: f.所属部门,
        使用人: f.使用人,
        入库日期: f.入库日期,
        当前状态: '在库',
        备注: f.备注,
      })
      ElMessage.success(`已填入固定资产（台账库存不变）`)
    }
    emit('close')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="visible && stock" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>填入：{{ stock.资产名称 || stock.资产编号 }}</h3>
        <button class="modal-close" @click="emit('close')">&times;</button>
      </div>
      <div class="modal-body">
        <!-- 预填信息 -->
        <div class="prefill-grid">
          <div class="prefill-item"><span class="prefill-label">分公司</span><span>{{ stock.分公司 }}</span></div>
          <div class="prefill-item"><span class="prefill-label">资产编号</span><span class="asset-code">{{ stock.资产编号 }}</span></div>
          <div class="prefill-item"><span class="prefill-label">资产类目</span><span>{{ stock.资产类目 || '-' }}</span></div>
          <div class="prefill-item"><span class="prefill-label">物品分类</span><span>{{ stock.物品分类 || '-' }}</span></div>
          <div class="prefill-item"><span class="prefill-label">规格</span><span>{{ stock.规格 || '-' }}</span></div>
          <div class="prefill-item"><span class="prefill-label">警戒线</span><span>{{ stock.警戒线 ?? '-' }}</span></div>
        </div>

        <!-- 填入目标 -->
        <div class="target-row">
          <button class="target-btn" :class="{ active: target === 'detail' }" @click="target = 'detail'">填入资产明细</button>
          <button class="target-btn" :class="{ active: target === 'fixed' }" @click="target = 'fixed'">填入固定资产</button>
        </div>

        <div class="form-grid">
          <div v-if="target === 'fixed'" class="form-item">
            <label class="form-label">电脑序列号 <span class="required">*</span></label>
            <input v-model="form.序列号" type="text" class="form-input" placeholder="请输入序列号" />
          </div>
          <div class="form-item">
            <label class="form-label">所属部门 <span v-if="target === 'detail'" class="required">*</span></label>
            <DepartmentSelect v-if="target === 'detail'" v-model="form.所属部门" />
            <input v-else v-model="form.所属部门" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">使用人</label>
            <input v-model="form.使用人" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">数量</label>
            <input v-model.number="form.数量" type="number" class="form-input" min="1" />
          </div>
          <div class="form-item">
            <label class="form-label">入库日期</label>
            <input v-model="form.入库日期" type="date" class="form-input" />
          </div>
          <div class="form-item full">
            <label class="form-label">备注</label>
            <textarea v-model="form.备注" class="form-textarea" rows="2"></textarea>
          </div>
        </div>
        <p class="fill-hint">填入不会扣减台账库存；明细/固定资产用于说明各分公司、各部门的物品分布。</p>
      </div>
      <div class="modal-footer">
        <button class="btn-cancel" @click="emit('close')">取消</button>
        <button class="btn-confirm" :disabled="submitting" @click="handleSubmit">{{ submitting ? '提交中...' : '确定填入' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-card); border-radius: 16px; width: 90%; max-width: 640px; max-height: 85vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { margin: 0; font-size: var(--text-lg); font-weight: 600; }
.modal-close { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: transparent; border: none; font-size: 20px; color: var(--color-text-tertiary); cursor: pointer; border-radius: 6px; }
.modal-close:hover { background: var(--color-bg-elevated); }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: var(--space-3); padding: 12px 20px; border-top: 1px solid var(--color-border); }
.prefill-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2) var(--space-4); padding: var(--space-3) var(--space-4); background: var(--color-bg-page); border-radius: 10px; margin-bottom: var(--space-4); font-size: var(--text-sm); }
.prefill-item { display: flex; align-items: baseline; gap: var(--space-2); min-width: 0; }
.prefill-label { color: var(--color-text-tertiary); font-size: var(--text-xs); white-space: nowrap; }
.asset-code { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-primary-600); }
.target-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.target-btn { flex: 1; height: 40px; border-radius: 10px; border: 1px solid var(--color-border); background: var(--color-bg-card); font-size: var(--text-sm); color: var(--color-text-secondary); cursor: pointer; transition: all var(--transition-fast); }
.target-btn:hover { border-color: var(--color-primary-300); color: var(--color-primary-500); }
.target-btn.active { background: var(--color-primary-50); border-color: var(--color-primary-400); color: var(--color-primary-600); font-weight: 600; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full { grid-column: 1 / -1; }
.form-label { font-size: 14px; font-weight: 500; color: var(--color-text-primary); }
.required { color: var(--color-danger); }
.form-input { width: 100%; height: 40px; padding: 0 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg-page); outline: none; box-sizing: border-box; color: var(--color-text-primary); }
.form-input:focus { border-color: var(--color-primary-400); }
.form-textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg-page); outline: none; resize: vertical; box-sizing: border-box; }
.fill-hint { margin: var(--space-3) 0 0; font-size: var(--text-xs); color: var(--color-text-tertiary); }
.btn-cancel { height: 40px; padding: 0 20px; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.btn-confirm { height: 40px; padding: 0 20px; border: none; background: var(--color-primary-500); color: #fff; border-radius: 8px; font-size: var(--text-sm); cursor: pointer; }
.btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
