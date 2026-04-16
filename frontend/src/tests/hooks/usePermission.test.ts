import { describe, it, expect } from 'vitest'
import { usePermission } from '@/hooks/usePermission'

describe('usePermission', () => {
  describe('role hierarchy', () => {
    it('admin has all permissions', () => {
      const { isAdmin, isManager, isSupervisor, isLeader, isStaff } = usePermission('admin')
      expect(isAdmin()).toBe(true)
      expect(isManager()).toBe(true)
      expect(isSupervisor()).toBe(true)
      expect(isLeader()).toBe(true)
      expect(isStaff()).toBe(true)
    })

    it('manager cannot be admin', () => {
      const { isAdmin, isManager } = usePermission('manager')
      expect(isAdmin()).toBe(false)
      expect(isManager()).toBe(true)
    })

    it('staff has only staff permission', () => {
      const { isAdmin, isManager, isSupervisor, isLeader, isStaff } = usePermission('staff')
      expect(isAdmin()).toBe(false)
      expect(isManager()).toBe(false)
      expect(isSupervisor()).toBe(false)
      expect(isLeader()).toBe(false)
      expect(isStaff()).toBe(true)
    })

    it('supervisor can manage leader and staff', () => {
      const { canManage } = usePermission('supervisor')
      expect(canManage('leader')).toBe(true)
      expect(canManage('staff')).toBe(true)
      expect(canManage('manager')).toBe(false)
    })
  })
})
