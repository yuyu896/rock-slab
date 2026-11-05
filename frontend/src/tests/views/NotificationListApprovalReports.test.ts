import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  permissions: [] as string[],
  back: vi.fn(),
  fetchNotifications: vi.fn(),
  markAsRead: vi.fn(),
  markAllAsRead: vi.fn(),
  getApprovalCCs: vi.fn(),
  markCCRead: vi.fn(),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ back: mocks.back }) }))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    isAdmin: false,
    can: (code: string) => mocks.permissions.includes(code),
  }),
}))
vi.mock('@/store/notification', () => ({
  useNotificationStore: () => ({
    fetchNotifications: mocks.fetchNotifications,
    markAsRead: mocks.markAsRead,
    markAllAsRead: mocks.markAllAsRead,
  }),
}))
vi.mock('@/api/notifications', () => ({
  getApprovalCCs: mocks.getApprovalCCs,
  markCCRead: mocks.markCCRead,
}))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn() } }))

import NotificationList from '@/views/mobile/NotificationList.vue'

function page(results: any[] = []) {
  return { data: { count: results.length, next: null, previous: null, results } }
}

function makeReport() {
  return {
    id: 'cc-1',
    transfer: 'transfer-1',
    inventoryTask: null,
    ccType: 'auto',
    ccTypeDisplay: '自动抄送',
    ccReason: '通过后向上级报告',
    recipient: 'user-1',
    recipientName: '审批人',
    isRead: false,
    readAt: null,
    approvalSnapshot: {
      docNumber: 'CG20261022-001',
      actionType: 'purchase',
      actionDisplay: '采购入库',
      result: '通过',
      approvedAt: '2026-10-22T09:30:00+08:00',
      reason: '办公设备采购',
    },
    createdAt: '2026-10-22T09:30:00+08:00',
    updatedAt: '2026-10-22T09:30:00+08:00',
  }
}

describe('NotificationList approval reports permissions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.permissions = []
    mocks.fetchNotifications.mockResolvedValue({ results: [] })
    mocks.getApprovalCCs.mockResolvedValue(page())
    mocks.markCCRead.mockImplementation(async (id: string) => ({
      data: { ...makeReport(), id, isRead: true, readAt: '2026-10-22T10:00:00+08:00' },
    }))
  })

  it('审批报告权限单独使用时只请求抄送列表并展示快照字段', async () => {
    mocks.permissions = ['view_approval_reports']
    mocks.getApprovalCCs.mockResolvedValue(page([makeReport()]))
    const wrapper = mount(NotificationList)
    await flushPromises()

    expect(mocks.fetchNotifications).not.toHaveBeenCalled()
    expect(mocks.getApprovalCCs).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('CG20261022-001')
    expect(wrapper.text()).toContain('采购入库')
    expect(wrapper.text()).toContain('通过')
    expect(wrapper.text()).toContain('2026-10-22')
    expect(wrapper.text()).toContain('办公设备采购')
    expect(wrapper.findAll('.view-tabs button').map(button => button.text())).toEqual(['审批报告'])

    await wrapper.get('.report-read-btn').trigger('click')
    await flushPromises()
    expect(mocks.markCCRead).toHaveBeenCalledWith('cc-1')
    expect(wrapper.find('.report-read-btn').exists()).toBe(false)
    wrapper.unmount()
  })

  it('没有审批报告权限时隐藏报告入口且不请求抄送 API', async () => {
    mocks.permissions = ['view_notifications']
    const wrapper = mount(NotificationList)
    await flushPromises()

    expect(mocks.fetchNotifications).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).not.toContain('审批报告')
    expect(mocks.getApprovalCCs).not.toHaveBeenCalled()
    expect(mocks.markCCRead).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('同时拥有两项权限时可切换列表，切换前不请求审批报告', async () => {
    mocks.permissions = ['view_notifications', 'view_approval_reports']
    const wrapper = mount(NotificationList)
    await flushPromises()

    expect(mocks.fetchNotifications).toHaveBeenCalledTimes(1)
    expect(mocks.getApprovalCCs).not.toHaveBeenCalled()
    await wrapper.get('.view-tabs button:nth-child(2)').trigger('click')
    await flushPromises()

    expect(mocks.getApprovalCCs).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.view-tabs button:nth-child(1)').attributes('aria-selected')).toBe('false')
    expect(wrapper.find('.view-tabs button:nth-child(2)').attributes('aria-selected')).toBe('true')
    wrapper.unmount()
  })
})
