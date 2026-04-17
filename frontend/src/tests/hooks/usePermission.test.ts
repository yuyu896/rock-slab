import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePermission } from '@/hooks/usePermission'
import { useUserStore } from '@/store/user'

describe('usePermission', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('role hierarchy', () => {
    it('admin has all permissions', () => {
      const userStore = useUserStore()
      userStore.profile = { role: 'admin' } as any

      const { isAdmin, isManager, isSupervisor, isLeader, isStaff } = usePermission()
      expect(isAdmin.value).toBe(true)
      expect(isManager.value).toBe(false)
      expect(isSupervisor.value).toBe(false)
      expect(isLeader.value).toBe(false)
      expect(isStaff.value).toBe(false)
    })

    it('manager cannot be admin', () => {
      const userStore = useUserStore()
      userStore.profile = { role: 'manager' } as any

      const { isAdmin, isManager } = usePermission()
      expect(isAdmin.value).toBe(false)
      expect(isManager.value).toBe(true)
    })

    it('staff has only staff permission', () => {
      const userStore = useUserStore()
      userStore.profile = { role: 'staff' } as any

      const { isAdmin, isManager, isSupervisor, isLeader, isStaff } = usePermission()
      expect(isAdmin.value).toBe(false)
      expect(isManager.value).toBe(false)
      expect(isSupervisor.value).toBe(false)
      expect(isLeader.value).toBe(false)
      expect(isStaff.value).toBe(true)
    })

    it('supervisor can manage users and approve', () => {
      const userStore = useUserStore()
      userStore.profile = { role: 'supervisor' } as any

      const { canManageUsers, canApprove } = usePermission()
      expect(canManageUsers.value).toBe(true)
      expect(canApprove.value).toBe(true)
    })
  })
})
