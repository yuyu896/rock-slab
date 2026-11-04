<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getSuppliers, createSupplier, updateSupplier, deleteSupplier, type Supplier } from '@/api/suppliers'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import BasePagination from '@/components/BasePagination.vue'

const { can } = usePermission()
const canEdit = computed(() => can('view_suppliers') && can('edit_suppliers'))

const suppliers = ref<Supplier[]>([])
const pagination = ref({ page: 1, pageSize: 50, total: 0 })
const loading = ref(false)

const newName = ref('')
const newContact = ref('')
const newPhone = ref('')
const saving = ref(false)
const editingId = ref('')
const editDraft = ref({ name: '', 联系人: '', 电话: '' })

async function fetchSuppliers() {
  if (!can('view_suppliers')) {
    suppliers.value = []
    pagination.value.total = 0
    return
  }
  loading.value = true
  try {
    const { data } = await getSuppliers({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
    })
    suppliers.value = data.results
    pagination.value.total = data.count
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!canEdit.value) return
  if (!newName.value.trim()) {
    ElMessage.warning('请填写供应商名称')
    return
  }
  saving.value = true
  try {
    await createSupplier({
      name: newName.value.trim(),
      联系人: newContact.value.trim(),
      电话: newPhone.value.trim(),
    })
    ElMessage.success('已添加')
    newName.value = ''
    newContact.value = ''
    newPhone.value = ''
    if (can('view_suppliers')) await fetchSuppliers()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

function startEdit(s: Supplier) {
  if (!canEdit.value) return
  editingId.value = s.id
  editDraft.value = { name: s.name, 联系人: s.联系人 || '', 电话: s.电话 || '' }
}

async function handleEdit(s: Supplier) {
  if (!canEdit.value) return
  if (!editDraft.value.name.trim()) {
    ElMessage.warning('请填写供应商名称')
    return
  }
  saving.value = true
  try {
    await updateSupplier(s.id, {
      name: editDraft.value.name.trim(),
      联系人: editDraft.value.联系人.trim(),
      电话: editDraft.value.电话.trim(),
    })
    ElMessage.success('已保存')
    editingId.value = ''
    if (can('view_suppliers')) await fetchSuppliers()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

async function handleDelete(s: Supplier) {
  if (!canEdit.value) return
  try {
    await ElMessageBox.confirm(`确定删除「${s.name}」？已录入单据不受影响。`, '删除确认', { type: 'warning' })
    await deleteSupplier(s.id)
    ElMessage.success('已删除')
    if (can('view_suppliers')) await fetchSuppliers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

function handlePaginationChange(page: number, pageSize: number) {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchSuppliers()
}

onMounted(fetchSuppliers)
</script>

<template>
  <div class="supplier-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">供应商字典</h1>
        <p class="page-desc">全集团扁平字典，采购建单行级供应商只准选此处条目</p>
      </div>
    </div>

    <div v-if="canEdit" class="add-row">
      <input v-model="newName" type="text" class="filter-input" placeholder="供应商名称" @keyup.enter="handleCreate" />
      <input v-model="newContact" type="text" class="filter-input narrow" placeholder="联系人（选填）" />
      <input v-model="newPhone" type="text" class="filter-input narrow" placeholder="电话（选填）" />
      <button class="btn-primary" :disabled="saving" @click="handleCreate">添加</button>
    </div>

    <div v-if="can('view_suppliers')" class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>序号</th>
            <th>供应商名称</th>
            <th>联系人</th>
            <th>电话</th>
            <th v-if="canEdit">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && suppliers.length === 0">
            <td :colspan="canEdit ? 5 : 4" class="empty-cell">加载中...</td>
          </tr>
          <tr v-else-if="suppliers.length === 0">
            <td :colspan="canEdit ? 5 : 4" class="empty-cell">暂无供应商，添加后建单即可选择</td>
          </tr>
          <tr v-for="(s, index) in suppliers" :key="s.id">
            <td class="col-index">{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
            <td>
              <input v-if="editingId === s.id" v-model="editDraft.name" class="filter-input" aria-label="供应商名称" />
              <span v-else>{{ s.name }}</span>
            </td>
            <td>
              <input v-if="editingId === s.id" v-model="editDraft.联系人" class="filter-input narrow" aria-label="供应商联系人" />
              <span v-else>{{ s.联系人 || '-' }}</span>
            </td>
            <td>
              <input v-if="editingId === s.id" v-model="editDraft.电话" class="filter-input narrow" aria-label="供应商电话" />
              <span v-else>{{ s.电话 || '-' }}</span>
            </td>
            <td v-if="canEdit">
              <template v-if="editingId === s.id">
                <button class="action-btn" :disabled="saving" @click="handleEdit(s)">保存</button>
                <button class="action-btn" :disabled="saving" @click="editingId = ''">取消</button>
              </template>
              <template v-else>
                <button class="action-btn" @click="startEdit(s)">编辑</button>
                <button class="action-btn danger" @click="handleDelete(s)">删除</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="table-container empty-cell">当前账号没有查看供应商权限</div>

    <BasePagination
      v-if="can('view_suppliers')"
      :total="pagination.total"
      :current-page="pagination.page"
      :page-size="pagination.pageSize"
      @change="handlePaginationChange"
    />
  </div>
</template>

<style scoped>
.supplier-page { max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5); flex-shrink: 0; }
.header-info { display: flex; flex-direction: column; gap: var(--space-1); }
.page-title { font-size: var(--text-xl); font-weight: 600; margin: 0; }
.page-desc { font-size: var(--text-sm); color: var(--color-text-tertiary); margin: 0; }
.add-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.filter-input { flex: 1; height: 38px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); font-size: var(--text-sm); }
.filter-input.narrow { flex: 0 0 180px; }
.btn-primary { height: 38px; padding: 0 var(--space-5); border: none; border-radius: 8px; background: var(--color-primary-500); color: #fff; cursor: pointer; font-size: var(--text-sm); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.table-container { background: var(--color-bg-card); border-radius: 12px; border: 1px solid var(--color-border); overflow: auto; flex: 1; min-height: 200px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { position: sticky; top: 0; z-index: 1; background: var(--color-bg-table-header); padding: var(--space-3) var(--space-4); text-align: left; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-secondary); border-bottom: 1px solid var(--color-border); }
.data-table td { padding: var(--space-3) var(--space-4); font-size: var(--text-sm); border-bottom: 1px solid var(--color-border-light); }
.col-index { width: 56px; text-align: center; color: var(--color-text-tertiary); }
.empty-cell { text-align: center; padding: var(--space-8) 0; color: var(--color-text-tertiary); }
.action-btn { border: none; background: none; cursor: pointer; font-size: var(--text-sm); color: var(--color-text-tertiary); }
.action-btn.danger { color: var(--color-danger); }
</style>
