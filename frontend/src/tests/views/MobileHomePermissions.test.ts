import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const state = vi.hoisted(() => ({
  permissions: [] as string[],
  push: vi.fn(),
  initNotifications: vi.fn(),
  getPendingTransfers: vi.fn().mockResolvedValue({ data: { count: 0 } }),
  getTransfers: vi.fn().mockResolvedValue({ data: { count: 0 } }),
  getInventoryTasks: vi.fn().mockResolvedValue({ data: { count: 0 } }),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push: state.push }) }))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    profile: { name: '张三', role: 'manager' },
    can: (code: string) => state.permissions.includes(code),
  }),
}))
vi.mock('@/store/notification', () => ({
  useNotificationStore: () => ({ unreadCount: 0, init: state.initNotifications }),
}))
vi.mock('@/api/transfers', () => ({
  getPendingTransfers: state.getPendingTransfers,
  getTransfers: state.getTransfers,
}))
vi.mock('@/api/inventories', () => ({ getInventoryTasks: state.getInventoryTasks }))

import MobileHome from '@/views/mobile/Home.vue'

describe('MobileHome transfer create shortcuts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    state.permissions = []
  })

  it('hides create shortcuts when module view permission is missing', async () => {
    state.permissions = [
      'edit_purchase', 'view_categories',
      'edit_transfer', 'view_asset_ledger',
      'edit_assignment', 'view_asset_ledger',
    ]
    const wrapper = mount(MobileHome)
    await flushPromises()

    const labels = wrapper.findAll('.quick-action-btn .action-label').map(label => label.text())
    expect(labels).not.toContain('提交入库')
    expect(labels).not.toContain('提交调拨')
    expect(labels).not.toContain('提交领用')
    expect(labels).toContain('扫码查询')
    expect(labels).toContain('盘点任务')
  })

  it('shows create shortcuts only when module, edit and candidate view permissions are present', async () => {
    state.permissions = [
      'view_purchase', 'edit_purchase', 'view_categories',
      'view_transfer', 'edit_transfer', 'view_asset_ledger',
      'view_assignment', 'edit_assignment',
    ]
    const wrapper = mount(MobileHome)
    await flushPromises()

    const labels = wrapper.findAll('.quick-action-btn .action-label').map(label => label.text())
    expect(labels).toContain('提交入库')
    expect(labels).toContain('提交调拨')
    expect(labels).toContain('提交领用')
  })
})
