<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { updatePassword } from '@/api/users'

const emit = defineEmits<{
  (e: 'done'): void
}>()

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const passwordLoading = ref(false)

function validateForm(): string | null {
  const { oldPassword, newPassword, confirmPassword } = passwordForm.value
  if (!oldPassword || !newPassword || !confirmPassword) {
    return '请填写所有密码字段'
  }
  if (newPassword.length < 6) {
    return '新密码长度不能少于6位'
  }
  if (newPassword !== confirmPassword) {
    return '两次输入的新密码不一致'
  }
  if (oldPassword === newPassword) {
    return '新密码不能与旧密码相同'
  }
  return null
}

async function handleSubmit() {
  const error = validateForm()
  if (error) {
    ElMessage.warning(error)
    return
  }

  passwordLoading.value = true
  try {
    await updatePassword({
      oldPassword: passwordForm.value.oldPassword,
      newPassword: passwordForm.value.newPassword
    })
    ElMessage.success('密码修改成功')
    emit('done')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '密码修改失败')
  } finally {
    passwordLoading.value = false
  }
}
</script>

<template>
  <div class="password-form">
    <div class="form-item">
      <label>旧密码</label>
      <input v-model="passwordForm.oldPassword" type="password" placeholder="请输入旧密码" autocomplete="current-password" />
    </div>
    <div class="form-item">
      <label>新密码</label>
      <input v-model="passwordForm.newPassword" type="password" placeholder="请输入新密码（至少6位）" autocomplete="new-password" />
    </div>
    <div class="form-item">
      <label>确认密码</label>
      <input v-model="passwordForm.confirmPassword" type="password" placeholder="请再次输入新密码" autocomplete="new-password" />
    </div>
    <button class="btn-save" :disabled="passwordLoading" @click="handleSubmit">
      {{ passwordLoading ? '提交中...' : '确认修改' }}
    </button>
  </div>
</template>

<script lang="ts">
export default { name: 'PasswordChangeModal' }
</script>

<style scoped>
.password-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-item label {
  font-size: var(--text-sm);
  color: rgba(0, 0, 0, 0.65);
  font-weight: 500;
}

.form-item input {
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: var(--text-sm);
  background: var(--color-bg-elevated);
  color: rgba(0, 0, 0, 0.85);
  outline: none;
  transition: border-color var(--transition-fast);
}

.form-item input:focus {
  border-color: var(--color-primary-500);
}

.form-item input::placeholder {
  color: rgba(0, 0, 0, 0.35);
}

.btn-save {
  width: 100%;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: var(--color-primary-500);
  color: white;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
  margin-top: var(--space-3);
}

.btn-save:hover:not(:disabled) {
  background: var(--color-primary-600);
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
