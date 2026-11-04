<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getDepartments, createDepartment, updateDepartment, deleteDepartment, type Department } from '@/api/departments'
import { handleApiError } from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/hooks/usePermission'
import BasePagination from '@/components/BasePagination.vue'

const { can } = usePermission()
const canEdit = computed(() => can('view_departments') && can('edit_departments'))

const departments = ref<Department[]>([])
const pagination = ref({ page: 1, pageSize: 50, total: 0 })
const loading = ref(false)

const newName = ref('')
const saving = ref(false)
const editingId = ref('')
const editingName = ref('')

async function fetchDepartments() {
  if (!can('view_departments')) {
    departments.value = []
    pagination.value.total = 0
    return
  }
  loading.value = true
  try {
    const { data } = await getDepartments({
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
    })
    departments.value = data.results
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
    ElMessage.warning('请填写部门名称')
    return
  }
  saving.value = true
  try {
    await createDepartment({ name: newName.value.trim() })
    ElMessage.success('已添加')
    newName.value = ''
    if (can('view_departments')) await fetchDepartments()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

function startEdit(d: Department) {
  if (!canEdit.value) return
  editingId.value = d.id
  editingName.value = d.name
}

async function handleEdit(d: Department) {
  if (!canEdit.value) return
  if (!editingName.value.trim()) {
    ElMessage.warning('请填写部门名称')
    return
  }
  saving.value = true
  try {
    await updateDepartment(d.id, { name: editingName.value.trim() })
    ElMessage.success('已保存')
    editingId.value = ''
    if (can('view_departments')) await fetchDepartments()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    saving.value = false
  }
}

async function handleDelete(d: Department) {
  if (!canEdit.value) return
  try {
    await ElMessageBox.confirm(`确定删除「${d.name}」？`, '删除确认', { type: 'warning' })
    await deleteDepartment(d.id)
    ElMessage.success('已删除')
    if (can('view_departments')) await fetchDepartments()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(handleApiError(error))
    }
  }
}

function handlePaginationChange(page: number, pageSize: number) {
  pagination.value.page = page
  pagination.value.pageSize = pageSize
  fetchDepartments()
}

onMounted(fetchDepartments)
</script>

<template>
  <div class="dept-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">部门字典</h1>
        <p class="page-desc">全集团扁平归属标签，供资产/单据表单下拉归一；不是组织树节点</p>
      </div>
    </div>

    <div v-if="canEdit" class="add-row">
      <input v-model="newName" type="text" class="filter-input" placeholder="部门名称" @keyup.enter="handleCreate" />
      <button class="btn-primary" :disabled="saving" @click="handleCreate">添加</button>
    </div>

    <div v-if="can('view_departments')" class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>序号</th>
            <th>部门名称</th>
            <th v-if="canEdit">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && departments.length === 0">
            <td :colspan="canEdit ? 3 : 2" class="empty-cell">加载中...</td>
          </tr>
          <tr v-else-if="departments.length === 0">
            <td :colspan="canEdit ? 3 : 2" class="empty-cell">暂无部门</td>
          </tr>
          <tr v-for="(d, index) in departments" :key="d.id">
            <td class="col-index">{{ (pagination.page - 1) * pagination.pageSize + index + 1 }}</td>
            <td>
              <input v-if="editingId === d.id" v-model="editingName" class="filter-input" aria-label="部门名称" />
              <span v-else>{{ d.name }}</span>
            </td>
            <td v-if="canEdit">
              <template v-if="editingId === d.id">
                <button class="action-btn" :disabled="saving" @click="handleEdit(d)">保存</button>
                <button class="action-btn" :disabled="saving" @click="editingId = ''">取消</button>
              </template>
              <template v-else>
                <button class="action-btn" @click="startEdit(d)">编辑</button>
                <button class="action-btn danger" @click="handleDelete(d)">删除</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="table-container empty-cell">当前账号没有查看部门权限</div>

    <BasePagination
      v-if="can('view_departments')"
      :total="pagination.total"
      :current-page="pagination.page"
      :page-size="pagination.pageSize"
      @change="handlePaginationChange"
    />
  </div>
</template>

<style scoped>
.dept-page { max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5); flex-shrink: 0; }
.header-info { display: flex; flex-direction: column; gap: var(--space-1); }
.page-title { font-size: var(--text-xl); font-weight: 600; margin: 0; }
.page-desc { font-size: var(--text-sm); color: var(--color-text-tertiary); margin: 0; }
.add-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.filter-input { flex: 1; height: 38px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); font-size: var(--text-sm); }
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
