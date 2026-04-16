import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock the API module
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  getProfile: vi.fn(),
}))

import { useUserStore } from '@/store/user'
import * as authApi from '@/api/auth'

describe('User Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('stores token and sets profile on successful login', async () => {
      const mockUser = { id: '1', phone: '13900000000', name: 'Test', role: 'admin', status: 'active' }
      vi.mocked(authApi.login).mockResolvedValue({
        data: { token: 'test-token-123', user: mockUser },
      } as any)

      const store = useUserStore()
      await store.login('13900000000', 'test123456')

      expect(localStorage.getItem('rock_slab_token')).toBe('test-token-123')
      expect(store.profile).toEqual(mockUser)
      expect(store.isLoggedIn).toBe(true)
    })

    it('clears state on login failure', async () => {
      vi.mocked(authApi.login).mockRejectedValue(new Error('Invalid credentials'))

      const store = useUserStore()
      await expect(store.login('13900000000', 'wrong')).rejects.toThrow()

      expect(localStorage.getItem('rock_slab_token')).toBeNull()
      expect(store.profile).toBeNull()
      expect(store.isLoggedIn).toBe(false)
    })
  })

  describe('logout', () => {
    it('clears token and profile on logout', async () => {
      localStorage.setItem('rock_slab_token', 'test-token')
      vi.mocked(authApi.logout).mockResolvedValue({} as any)

      const store = useUserStore()
      store.profile = { id: '1', phone: '13900000000', name: 'Test', role: 'admin', status: 'active' } as any

      await store.logout()

      expect(localStorage.getItem('rock_slab_token')).toBeNull()
      expect(store.profile).toBeNull()
    })

    it('clears state even if API call fails', async () => {
      localStorage.setItem('rock_slab_token', 'test-token')
      vi.mocked(authApi.logout).mockRejectedValue(new Error('Network error'))

      const store = useUserStore()
      await store.logout()

      expect(localStorage.getItem('rock_slab_token')).toBeNull()
    })
  })

  describe('role checks', () => {
    it('isAdmin returns true for admin role', () => {
      const store = useUserStore()
      store.profile = { role: 'admin' } as any
      expect(store.isAdmin).toBe(true)
    })

    it('isAdmin returns false for staff role', () => {
      const store = useUserStore()
      store.profile = { role: 'staff' } as any
      expect(store.isAdmin).toBe(false)
    })
  })
})
