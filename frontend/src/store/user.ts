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
  const expiresAt = ref<string | null>(localStorage.getItem('rock_slab_token_expires_at'))
  const profile = ref<User | null>(null)
  /** 当前用户持有的业务操作授权码集合（admin 恒真，不依赖此集合） */
  const operations = ref<string[]>([])
  /** 页面入口的授权关系由后端权限目录提供，避免前端导航各自维护权限码列表。 */
  const pageOperations = ref<Record<string, string[]>>({})
  /** 操作前置由同一后端权限目录提供，避免运行时重复维护。 */
  const operationPrerequisites = ref<Record<string, string[]>>({})
  /** profile 是否已就绪（路由守卫等待用；登出重置） */
  const profileLoaded = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  /** 是否为超级管理员（走职位，拥有全部权限） */
  const isAdmin = computed(() => profile.value?.role === 'admin')
  /** token 是否已过期 */
  const isTokenExpired = computed(() => {
    if (!expiresAt.value) return false
    return new Date() >= new Date(expiresAt.value)
  })

  let operationsFetchedAt = 0
  let tokenExpiryCheckInterval: number | null = null

  /** camelCase 键转 snake_case（仅处理 pageOperations 内层键） */
  function toSnakeKeys(obj: Record<string, string[]>): Record<string, string[]> {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [k.replace(/([A-Z])/g, '_$1').toLowerCase(), v])
    )
  }

  /** 拉取当前用户的管理权限摘要（登录/刷新后调用） */
  async function fetchMyPermissions() {
    try {
      const { data } = await getMyPermissions()
      operations.value = data.operations || []
      pageOperations.value = toSnakeKeys(data.pageOperations || {})
      operationPrerequisites.value = data.operationPrerequisites || {}
      operationsFetchedAt = Date.now()
    } catch {
      operations.value = []
      pageOperations.value = {}
      operationPrerequisites.value = {}
    }
  }

  /** 权限变更免手动刷新：距上次拉取 ≥5 分钟则后台静默重拉（失败不打扰） */
  async function refreshOperationsIfStale() {
    if (!token.value || Date.now() - operationsFetchedAt < 5 * 60 * 1000) return
    try {
      await fetchMyPermissions()
    } catch { /* 静默 */ }
  }

  /** 登录 */
  async function login(phone: string, password: string) {
    const { data } = await authApi.login({ phone, password })
    token.value = data.token
    expiresAt.value = data.expiresAt
    profile.value = data.user
    localStorage.setItem(TOKEN_KEY, data.token)
    localStorage.setItem('rock_slab_token_expires_at', data.expiresAt)
    startTokenExpiryCheck()
    await fetchMyPermissions()
  }

  /** 登出 */
  async function logout() {
    stopTokenExpiryCheck()
    try {
      await authApi.logout()
    } finally {
      token.value = null
      expiresAt.value = null
      profile.value = null
      operations.value = []
      pageOperations.value = {}
      operationPrerequisites.value = {}
      profileLoaded.value = false
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem('rock_slab_token_expires_at')
    }
  }

  /** 获取当前用户信息 */
  async function fetchProfile() {
    const { data } = await authApi.getProfile()
    profile.value = data
    await fetchMyPermissions()
    profileLoaded.value = true
  }

  /** 是否持有某业务操作权限（admin 恒真） */
  function can(code: string): boolean {
    if (profile.value?.role === 'admin') return true
    return operations.value.includes(code)
      && (operationPrerequisites.value[code] || []).every(prerequisite => operations.value.includes(prerequisite))
  }

  function canAccessPage(page: string): boolean {
    if (profile.value?.role === 'admin') return true
    return (pageOperations.value[page] || []).some(can)
  }

  /** 启动 token 过期检查定时器（每 30 秒检查一次） */
  function startTokenExpiryCheck() {
    stopTokenExpiryCheck()
    tokenExpiryCheckInterval = window.setInterval(() => {
      if (isTokenExpired.value) {
        logout()
      }
    }, 30 * 1000)
  }

  /** 停止 token 过期检查定时器 */
  function stopTokenExpiryCheck() {
    if (tokenExpiryCheckInterval !== null) {
      clearInterval(tokenExpiryCheckInterval)
      tokenExpiryCheckInterval = null
    }
  }

  /** 应用卸载时清理定时器 */
  function cleanup() {
    stopTokenExpiryCheck()
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
    expiresAt,
    profile,
    profileLoaded,
    operations,
    pageOperations,
    refreshOperationsIfStale,
    isLoggedIn,
    isAdmin,
    isTokenExpired,
    login,
    logout,
    fetchProfile,
    fetchMyPermissions,
    startTokenExpiryCheck,
    stopTokenExpiryCheck,
    cleanup,
    can,
    canAccessPage,
    hasRole,
    hasMinRole,
  }
})
