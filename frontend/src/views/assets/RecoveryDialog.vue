<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { recoverAsset } from '@/api/transfers'
import { lookupCategoryByCode } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { Asset, FixedAsset } from '@/types'

const props = defineProps<{
  visible: boolean
  /** asset=资产明细行；fixed=固定资产实例行 */
  mode: 'asset' | 'fixed'
  item: Asset | FixedAsset | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'success'): void
}>()

const RECOVERY_CATEGORIES = ['闲置回收', '报废回收', '捐赠回收', '其他']

const submitting = ref(false)
const form = ref({
  调拨数量: 1,
  回收分类: '',
  出库日期: new Date().toISOString().slice(0, 10),
  存放位置: '',
  备注: '',
})

const isFixed = computed(() => props.mode === 'fixed')
const maxQty = computed(() => {
  if (isFixed.value) return 1
  return (props.item as Asset | null)?.数量 ?? 1
})

watch(
  () => props.visible,
  (val) => {
    if (val) {
      form.value = {
        调拨数量: 1,
        回收分类: '',
        出库日期: new Date().toISOString().slice(0, 10),
        存放位置: '',
        备注: '',
      }
    }
  },
)

async function handleSubmit() {
  const item = props.item
  if (!item) return
  if (!form.value.回收分类) {
    ElMessage.warning('请选择回收分类')
    return
  }
  if (!isFixed.value && (form.value.调拨数量 < 1 || form.value.调拨数量 > maxQty.value)) {
    ElMessage.warning(`回收数量需在 1 ~ ${maxQty.value} 之间`)
    return
  }

  submitting.value = true
  try {
    // 编号 → 字典品目 uuid；行内即时回收为单明细行单据
    const { data: category } = await lookupCategoryByCode(item.资产编号)
    await recoverAsset({
      调拨日期: new Date().toISOString().slice(0, 10),
      调出分公司: item.分公司 || '',
      调出部门: item.所属部门 || '',
      回收分类: form.value.回收分类,
      出库日期: form.value.出库日期 || undefined,
      备注: form.value.备注,
      items: [{
        item: category.id,
        数量: isFixed.value ? 1 : form.value.调拨数量,
        存放位置: form.value.存放位置 || undefined,
        固定资产内部编号: isFixed.value ? (item as FixedAsset).内部编号 || '' : undefined,
      }],
      immediate: true,
    })
    ElMessage.success(isFixed.value ? '已回收，该固定资产记录已移除' : '已回收')
    emit('success')
    emit('close')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="visible && item" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>{{ isFixed ? '回收固定资产' : '回收资产' }}</h3>
        <button class="modal-close" @click="emit('close')">&times;</button>
      </div>
      <div class="modal-body">
        <div class="prefill-grid">
          <div class="prefill-item" v-if="isFixed"><span class="prefill-label">内部编号</span><span class="asset-code">{{ (item as FixedAsset).内部编号 }}</span></div>
          <div class="prefill-item"><span class="prefill-label">资产编号</span><span class="asset-code">{{ item.资产编号 }}</span></div>
          <div class="prefill-item"><span class="prefill-label">资产名称</span><span>{{ item.资产名称 || '-' }}</span></div>
          <div class="prefill-item"><span class="prefill-label">分公司</span><span>{{ item.分公司 || '-' }}</span></div>
          <div class="prefill-item"><span class="prefill-label">所属部门</span><span>{{ item.所属部门 || '-' }}</span></div>
          <div class="prefill-item" v-if="!isFixed"><span class="prefill-label">当前数量</span><span>{{ (item as Asset).数量 }}</span></div>
        </div>

        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">回收数量 <span class="required">*</span></label>
            <input
              v-if="isFixed"
              :value="1"
              type="number"
              class="form-input"
              disabled
            />
            <input
              v-else
              v-model.number="form.调拨数量"
              type="number"
              class="form-input"
              min="1"
              :max="maxQty"
            />
          </div>
          <div class="form-item">
            <label class="form-label">回收分类 <span class="required">*</span></label>
            <select v-model="form.回收分类" class="form-select">
              <option value="">请选择</option>
              <option v-for="cat in RECOVERY_CATEGORIES" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">出库日期</label>
            <input v-model="form.出库日期" type="date" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">存放位置</label>
            <input v-model="form.存放位置" type="text" class="form-input" />
          </div>
          <div class="form-item full">
            <label class="form-label">备注</label>
            <textarea v-model="form.备注" class="form-textarea" rows="2"></textarea>
          </div>
        </div>
        <p class="recover-hint">确认后立即生效：生成「已通过」回收单并同步扣减资产汇总库存{{ isFixed ? '、删除该固定资产记录' : '、扣减该明细数量' }}。</p>
      </div>
      <div class="modal-footer">
        <button class="btn-cancel" @click="emit('close')">取消</button>
        <button class="btn-confirm" :disabled="submitting" @click="handleSubmit">{{ submitting ? '提交中...' : '确认回收' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-card); border-radius: 16px; width: 90%; max-width: 560px; max-height: 85vh; overflow-y: auto; }
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
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full { grid-column: 1 / -1; }
.form-label { font-size: 14px; font-weight: 500; color: var(--color-text-primary); }
.required { color: var(--color-danger); }
.form-input, .form-select { width: 100%; height: 40px; padding: 0 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg-page); outline: none; box-sizing: border-box; color: var(--color-text-primary); }
.form-input:focus, .form-select:focus { border-color: var(--color-primary-400); }
.form-input:disabled { opacity: 0.6; cursor: not-allowed; }
.form-textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg-page); outline: none; resize: vertical; box-sizing: border-box; }
.recover-hint { margin: var(--space-3) 0 0; font-size: var(--text-xs); color: var(--color-text-tertiary); }
.btn-cancel { height: 40px; padding: 0 20px; background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 8px; font-size: var(--text-sm); color: var(--color-text-primary); cursor: pointer; }
.btn-confirm { height: 40px; padding: 0 20px; border: none; background: var(--color-danger); color: #fff; border-radius: 8px; font-size: var(--text-sm); cursor: pointer; }
.btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
