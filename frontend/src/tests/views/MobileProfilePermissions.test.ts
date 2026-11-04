import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const state = vi.hoisted(() => ({
  isAdmin: false,
  permissions: [] as string[],
  push: vi.fn(),
  unreadCount: 0,
  fetchUnreadCount: vi.fn(),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push: state.push }) }))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    isAdmin: state.isAdmin,
    profile: { name: '测试员工', phone: '13800000000', role: 'staff' },
    can: (code: string) => state.isAdmin || state.permissions.includes(code),
    canAccessPage: (page: string) => state.isAdmin || ({
      mobile_assets: ['view_asset_ledger'],
      mobile_my_documents: ['create_purchase', 'create_assignment'],
      mobile_approvals: ['approve_recovery', 'review_inventory'],
      mobile_inventory: ['view_inventory', 'manage_inventory', 'review_inventory'],
      mobile_notifications: ['view_notifications', 'view_approval_reports'],
    }[page] || []).some(code => state.permissions.includes(code)),
  }),
}))
vi.mock('@/store/notification', () => ({
  useNotificationStore: () => ({ unreadCount: state.unreadCount, fetchUnreadCount: state.fetchUnreadCount }),
}))
vi.mock('@/api/auth', () => ({ updatePassword: vi.fn() }))
vi.mock('@/utils/request', () => ({ TOKEN_KEY: 'test-token', handleApiError: vi.fn() }))
vi.mock('element-plus', () => ({
  ElMessageBox: { confirm: vi.fn() },
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

import MobileProfile from '@/views/mobile/Profile.vue'

describe('MobileProfile permission visibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    state.isAdmin = false
    state.permissions = []
    state.unreadCount = 0
  })

  it('没有资产台账查看权限时隐藏资产查询入口', async () => {
    const wrapper = mount(MobileProfile)
    await flushPromises()

    expect(wrapper.findAll('.menu-item').some(item => item.text().includes('资产查询'))).toBe(false)
    wrapper.unmount()
  })

  it('有资产台账查看权限时显示入口并导航到已注册页面', async () => {
    state.permissions = ['view_asset_ledger']
    const wrapper = mount(MobileProfile)
    await flushPromises()

    const assets = wrapper.findAll('.menu-item').find(item => item.text().includes('资产查询'))
    expect(assets).toBeDefined()
    await assets!.trigger('click')
    expect(state.push).toHaveBeenCalledWith('/mobile/assets')
    wrapper.unmount()
  })

  it('只有审批报告权限时仍显示消息中心入口且不请求普通通知未读数', async () => {
    state.permissions = ['view_approval_reports']
    const wrapper = mount(MobileProfile)
    await flushPromises()

    const notifications = wrapper.findAll('.menu-item').find(item => item.text().includes('审批报告'))
    expect(notifications).toBeDefined()
    await notifications!.trigger('click')
    expect(state.push).toHaveBeenCalledWith('/mobile/notifications')
    expect(state.fetchUnreadCount).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it.each(['import_inventory', 'rescan_inventory', 'view_inventory_report'])(
    '仅有 %s 时不显示移动端盘点入口', async (permission) => {
      state.permissions = [permission]
      const wrapper = mount(MobileProfile)
      await flushPromises()

      expect(wrapper.findAll('.menu-item').some(item => item.text().includes('盘点任务'))).toBe(false)
      wrapper.unmount()
    },
  )
})
