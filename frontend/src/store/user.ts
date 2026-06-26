/* 磐盘 - 用户 Store */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import { getMyPermissions } from '@/api/permissions'
import { TOKEN_KEY } from '@/utils/request'
import { ROLE_LEVELS } from '@/constants'
import type { User, UserRoleType } from '@/types'

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const profile = ref<User | null>(null)
  /** 当前用户持有的业务操作授权码集合（admin 恒真，不依赖此集合） */
  const operations = ref<string[]>([])

  const isLoggedIn = computed(() => !!token.value)
  /** 是否为超级管理员（走职位，拥有全部权限） */
  const isAdmin = computed(() => profile.value?.role === 'admin')

  /** 拉取当前用户的管理权限摘要（登录/刷新后调用） */
  async function fetchMyPermissions() {
    try {
      const { data } = await getMyPermissions()
      operations.value = data.operations || []
    } catch {
      operations.value = []
    }
  }

  /** 登录 */
  async function login(phone: string, password: string) {
    const { data } = await authApi.login({ phone, password })
    token.value = data.token
    profile.value = data.user
    localStorage.setItem(TOKEN_KEY, data.token)
    await fetchMyPermissions()
  }

  /** 登出 */
  async function logout() {
    try {
      await authApi.logout()
    } finally {
      token.value = null
      profile.value = null
      operations.value = []
      localStorage.removeItem(TOKEN_KEY)
    }
  }

  /** 获取当前用户信息 */
  async function fetchProfile() {
    const { data } = await authApi.getProfile()
    profile.value = data
    await fetchMyPermissions()
  }

  /** 是否持有某业务操作权限（admin 恒真） */
  function can(code: string): boolean {
    if (profile.value?.role === 'admin') return true
    return operations.value.includes(code)
  }

  /** 是否拥有指定角色 */
  function hasRole(role: UserRoleType): boolean {
    return profile.value?.role === role
  }

  /** 是否达到指定角色级别及以上（仅用于职位展示排序，不再驱动权限） */
  function hasMinRole(role: UserRoleType): boolean {
    if (!profile.value) return false
    const currentLevel = ROLE_LEVELS[profile.value.role]
    const requiredLevel = ROLE_LEVELS[role]
    return currentLevel <= requiredLevel
  }

  return {
    token,
    profile,
    operations,
    isLoggedIn,
    isAdmin,
    login,
    logout,
    fetchProfile,
    fetchMyPermissions,
    can,
    hasRole,
    hasMinRole,
  }
})
