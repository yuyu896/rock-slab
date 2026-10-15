import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { getBranches, getCategories, getTransfer } = vi.hoisted(() => ({
  getBranches: vi.fn(),
  getCategories: vi.fn().mockResolvedValue({ data: [] }),
  getTransfer: vi.fn().mockResolvedValue({ data: {
    id: 'transfer-draft-1',
    actionType: 'transfer',
    canEditDraft: true,
    审批状态: '草稿',
    调拨日期: '2026-10-15',
    from_branch: 'branch-old',
    to_branch: 'branch-target',
    调出分公司: '旧调出方',
    调入分公司: '调入方',
    lines: [{ itemCode: 'AST-001', itemName: '测试物资', 数量: 1 }],
  } }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { id: 'transfer-draft-1' } }),
  useRouter: () => ({ back: vi.fn() }),
}))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), warning: vi.fn() } }))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ profile: { branch: 'branch-current' } }) }))
vi.mock('@/api/transfers', () => ({
  getTransfer,
  resubmitTransfer: vi.fn(),
  submitTransfer: vi.fn(),
  transferAsset: vi.fn(),
  updateTransfer: vi.fn(),
}))
vi.mock('@/api/categories', () => ({ getCategories, lookupCategoryByCode: vi.fn() }))
vi.mock('@/api/branches', () => ({ getBranches }))

import MobileTransfer from '@/views/mobile/MobileTransfer.vue'

describe('MobileTransfer 草稿编辑', () => {
  it('选项异步加载结束后仍保留单据原调出分公司', async () => {
    const pendingBranchLoads: ((value: { data: { id: string; name: string }[] }) => void)[] = []
    getBranches.mockImplementation(() => new Promise((resolve) => pendingBranchLoads.push(resolve)))
    const wrapper = mount(MobileTransfer)
    await flushPromises()

    expect(pendingBranchLoads).toHaveLength(2)
    for (const resolve of pendingBranchLoads) {
      resolve({ data: [
        { id: 'branch-old', name: '旧调出方' },
        { id: 'branch-current', name: '当前分公司' },
        { id: 'branch-target', name: '调入方' },
      ] })
    }
    await flushPromises()

    const fromBranch = wrapper.findAll('select.form-select').at(0)!
    expect((fromBranch.element as HTMLSelectElement).value).toBe('branch-old')
  })
})
