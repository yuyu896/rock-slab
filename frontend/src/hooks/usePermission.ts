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

  /** 可审批：持有审批类操作授权（admin 恒真） */
  const canApprove = computed(() =>
    userStore.can('approve_transfer') || userStore.can('approve_inventory'),
  )

  /** 可管理用户：持有 manage_users 授权 */
  const canManageUsers = computed(() => userStore.can('manage_users'))

  /** 可提交单据：所有登录用户（写操作受各 manage_* 授权控制） */
  const canCreateDocument = computed(() => !!userStore.profile)

  /** 可管理类目：持有 manage_categories 授权 */
  const canManageCategories = computed(() => userStore.can('manage_categories'))

  /** 可编辑/删除/导入资产：持有 manage_assets 授权 */
  const canManageAssets = computed(() => userStore.can('manage_assets'))

  /** 可管理组织架构：持有 manage_organizations 授权 */
  const canManageOrganizations = computed(() => userStore.can('manage_organizations'))

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
