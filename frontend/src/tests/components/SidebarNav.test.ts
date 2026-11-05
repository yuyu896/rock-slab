import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('@/api/inventories', () => ({
  getInventoryTasks: vi.fn().mockResolvedValue({ data: { count: 0 } }),
}))

vi.mock('@/api/assets', () => ({
  getFixedAssets: vi.fn(),
}))

const permissions = vi.hoisted(() => ({ codes: [] as string[], isAdmin: false }))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    isAdmin: permissions.isAdmin,
    can: (code: string) => permissions.codes.includes(code),
    canAccessPage: (page: string) => ({
      categories: ['view_categories'],
      asset_ledger: ['view_asset_ledger'], instances: ['view_instances', 'edit_instances', 'change_instance_assignee'],
      assignment: ['view_assignment', 'create_assignment'],
      purchase: ['view_purchase', 'create_purchase'], return: ['view_return'],
      transfer: ['view_transfer', 'create_transfer'],
      recovery: ['view_recovery', 'create_recovery'], recovery_ledger: ['view_recovery_ledger'], inventory: ['view_inventory'],
      reconciliation: ['view_reconciliation'],
      personnel: ['view_users', 'view_organizations'], departments: ['view_departments'],
      suppliers: ['view_suppliers'], dashboard: ['view_dashboard'], reports: ['view_reports'],
      permission_matrix: ['view_permission_matrix'], audit: ['view_audit_logs'],
    }[page] || []).some(code => permissions.codes.includes(code)),
  }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/dashboard' }),
  useRouter: () => ({ push: vi.fn() }),
}))

import SidebarNav from '@/components/layout/SidebarNav.vue'
import { getFixedAssets } from '@/api/assets'

function mountNav() {
  const wrapper = mount(SidebarNav, { props: { isCollapsed: false } })
  return wrapper
}

function findInstanceItem(wrapper: ReturnType<typeof mountNav>) {
  return wrapper.findAll('.nav-submenu-item').find(a => a.text().includes('实例档案'))
}

describe('SidebarNav 实例档案待补录徽标（P3 刀三）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    permissions.codes = ['view_inventory', 'view_instances', 'view_recovery_ledger']
  })

  it('有待补录时子项显示计数徽标，请求带 pending_serial=1', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 5, next: null, previous: null, results: [] },
    } as any)
    const wrapper = mountNav()
    await flushPromises()

    expect(getFixedAssets).toHaveBeenCalledWith(
      expect.objectContaining({ pending_serial: '1', pageSize: 1 }),
    )
    const item = findInstanceItem(wrapper)!
    const badge = item.find('.nav-badge')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('5')
  })

  it('无待补录不显示徽标', async () => {
    vi.mocked(getFixedAssets).mockResolvedValue({
      data: { count: 0, next: null, previous: null, results: [] },
    } as any)
    const wrapper = mountNav()
    await flushPromises()

    expect(findInstanceItem(wrapper)!.find('.nav-badge').exists()).toBe(false)
  })

  it('接口失败静默按 0 处理，导航不受影响', async () => {
    vi.mocked(getFixedAssets).mockRejectedValue(new Error('network'))
    const wrapper = mountNav()
    await flushPromises()

    expect(findInstanceItem(wrapper)).toBeTruthy()
    expect(findInstanceItem(wrapper)!.find('.nav-badge').exists()).toBe(false)
  })
})

describe('SidebarNav 物资处置台账入口', () => {
  it('显示物资处置台账子入口', () => {
    const wrapper = mountNav()
    const item = wrapper.findAll('.nav-submenu-item').find(a => a.text().includes('物资处置台账'))
    expect(item).toBeTruthy()
  })
})

describe('SidebarNav 权限可见性', () => {
  it('审计日志只对系统管理员显示，旧权限码不开放入口', () => {
    permissions.codes = ['view_audit_logs']
    const staffNav = mountNav()
    expect(staffNav.text()).not.toContain('审计日志')

    permissions.isAdmin = true
    const adminNav = mountNav()
    expect(adminNav.text()).toContain('审计日志')
    permissions.isAdmin = false
  })

  it('仅有维护对账权限时隐藏对账入口', () => {
    permissions.codes = ['manage_reconciliation']
    const wrapper = mountNav()
    const labels = wrapper.findAll('.nav-link, .nav-submenu-item').map(item => item.text())

    expect(labels.some(label => label.includes('对账'))).toBe(false)
  })

  it('只展示获准模块，不展示无关页面', () => {
    permissions.codes = ['view_categories', 'view_permission_matrix']
    const wrapper = mountNav()
    const labels = wrapper.findAll('.nav-link, .nav-submenu-item').map(item => item.text())

    expect(labels.some(label => label.includes('品目列表'))).toBe(true)
    expect(labels.some(label => label.includes('权限矩阵'))).toBe(true)
    expect(labels.some(label => label.includes('工作台'))).toBe(false)
    expect(labels.some(label => label.includes('实例档案'))).toBe(false)
  })

  it('仅实例编辑权限显示实例档案入口，但不请求完整列表待补录徽标', async () => {
    vi.clearAllMocks()
    permissions.codes = ['edit_instances']
    const wrapper = mountNav()
    await flushPromises()

    expect(findInstanceItem(wrapper)).toBeTruthy()
    expect(getFixedAssets).not.toHaveBeenCalled()
  })

  it('旧品目创建权限不显示品目入口', () => {
    permissions.codes = ['create_categories']
    const wrapper = mountNav()
    const labels = wrapper.findAll('.nav-submenu-item').map(item => item.text())

    expect(labels).not.toContain('品目列表')
    expect(labels).not.toContain('新增品目')
  })

  it('归还旧写权限不再显示操作入口', () => {
    permissions.codes = ['create_purchase', 'create_assignment', 'create_return', 'create_transfer', 'create_recovery']
    const wrapper = mountNav()
    const labels = wrapper.findAll('.nav-submenu-item').map(item => item.text())

    expect(labels).toEqual(expect.arrayContaining(['采购入库', '领用出库', '调拨', '回收单']))
    expect(labels).not.toContain('归还历史')
  })

  it('归还查看权限也不显示已停用的历史入口', () => {
    permissions.codes = ['view_return']
    const wrapper = mountNav()
    const labels = wrapper.findAll('.nav-submenu-item').map(item => item.text())

    expect(labels).not.toContain('归还历史')
    expect(labels).not.toContain('归还入库')
  })

})
