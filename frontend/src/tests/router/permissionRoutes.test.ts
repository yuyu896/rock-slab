import { beforeEach, describe, expect, it, vi } from 'vitest'
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
const mobileRoute = (path: string) => routes.find(route => route.path === '/mobile')?.children?.find(route => route.path === path)

beforeEach(async () => {
  auth.isAdmin = false
  auth.profileLoaded = true
  auth.permissions = []
  auth.pageOperations = {
    dashboard: ['view_dashboard'], reports: ['view_reports'],
    asset_ledger: ['view_asset_ledger'], instances: ['view_instances', 'edit_instances', 'change_instance_assignee'],
    categories: ['view_categories', 'create_categories', 'import_categories'],
    purchase: ['view_purchase', 'create_purchase', 'edit_purchase', 'submit_purchase', 'approve_purchase', 'withdraw_purchase', 'import_purchase'],
    assignment: ['view_assignment', 'create_assignment', 'edit_assignment', 'submit_assignment', 'approve_assignment', 'withdraw_assignment', 'import_assignment'],
    transfer: ['view_transfer', 'create_transfer', 'edit_transfer', 'submit_transfer', 'approve_internal_transfer', 'withdraw_transfer'],
    recovery: ['view_recovery', 'create_recovery', 'edit_recovery', 'submit_recovery', 'approve_recovery', 'withdraw_recovery'],
    recovery_ledger: ['view_recovery_ledger'],
    inventory: ['view_inventory', 'create_inventory', 'manage_inventory', 'import_inventory', 'review_inventory', 'view_inventory_report'],
    mobile_inventory: ['view_inventory', 'manage_inventory', 'review_inventory'],
    reconciliation: ['view_reconciliation'],
    personnel: ['view_users', 'create_users', 'edit_users', 'delete_users', 'view_organizations', 'create_organizations', 'edit_organizations', 'delete_organizations'],
    departments: ['view_departments', 'create_departments'],
    suppliers: ['view_suppliers', 'create_suppliers'],
    permission_matrix: ['view_permission_matrix'],
    mobile_assets: ['view_asset_ledger'], mobile_scan: ['view_asset_ledger', 'view_instances'],
    mobile_my_documents: ['create_purchase', 'view_purchase', 'edit_purchase'],
    mobile_approvals: ['approve_recovery', 'review_inventory'],
    mobile_approval_detail: ['approve_recovery'],
    mobile_notifications: ['view_notifications', 'view_approval_reports'],
  }
  localStorage.setItem(TOKEN_KEY, 'test-token')
  await router.replace('/login')
})

