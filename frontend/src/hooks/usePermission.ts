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

  /** 可审批：主管及以上 */
  const canApprove = computed(() => roleLevel.value <= 3)

  /** 可管理用户：主管及以上（主管管区域，组长管分公司，admin管全部） */
  const canManageUsers = computed(() => roleLevel.value <= 3)

  /** 可提交单据：专员、组长、主管 */
  const canCreateDocument = computed(() => roleLevel.value >= 3)

  /** 可管理类目：主管及以上 */
  const canManageCategories = computed(() => roleLevel.value <= 3)

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
    hasMinRole,
  }
}
