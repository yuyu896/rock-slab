import { describe, expect, it, vi } from 'vitest'
import { routes, default as router } from '@/router'
import { TOKEN_KEY } from '@/utils/request'

const auth = vi.hoisted(() => ({
  isAdmin: false,
  profileLoaded: true,
  permissions: [] as string[],
  pageOperations: {} as Record<string, string[]>,
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    get isAdmin() { return auth.isAdmin },
    get profileLoaded() { return auth.profileLoaded },
    can: (code: string) => auth.isAdmin || auth.permissions.includes(code),
    canAccessPage: (page: string) => auth.isAdmin || (auth.pageOperations[page] || []).some(code => auth.permissions.includes(code)),
    fetchProfile: vi.fn(),
    refreshOperationsIfStale: vi.fn(),
  }),
}))

const topLevel = routes.find(route => route.path === '/')!
const childRoute = (path: string) => topLevel.children?.find(route => route.path === path)

describe('对账路由整合', () => {
  it('三个子路由均存在且 permissionPage 为 reconciliation', () => {
    const orders = childRoute('reconciliation/orders')
    const differences = childRoute('reconciliation/differences')
    const payment = childRoute('reconciliation/payment')

    expect(orders).toBeDefined()
    expect(orders?.meta?.permissionPage).toBe('reconciliation')

    expect(differences).toBeDefined()
    expect(differences?.meta?.permissionPage).toBe('reconciliation')

    expect(payment).toBeDefined()
    expect(payment?.meta?.permissionPage).toBe('reconciliation')
  })

  it('/reconciliation 重定向到 /reconciliation/orders', () => {
    const resolved = router.resolve('/reconciliation')
    expect(resolved.redirectedFrom).toBeUndefined()
    const reconciliationRoute = childRoute('reconciliation')
    expect(reconciliationRoute?.redirect).toBe('/reconciliation/orders')
    expect((reconciliationRoute as { component?: unknown })?.component).toBeUndefined()
  })

  it('/reconciliation 导航落地于 /reconciliation/orders（有权限时）', async () => {
    auth.permissions = ['view_reconciliation']
    auth.pageOperations = { reconciliation: ['view_reconciliation'] }
    localStorage.setItem(TOKEN_KEY, 'test-token')
    await router.replace('/login')
    await router.push('/reconciliation')
    expect(router.currentRoute.value.path).toBe('/reconciliation/orders')
  })

  it('旧 Reconciliation.vue 不再被任何路由引用', () => {
    const reconciliationRoute = childRoute('reconciliation')
    expect((reconciliationRoute as { component?: unknown })?.component).toBeUndefined()
    expect(reconciliationRoute?.redirect).toBe('/reconciliation/orders')
  })
})
