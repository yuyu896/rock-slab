<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { Asset, Category } from '@/types'

const props = defineProps<{
  visible: boolean
  saving: boolean
  branchOptions: { value: string; label: string }[]
  categoryOptions: { value: string; label: string }[]
  allCategories: Category[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', payload: Partial<Asset>): void
}>()

const newAsset = ref<Partial<Asset>>(getDefaultAsset())
const dynamicAttrValues = ref<Record<string, string>>({})

function getDefaultAsset(): Partial<Asset> {
  return {
    分公司: '',
    资产编号: '',
    资产类目: '',
    物品分类: '',
    资产名称: '',
    规格: '',
    数量: 1,
    单价: 0,
    供应商: '',
    是否租用: false,
    所属部门: '',
    使用人: '',
    备注: '',
  }
}

const currentCategoryAttrs = computed(() => {
  if (!newAsset.value.物品分类) return []
  const cat = props.allCategories.find(c => c.物品分类 === newAsset.value.物品分类)
  if (!cat || !(cat as any).attributes) return []
  return (cat as any).attributes
})

const itemCategoryOptions = computed(() => {
  if (!newAsset.value.资产类目) return []
  const seen = new Set<string>()
  return props.allCategories
    .filter(c => c.资产类目 === newAsset.value.资产类目)
    .filter(c => {
      if (seen.has(c.物品分类)) return false
      seen.add(c.物品分类)
      return true
    })
})

const createMainCategoryOptions = computed(() => {
  return props.categoryOptions.filter(o => o.value !== '')
})

function resetForm() {
  newAsset.value = getDefaultAsset()
  dynamicAttrValues.value = {}
}

function handleSubmit() {
  const a = newAsset.value
  if (!a.分公司 || !a.资产编号 || !a.资产名称 || !a.资产类目 || !a.物品分类 || !a.数量) {
    ElMessage.warning('请填写所有必填字段')
    return
  }
  const payload: Partial<Asset> = {
    ...a,
    购入金额: (a.数量 ?? 0) * (a.单价 ?? 0),
    当前状态: '在库',
    入库日期: new Date().toISOString().slice(0, 10),
  }
  if (Object.keys(dynamicAttrValues.value).length > 0) {
    const attrParts = Object.entries(dynamicAttrValues.value).map(([k, v]) => `${k}:${v}`)
    payload.备注 = (a.备注 ? a.备注 + '\n' : '') + '[属性]' + attrParts.join('; ')
  }
  emit('save', payload)
}

function handleClose() {
  resetForm()
  emit('close')
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h3>新增资产</h3>
        <button class="modal-close" @click="handleClose">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">分公司 <span class="required">*</span></label>
            <select v-model="newAsset.分公司" class="form-select">
              <option value="">请选择</option>
              <option v-for="b in branchOptions.filter(b => b.value)" :key="b.value" :value="b.value">{{ b.label }}</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">资产编号 <span class="required">*</span></label>
            <input v-model="newAsset.资产编号" type="text" class="form-input" placeholder="如：A-a00001" />
          </div>
          <div class="form-item">
            <label class="form-label">资产类目 <span class="required">*</span></label>
            <select v-model="newAsset.资产类目" class="form-select" @change="newAsset.物品分类 = ''">
              <option value="">请选择</option>
              <option v-for="opt in createMainCategoryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">物品分类 <span class="required">*</span></label>
            <select v-model="newAsset.物品分类" class="form-select">
              <option value="">请选择</option>
              <option v-for="c in itemCategoryOptions" :key="c.id" :value="c.物品分类">{{ c.物品分类 }}</option>
            </select>
          </div>
          <div class="form-item">
            <label class="form-label">资产名称 <span class="required">*</span></label>
            <input v-model="newAsset.资产名称" type="text" class="form-input" placeholder="请输入资产名称" />
          </div>
          <div class="form-item">
            <label class="form-label">规格</label>
            <input v-model="newAsset.规格" type="text" class="form-input" placeholder="规格型号" />
          </div>
          <div class="form-item">
            <label class="form-label">数量 <span class="required">*</span></label>
            <input v-model.number="newAsset.数量" type="number" class="form-input" min="1" />
          </div>
          <div class="form-item">
            <label class="form-label">单价</label>
            <input v-model.number="newAsset.单价" type="number" class="form-input" min="0" step="0.01" />
          </div>
          <div class="form-item">
            <label class="form-label">供应商</label>
            <input v-model="newAsset.供应商" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">所属部门</label>
            <input v-model="newAsset.所属部门" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">使用人</label>
            <input v-model="newAsset.使用人" type="text" class="form-input" />
          </div>
          <div class="form-item">
            <label class="form-label">采购方式</label>
            <div class="form-toggle">
              <label><input type="radio" :value="false" v-model="newAsset.是否租用" /> 自购</label>
              <label><input type="radio" :value="true" v-model="newAsset.是否租用" /> 租用</label>
            </div>
          </div>
          <template v-if="currentCategoryAttrs.length > 0">
            <div v-for="attr in currentCategoryAttrs" :key="attr.name" class="form-item">
              <label class="form-label">{{ attr.name }} <span v-if="attr.required" class="required">*</span></label>
              <input v-if="attr.type === 'text'" v-model="dynamicAttrValues[attr.name]" type="text" class="form-input" :placeholder="'请输入' + attr.name" />
              <input v-else-if="attr.type === 'number'" v-model.number="dynamicAttrValues[attr.name]" type="number" class="form-input" :placeholder="'请输入' + attr.name" />
              <select v-else-if="attr.type === 'select'" v-model="dynamicAttrValues[attr.name]" class="form-select">
                <option value="">请选择</option>
                <option v-for="opt in (attr.options || '').split(',')" :key="opt" :value="opt.trim()">{{ opt.trim() }}</option>
              </select>
            </div>
          </template>
          <div class="form-item full">
            <label class="form-label">备注</label>
            <textarea v-model="newAsset.备注" class="form-textarea" rows="3" placeholder="备注信息"></textarea>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-cancel" @click="handleClose">取消</button>
        <button class="btn-confirm" @click="handleSubmit" :disabled="saving">{{ saving ? '创建中...' : '确定创建' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal-content { background: var(--color-bg-elevated); border-radius: 16px; width: 90%; max-width: 720px; max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--color-border); }
.modal-header h3 { margin: 0; font-size: 18px; }
.modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--color-text-secondary); }
.modal-body { padding: 24px; }
.modal-footer { padding: 16px 24px; border-top: 1px solid var(--color-border); display: flex; justify-content: flex-end; gap: 12px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full { grid-column: 1 / -1; }
.form-label { font-size: 14px; font-weight: 500; }
.required { color: var(--color-danger); }
.form-input, .form-select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg); outline: none; }
.form-input:focus, .form-select:focus { border-color: var(--color-primary); }
.form-textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 8px; font-size: 14px; background: var(--color-bg); outline: none; resize: vertical; }
.form-toggle { display: flex; gap: 16px; padding: 8px 0; }
.form-toggle label { display: flex; align-items: center; gap: 4px; font-size: 14px; cursor: pointer; }
.btn-cancel { padding: 8px 20px; border-radius: 8px; border: 1px solid var(--color-border); background: var(--color-bg-elevated); cursor: pointer; font-size: 14px; }
.btn-confirm { padding: 8px 20px; border-radius: 8px; border: none; background: var(--color-primary); color: #fff; cursor: pointer; font-size: 14px; }
.btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
