import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { getBranches, getCategories, getTransfer } = vi.hoisted(() => ({
  getBranches: vi.fn(),
  getCategories: vi.fn().mockResolvedValue({ data: [] }),
  getTransfer: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { id: 'assign-draft-1' } }),
  useRouter: () => ({ back: vi.fn() }),
}))
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn(), warning: vi.fn() } }))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ profile: { branch: 'branch-current' } }) }))
vi.mock('@/api/transfers', () => ({
  getTransfer,
  resubmitTransfer: vi.fn(),
  submitTransfer: vi.fn(),
  assignAsset: vi.fn(),
  updateTransfer: vi.fn(),
}))
vi.mock('@/api/categories', () => ({ getCategories, lookupCategoryByCode: vi.fn() }))
vi.mock('@/api/branches', () => ({ getBranches }))

import MobileAssign from '@/views/mobile/MobileAssign.vue'

describe('MobileAssign 草稿编辑', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCategories.mockResolvedValue({ data: [] })
    getTransfer.mockResolvedValue({ data: {
      id: 'assign-draft-1',
      canEditDraft: true,
      审批状态: '草稿',
      from_branch: 'branch-original',
      lines: [{ itemCode: 'AST-001', itemName: '测试物资' }],
    } })
  })

  it('分公司选项异步加载完成后保留草稿原所属分公司', async () => {
    let resolveBranches: ((value: { data: { id: string; name: string }[] }) => void) | undefined
    getBranches.mockImplementation(() => new Promise((resolve) => { resolveBranches = resolve }))
    const wrapper = mount(MobileAssign)
    await flushPromises()

    resolveBranches?.({ data: [
      { id: 'branch-original', name: '原分公司' },
      { id: 'branch-current', name: '当前分公司' },
    ] })
    await flushPromises()

    const branchSelect = wrapper.find('select.form-select')
    expect((branchSelect.element as HTMLSelectElement).value).toBe('branch-original')
  })
})