describe('权限路由', () => {
  it('对账模块仅凭查看权限开放页面路由', async () => {
    auth.permissions = ['manage_reconciliation']
    await router.push('/reconciliation')
    expect(router.currentRoute.value.path).not.toBe('/reconciliation')

    await router.replace('/login')
    auth.permissions = ['view_reconciliation']
    await router.push('/reconciliation')
    expect(router.currentRoute.value.path).toBe('/reconciliation/orders')
  })

  it('业务页面使用对应查看权限，权限分配仍只允许系统管理员', () => {
    expect(childRoute('assets/summary')?.meta?.permissionPage).toBe('asset_ledger')
    expect(childRoute('categories')?.meta?.operation).toBe('view_categories')
    expect(childRoute('departments')?.meta?.operation).toBe('view_departments')
    expect(childRoute('suppliers')?.meta?.operation).toBe('view_suppliers')
    expect(childRoute('fixed-assets')?.meta?.permissionPage).toBe('instances')
    expect(childRoute('transfers/purchase')?.meta?.permissionPage).toBe('purchase')
    expect(childRoute('admin/permissions')?.meta?.requiresAdmin).toBe(true)
    expect(childRoute('admin/permission-matrix')?.meta?.permissionPage).toBe('permission_matrix')
    expect(childRoute('audit')?.meta?.requiresAdmin).toBe(true)
  })

  it('审计日志路由仅允许系统管理员直接进入', async () => {
    auth.permissions = ['view_audit_logs']
    await router.push('/audit')
    expect(router.currentRoute.value.path).not.toBe('/audit')

    await router.replace('/login')
    auth.isAdmin = true
    await router.push('/audit')
    expect(router.currentRoute.value.path).toBe('/audit')
  })

  it('仅有实例编辑权限时可进入实例维护页面', async () => {
    auth.permissions = ['edit_instances']
    await router.push('/fixed-assets')

    expect(router.currentRoute.value.path).toBe('/fixed-assets')
  })

  it('类别编辑详情需要同时拥有查看和编辑权限', async () => {
    expect(childRoute('categories/:id/edit')?.meta?.operationAll).toEqual([
      'view_categories', 'edit_categories',
    ])

    auth.permissions = ['edit_categories']
    await router.push('/categories/category-1/edit')
    expect(router.currentRoute.value.path).not.toBe('/categories/category-1/edit')

    await router.replace('/login')
    auth.permissions = ['view_categories']
    await router.push('/categories/category-1/edit')
    expect(router.currentRoute.value.path).not.toBe('/categories/category-1/edit')

    await router.replace('/login')
    auth.permissions = ['view_categories', 'edit_categories']
    await router.push('/categories/category-1/edit')
    expect(router.currentRoute.value.path).toBe('/categories/category-1/edit')
  })

  it('部门和供应商页面不会仅凭编辑或删除权限开放', async () => {
    auth.permissions = ['edit_departments']
    await router.push('/departments')
    expect(router.currentRoute.value.path).not.toBe('/departments')

    await router.replace('/login')
    auth.permissions = ['delete_suppliers']
    await router.push('/suppliers')
    expect(router.currentRoute.value.path).not.toBe('/suppliers')
  })

  it('审批中心接受任一审批权限', async () => {
    auth.permissions = ['approve_recovery']
    await router.push('/mobile/approval')

    expect(router.currentRoute.value.path).toBe('/mobile/approval')
  })

  it('审批报告权限单独允许访问通知中心', async () => {
    expect(mobileRoute('notifications')?.meta?.permissionPage).toBe('mobile_notifications')
    auth.permissions = ['view_approval_reports']
    await router.push('/mobile/notifications')

    expect(router.currentRoute.value.path).toBe('/mobile/notifications')
  })

  it('物资处置台账使用独立权限入口', async () => {
    expect(childRoute('transfers/recovery/ledger')?.meta?.permissionPage).toBe('recovery_ledger')

    auth.permissions = ['view_recovery_ledger']
    await router.push('/transfers/recovery/ledger')
    expect(router.currentRoute.value.path).toBe('/transfers/recovery/ledger')
  })

  it('旧处置权限不能进入物资处置台账', async () => {
    auth.permissions = ['dispose_assets']
    await router.push('/transfers/recovery/ledger')

    expect(router.currentRoute.value.path).not.toBe('/transfers/recovery/ledger')
  })

  it('移动盘点页面仅接受当前支持的查看、维护或审批权限', async () => {
    expect(mobileRoute('inventory')?.meta?.permissionPage).toBe('mobile_inventory')
    auth.permissions = ['import_inventory']
    await router.push('/mobile/inventory')
    expect(router.currentRoute.value.path).not.toBe('/mobile/inventory')

    auth.permissions = ['view_inventory', 'edit_inventory']
    await router.push('/mobile/inventory/t-1')
    expect(router.currentRoute.value.path).toBe('/mobile/inventory/t-1')
  })

  it('重盘权限需同时具备维护权限才能进入盘点管理页', async () => {
    auth.permissions = ['rescan_inventory']
    await router.push('/inventory')
    expect(router.currentRoute.value.path).not.toBe('/inventory')

    auth.permissions = ['rescan_inventory', 'manage_inventory']
    await router.push('/inventory')
    expect(router.currentRoute.value.path).toBe('/inventory')
  })

  it('资产查询的兼容路由要求资产台账查看权限', async () => {
    expect(mobileRoute('my-assets')?.meta?.permissionPage).toBe('mobile_assets')
    expect(mobileRoute('my-assets')?.meta?.title).toBe('资产查询')
    expect(mobileRoute('my-assets')?.component).toBeDefined()
    expect(mobileRoute('assets')?.meta?.title).toBe('资产查询')
    expect(mobileRoute('assets')?.meta?.permissionPage).toBe('mobile_assets')

    await router.push('/mobile/my-assets')
    expect(router.currentRoute.value.path).toBe('/login')

    auth.permissions = ['view_asset_ledger']
    await router.push('/mobile/my-assets')
    expect(router.currentRoute.value.path).toBe('/mobile/my-assets')
  })

  it('无权页面跳到首个有权主页面', async () => {
    auth.permissions = ['view_reports']
    await router.push('/dashboard')

    expect(router.currentRoute.value.path).toBe('/reports')
  })

  it('没有任何页面权限时取消导航，不循环跳回工作台', async () => {
    await router.push('/dashboard')

    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('系统管理员不依赖逐项授权即可访问业务页面', async () => {
    auth.isAdmin = true
    await router.push('/reconciliation')

    expect(router.currentRoute.value.path).toBe('/reconciliation/orders')
  })

  it('采购新建和编辑入口均要求采购查看、编辑和品目查看权限', async () => {
    expect(childRoute('transfers/purchase/create')?.meta?.operationAll).toEqual([
      'view_purchase', 'edit_purchase', 'view_categories',
    ])

    auth.permissions = ['edit_purchase', 'view_categories']
    await router.push('/transfers/purchase/create')
    expect(router.currentRoute.value.path).not.toBe('/transfers/purchase/create')

    await router.replace('/login')
    auth.permissions = ['view_purchase', 'edit_purchase', 'view_categories']
    await router.push('/transfers/purchase/create')
    expect(router.currentRoute.value.path).toBe('/transfers/purchase/create')

    await router.replace('/login')
    auth.permissions = ['view_purchase', 'edit_purchase', 'view_categories']
    await router.push('/transfers/purchase/create?id=t-1')
    expect(router.currentRoute.value.fullPath).toBe('/transfers/purchase/create?id=t-1')

    await router.replace('/login')
    auth.permissions = ['view_purchase', 'edit_purchase']
    await router.push('/transfers/purchase/create?id=t-1')
    expect(router.currentRoute.value.fullPath).not.toBe('/transfers/purchase/create?id=t-1')
  })

  it('归还前端入口已移除，历史单据不提供独立页面路由', async () => {
    expect(childRoute('transfers/return')).toBeUndefined()
    expect(childRoute('transfers/return/create')).toBeUndefined()
    expect(childRoute('transfers/return/:id')).toBeUndefined()

    auth.permissions = ['view_return']
    await router.push('/transfers/return')
    expect(router.currentRoute.value.path).not.toBe('/transfers/return')

    await router.push('/transfers/return/create')
    expect(router.currentRoute.value.path).not.toBe('/transfers/return/create')

    await router.push('/transfers/return/return-1')
    expect(router.currentRoute.value.path).not.toBe('/transfers/return/return-1')
  })

  it('流转单新建和编辑入口均要求模块查看、编辑及候选数据查看权限', async () => {
    const cases = [
      { path: '/transfers/assign/create', permissions: ['view_assignment', 'edit_assignment', 'view_asset_ledger'] },
      { path: '/transfers/transfer/create', permissions: ['view_transfer', 'edit_transfer', 'view_asset_ledger'] },
      { path: '/transfers/recovery/create', permissions: ['view_recovery', 'edit_recovery', 'view_asset_ledger'] },
      { path: '/mobile/submit/assign', permissions: ['view_assignment', 'edit_assignment', 'view_asset_ledger'] },
      { path: '/mobile/submit/transfer', permissions: ['view_transfer', 'edit_transfer', 'view_asset_ledger'] },
      { path: '/mobile/purchase', permissions: ['view_purchase', 'edit_purchase', 'view_categories'] },
    ]

    for (const item of cases) {
      await router.replace('/login')
      auth.permissions = item.permissions.slice(1)
      await router.push(item.path)
      expect(router.currentRoute.value.fullPath).not.toBe(item.path)

      await router.replace('/login')
      auth.permissions = item.permissions
      await router.push(item.path)
      expect(router.currentRoute.value.path).toBe(item.path)

      await router.replace('/login')
      auth.permissions = item.permissions
      await router.push(`${item.path}?id=existing-1`)
      expect(router.currentRoute.value.fullPath).toBe(`${item.path}?id=existing-1`)

      await router.replace('/login')
      auth.permissions = item.permissions.slice(1)
      await router.push(`${item.path}?id=existing-1`)
      expect(router.currentRoute.value.fullPath).not.toBe(`${item.path}?id=existing-1`)
    }
  })
})
