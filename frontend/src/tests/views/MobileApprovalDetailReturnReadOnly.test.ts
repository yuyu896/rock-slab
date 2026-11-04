import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  back: vi.fn(),
  push: vi.fn(),
  getTransfer: vi.fn().mockResolvedValue({ data: {
    id: 'return-pending', actionType: 'return', 审批状态: '待审批',
    调拨日期: '2026-10-15', 创建人: '申请人', createdAt: '2026-10-15T10:00:00Z', lines: [],
  } }),
  approveTransfer: vi.fn(),
  rejectTransfer: vi.fn(),
  confirm: vi.fn(),
  prompt: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ back: mocks.back, push: mocks.push }),
  useRoute: () => ({ params: { id: 'return-pending' } }),
}))
vi.mock('@/api/transfers', () => ({
  getTransfer: mocks.getTransfer,
  approveTransfer: mocks.approveTransfer,
  rejectTransfer: mocks.rejectTransfer,
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ can: () => true }) }))
vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
  ElMessageBox: { confirm: mocks.confirm, prompt: mocks.prompt },
}))

import MobileApprovalDetail from '@/views/mobile/ApprovalDetail.vue'

describe('移动端归还历史审批详情', () => {
  it('即使旧权限仍返回 true，也不显示审批入口', async () => {
    const wrapper = mount(MobileApprovalDetail)
    await flushPromises()

    expect(wrapper.text()).toContain('归还')
    expect(wrapper.find('.action-section').exists()).toBe(false)
    expect(mocks.approveTransfer).not.toHaveBeenCalled()
    expect(mocks.rejectTransfer).not.toHaveBeenCalled()
  })
})
