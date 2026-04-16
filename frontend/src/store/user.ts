/* 磐盘 - 用户 Store */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import { TOKEN_KEY } from '@/utils/request'
import { ROLE_LEVELS } from '@/constants'
import type { User, UserRoleType } from '@/types'

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const profile = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  /** 登录 */
  async function login(phone: string, password: string) {
    const { data } = await authApi.login({ phone, password })
    token.value = data.token
    profile.value = data.user
    localStorage.setItem(TOKEN_KEY, data.token)
  }

  /** 登出 */
  async function logout() {
    try {
      await authApi.logout()
    } finally {
      token.value = null
      profile.value = null
      localStorage.removeItem(TOKEN_KEY)
    }
  }

  /** 获取当前用户信息 */
  async function fetchProfile() {
    const { data } = await authApi.getProfile()
    profile.value = data
  }

  /** 是否拥有指定角色 */
  function hasRole(role: UserRoleType): boolean {
    return profile.value?.role === role
  }

  /** 是否达到指定角色级别及以上 */
  function hasMinRole(role: UserRoleType): boolean {
    if (!profile.value) return false
    const currentLevel = ROLE_LEVELS[profile.value.role]
    const requiredLevel = ROLE_LEVELS[role]
    return currentLevel <= requiredLevel
  }

  return {
    token,
    profile,
    isLoggedIn,
    login,
    logout,
    fetchProfile,
    hasRole,
    hasMinRole,
  }
})
