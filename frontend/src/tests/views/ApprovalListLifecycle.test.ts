import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { push, getTransfers } = vi.hoisted(() => ({
  push: vi.fn(),
  getTransfers: vi.fn().mockResolvedValue({ data: { results: [] } }),
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/api/transfers', () => ({
  getTransfers,
  approveTransfer: vi.fn(),
  rejectTransfer: vi.fn(),
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ can: () => true }) }))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() }, ElMessageBox: {} }))

import ApprovalList from '@/views/mobile/ApprovalList.vue'

describe('移动端审批中心生命周期入口', () => {
  it('可从审批中心打开我的申请', async () => {
    const wrapper = mount(ApprovalList)
    await flushPromises()

    await wrapper.get('.my-applications-btn').trigger('click')

    expect(push).toHaveBeenCalledWith('/mobile/my-transfers')
  })

  it('归还历史待审批单不显示审批操作', async () => {
    getTransfers.mockResolvedValueOnce({ data: { results: [{
      id: 'return-pending', actionType: 'return', 审批状态: '待审批',
      createdAt: '2026-10-15T10:00:00Z', lines: [],
    }] } })
    const wrapper = mount(ApprovalList)
    await flushPromises()

    expect(wrapper.text()).toContain('归还')
    expect(wrapper.find('.card-actions').exists()).toBe(false)
  })
})
