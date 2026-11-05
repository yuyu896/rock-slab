import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const mocks = vi.hoisted(() => ({
  assignAsset: vi.fn(),
  getTransfer: vi.fn(),
  getBranches: vi.fn(),
  getCategories: vi.fn(),
  lookupCategoryByCode: vi.fn(),
  lookupAvailableTransferItem: vi.fn(),
  routeQuery: {} as Record<string, string>,
  routerReplace: vi.fn(),
  can: vi.fn((_code: string) => true),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: mocks.routeQuery }),
  useRouter: () => ({ back: vi.fn(), replace: mocks.routerReplace }),
}))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ profile: { branch: 'b-1', name: '张三' }, can: mocks.can }) }))
vi.mock('@/api/transfers', () => ({
  assignAsset: mocks.assignAsset,
  getTransfer: mocks.getTransfer,
  resubmitTransfer: vi.fn(),
  submitTransfer: vi.fn(),
  updateTransfer: vi.fn(),
}))
vi.mock('@/api/categories', () => ({
  lookupCategoryByCode: mocks.lookupCategoryByCode,
  getCategories: mocks.getCategories,
}))
vi.mock('@/api/branches', () => ({ getBranches: mocks.getBranches }))
vi.mock('@/api/assets', () => ({ lookupAvailableTransferItem: mocks.lookupAvailableTransferItem }))

import MobileAssign from '@/views/mobile/MobileAssign.vue'

describe('移动端领用备注', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.keys(mocks.routeQuery).forEach((key) => delete mocks.routeQuery[key])
    mocks.can.mockReturnValue(true)
    mocks.assignAsset.mockResolvedValue({ data: { id: 'assign-1' } })
    mocks.getBranches.mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] })
    mocks.getCategories.mockResolvedValue({ data: [] })
    mocks.lookupCategoryByCode.mockResolvedValue({ data: { id: 'item-1' } })
    mocks.lookupAvailableTransferItem.mockResolvedValue('item-1')
  })

  it('不显示用途并将备注提交到唯一明细行，不发单头备注', async () => {
    const wrapper = mount(MobileAssign)
    await flushPromises()

    await wrapper.find('input[placeholder="请输入资产编号"]').setValue('NB-001')
    await wrapper.find('textarea[placeholder="请输入设备备注"]').setValue('贴资产标签')
    await wrapper.find('.submit-btn').trigger('click')
    await flushPromises()

    expect(mocks.assignAsset).toHaveBeenCalledTimes(1)
    expect(mocks.lookupAvailableTransferItem).toHaveBeenCalledWith('北京分公司', 'NB-001')
    const payload = mocks.assignAsset.mock.calls[0][0]
    expect(payload).not.toHaveProperty('调出部门')
    expect(payload).not.toHaveProperty('用途')
    expect(payload).not.toHaveProperty('备注')
    expect(payload.items).toEqual([expect.objectContaining({ 备注: '贴资产标签' })])
    expect(payload.items[0]).not.toHaveProperty('用途')
    expect(wrapper.text()).not.toContain('用途')
    expect(wrapper.find('textarea[placeholder="请输入设备备注"]').attributes('rows')).toBe('1')
  })

  it('编辑多行单据时转到完整领用编辑页，避免只保存首行', async () => {
    mocks.routeQuery.id = 'assign-multi'
    mocks.getTransfer.mockResolvedValue({
      data: {
        canEditDraft: true,
        审批状态: '草稿',
        lines: [{ id: 'line-1' }, { id: 'line-2' }],
      },
    })

    mount(MobileAssign)
    await flushPromises()

    expect(mocks.routerReplace).toHaveBeenCalledWith({
      path: '/transfers/assign/create',
      query: { id: 'assign-multi' },
    })
  })

  it('编辑权限和模块及台账查看权限齐全时显示草稿和直接提交', async () => {
    mocks.can.mockImplementation((code) => ['edit_assignment', 'view_assignment', 'view_asset_ledger'].includes(code))

    const wrapper = mount(MobileAssign)
    await flushPromises()

    expect(wrapper.find('.draft-btn').exists()).toBe(true)
    expect(wrapper.find('.submit-btn').exists()).toBe(true)
  })

  it('缺少台账查看前置时不显示建单操作', async () => {
    mocks.can.mockImplementation((code) => code === 'edit_assignment')

    const wrapper = mount(MobileAssign)
    await flushPromises()

    expect(wrapper.find('.draft-btn').exists()).toBe(false)
    expect(wrapper.find('.submit-btn').exists()).toBe(false)
  })

  it('缺少领用单查看权时仅凭编辑和台账查看权限不显示写操作', async () => {
    mocks.can.mockImplementation((code) => ['edit_assignment', 'view_asset_ledger'].includes(code))

    const wrapper = mount(MobileAssign)
    await flushPromises()

    expect(wrapper.find('.draft-btn').exists()).toBe(false)
    expect(wrapper.find('.submit-btn').exists()).toBe(false)
  })
})
