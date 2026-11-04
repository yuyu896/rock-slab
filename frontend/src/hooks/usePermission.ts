/* 磐盘 - usePermission 组合式函数 */
import { computed } from 'vue'
import { useUserStore } from '@/store/user'
import { ROLE_LEVELS } from '@/constants'
import type { UserRoleType } from '@/types'

export function usePermission() {
  const userStore = useUserStore()

  const currentRole = computed<UserRoleType | null>(() => userStore.profile?.role ?? null)

  const roleLevel = computed<number>(() => {
    if (!currentRole.value) return 99
    return ROLE_LEVELS[currentRole.value]
  })

  const isAdmin = computed(() => currentRole.value === 'admin')
  const isManager = computed(() => currentRole.value === 'manager')
  const isSupervisor = computed(() => currentRole.value === 'supervisor')
  const isLeader = computed(() => currentRole.value === 'leader')
  const isStaff = computed(() => currentRole.value === 'staff')

  /** 可审批：持有任一单据或盘点审批授权。 */
  const canApprove = computed(() => [
    'approve_purchase',
    'approve_assignment',
    'approve_internal_transfer',
    'approve_recovery',
    'review_inventory',
  ].some(code => userStore.can(code)))

  /** 可执行任一员工账号维护操作。 */
  const canManageUsers = computed(() => [
    'edit_users',
  ].some(code => userStore.can(code)))

  /** 可创建目录中的任一业务单据。 */
  const canCreateDocument = computed(() => [
    'edit_categories',
    'edit_purchase',
    'edit_assignment',
    'edit_transfer',
    'edit_recovery',
    'edit_inventory',
  ].some(code => userStore.can(code)))

  /** 可执行任一品目维护操作。具体按钮仍应检查对应操作码。 */
  const canManageCategories = computed(() => [
    'edit_categories',
  ].some(code => userStore.can(code)))

  /** 可执行任一资产台账或实例维护操作。 */
  const canManageAssets = computed(() => [
    'import_asset_ledger', 'adjust_asset_ledger', 'edit_instances',
    'change_instance_assignee', 'print_instance_label',
  ].some(code => userStore.can(code)))

  /** 可执行任一组织架构维护操作。 */
  const canManageOrganizations = computed(() => [
    'edit_organizations', 'delete_organizations',
  ].some(code => userStore.can(code)))

  /** 通用：是否持有任意业务操作授权 */
  function can(code: string): boolean {
    return userStore.can(code)
  }

  /** 检查是否达到指定角色级别 */
  function hasMinRole(role: UserRoleType): boolean {
    return userStore.hasMinRole(role)
  }

  return {
    currentRole,
    roleLevel,
    isAdmin,
    isManager,
    isSupervisor,
    isLeader,
    isStaff,
    canApprove,
    canManageUsers,
    canCreateDocument,
    canManageCategories,
    canManageAssets,
    canManageOrganizations,
    can,
    hasMinRole,
  }
}
