<template>
  <div class="create-page">
    <header class="page-header">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回
      </button>
      <h1>{{ isEdit ? '编辑分类' : '新增分类' }}</h1>
    </header>

    <section class="card">
      <div class="form-grid">
        <div class="form-item">
          <label class="form-label">资产类目 <span class="required">*</span></label>
          <select v-model="form.资产类目" class="form-input">
            <option value="">请选择</option>
            <option value="固定资产类">固定资产类</option>
            <option value="低值易耗品">低值易耗品</option>
            <option value="无形资产类">无形资产类</option>
            <option value="文档资料类">文档资料类</option>
            <option value="特殊设备类">特殊设备类</option>
            <option value="其他资产">其他资产</option>
          </select>
        </div>
        <div class="form-item">
          <label class="form-label">物品分类 <span class="required">*</span></label>
          <input v-model="form.物品分类" type="text" class="form-input" placeholder="请输入物品分类" />
        </div>
        <div class="form-item">
          <label class="form-label">资产名称 <span class="required">*</span></label>
          <input v-model="form.资产名称" type="text" class="form-input" placeholder="请输入资产名称" />
        </div>
        <div class="form-item">
          <label class="form-label">资产编号 <span class="required">*</span></label>
          <input v-model="form.资产编号" type="text" class="form-input" placeholder="如：A-a00001" />
        </div>
        <div class="form-item">
          <label class="form-label">计量单位 <span class="required">*</span></label>
          <input v-model="form.计量单位" type="text" class="form-input" placeholder="如：台、个、张" />
        </div>
        <div class="form-item">
          <label class="form-label">警戒线</label>
          <input v-model.number="form.警戒线" type="number" class="form-input" placeholder="库存警戒数量" />
        </div>
        <div class="form-item full">
          <label class="form-label">备注</label>
          <textarea v-model="form.备注" class="form-textarea" placeholder="备注信息" rows="3" />
        </div>
      </div>
    </section>

    <footer class="page-footer">
      <button class="btn-secondary" @click="goBack">取消</button>
      <button class="btn-primary" :disabled="saving" @click="save">
        {{ saving ? '保存中...' : '确定保存' }}
      </button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getCategory, createCategory, updateCategory } from '@/api/categories'
import { handleApiError } from '@/utils/request'
import { ElMessage } from 'element-plus'
import type { CategoryRequest } from '@/types'

const router = useRouter()
const route = useRoute()
const id = computed(() => (route.params.id as string) || '')
const isEdit = computed(() => !!id.value)
const saving = ref(false)

const form = reactive({
  资产类目: '',
  物品分类: '',
  资产名称: '',
  资产编号: '',
  计量单位: '',
  警戒线: 10 as number | null,
  备注: '',
})

async function loadCategory() {
  if (!id.value) return
  try {
    const { data } = await getCategory(id.value)
    form.资产类目 = data.资产类目 ?? ''
    form.物品分类 = data.物品分类 ?? ''
    form.资产名称 = data.资产名称 ?? ''
    form.资产编号 = data.资产编号 ?? ''
    form.计量单位 = data.计量单位 ?? ''
    form.警戒线 = data.警戒线 ?? null
    form.备注 = data.备注 ?? ''
  } catch (error) {
    ElMessage.error(handleApiError(error))
  }
}

function goBack() {
  router.replace('/categories')
}

async function save() {
  saving.value = true
  try {
    const payload: CategoryRequest = {
      asset_category: form.资产类目,
      item_category: form.物品分类,
      asset_name: form.资产名称,
      asset_code: form.资产编号,
      unit: form.计量单位,
      warning_line: form.警戒线,
      remarks: form.备注,
    }
    if (isEdit.value) {
      await updateCategory(id.value, payload)
      ElMessage.success('保存成功')
    } else {
      await createCategory(payload)
      ElMessage.success('创建成功')
    }
    router.replace('/categories')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

onMounted(loadCategory)
</script>

<style scoped>
.create-page { max-width: 800px; margin: 0 auto; padding: var(--space-6); }
.page-header { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-5); }
.back-btn { display: flex; align-items: center; gap: 4px; background: none; border: none; color: var(--color-text-secondary); cursor: pointer; font-size: var(--text-sm); }
.back-btn svg { width: 18px; height: 18px; }
.page-header h1 { font-size: var(--text-2xl); font-weight: 700; color: var(--color-text-primary); margin: 0; }
.card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-6); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full { grid-column: 1 / -1; }
.form-label { font-size: var(--text-sm); font-weight: 500; }
.required { color: var(--color-danger); }
.form-input, .form-textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-bg-elevated); outline: none; resize: vertical; box-sizing: border-box; }
.form-input:focus, .form-textarea:focus { border-color: var(--color-primary-400); }
.page-footer { display: flex; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-5); }
.btn-secondary { padding: var(--space-2) var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg-elevated); cursor: pointer; font-size: var(--text-sm); color: var(--color-text-primary); }
.btn-primary { padding: var(--space-2) var(--space-5); border: none; border-radius: var(--radius-md); background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: var(--text-sm); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
