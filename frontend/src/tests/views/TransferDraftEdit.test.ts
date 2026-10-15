import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { getBranches, getTransfer, getUsers, updateTransfer, submitTransfer, transferAsset } = vi.hoisted(() => ({
  getBranches: vi.fn().mockResolvedValue({ data: [
    { id: 'branch-from', name: '调出分公司' },
    { id: 'branch-to', name: '调入分公司' },
  ] }),
  getTransfer: vi.fn().mockResolvedValue({ data: {
    id: 'transfer-draft-1',
    canEditDraft: true,
    actionType: 'transfer',
    审批状态: '草稿',
    调拨日期: '2026-10-15',
    from_branch: 'branch-from',
    to_branch: 'branch-to',
    调出分公司: '调出分公司',
    调入分公司: '调入分公司',
    调入负责人: '员工乙',
    经办人: '创建人',
    lines: [{
      item: 'item-1', itemCode: 'AST-001', itemName: '测试物资',
      数量: 1, instances: [],
    }],
  } }),
  getUsers: vi.fn().mockResolvedValue({ data: [{ id: 'user-2', name: '员工乙' }] }),
  updateTransfer: vi.fn().mockResolvedValue({ data: {} }),
  submitTransfer: vi.fn().mockResolvedValue({ data: {} }),
  transferAsset: vi.fn().mockResolvedValue({ data: {} }),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { id: 'transfer-draft-1' } }),
  useRouter: () => ({ replace: vi.fn() }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ profile: { name: '创建人' } }) }))
vi.mock('@/api/transfers', () => ({ getTransfer, updateTransfer, submitTransfer, transferAsset }))
vi.mock('@/api/branches', () => ({ getBranches }))
vi.mock('@/api/users', () => ({ getUsers }))

import TransferCreate from '@/views/transfers/TransferCreate.vue'

describe('TransferCreate 草稿编辑', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getTransfer.mockResolvedValue({ data: {
      id: 'transfer-draft-1',
      canEditDraft: true,
      actionType: 'transfer',
      审批状态: '草稿',
      调拨日期: '2026-10-15',
      from_branch: 'branch-from',
      to_branch: 'branch-to',
      调出分公司: '调出分公司',
      调入分公司: '调入分公司',
      调入负责人: '员工乙',
      经办人: '创建人',
      lines: [{ item: 'item-1', itemCode: 'AST-001', itemName: '测试物资', 数量: 1, instances: [] }],
    } })
  })

  it('读取并重提草稿时保留调入负责人', async () => {
    const wrapper = mount(TransferCreate, {
      global: {
        stubs: {
          TransferLinesEditor: { methods: { validate: () => true }, template: '<div />' },
          DepartmentSelect: { template: '<div />' },
        },
      },
    })
    await flushPromises()

    const responsibleSelect = wrapper.findAll('select.form-select').at(2)!
    expect((responsibleSelect.element as HTMLSelectElement).value).toBe('员工乙')

    await wrapper.get('.btn-confirm').trigger('click')
    await flushPromises()

    expect(updateTransfer).toHaveBeenCalledWith(
      'transfer-draft-1',
      expect.objectContaining({ 调入负责人: '员工乙' }),
    )
    expect(submitTransfer).toHaveBeenCalledWith('transfer-draft-1')
  })

  it('详情未获准编辑时不允许误提交为新单据', async () => {
    getTransfer.mockResolvedValueOnce({ data: { id: 'transfer-draft-1', canEditDraft: false, 审批状态: '草稿' } })
    const wrapper = mount(TransferCreate, {
      global: {
        stubs: {
          TransferLinesEditor: { methods: { validate: () => true }, template: '<div />' },
          DepartmentSelect: { template: '<div />' },
        },
      },
    })
    await flushPromises()

    await wrapper.get('.btn-confirm').trigger('click')
    await flushPromises()

    expect(transferAsset).not.toHaveBeenCalled()
    expect(updateTransfer).not.toHaveBeenCalled()
  })

  it('详情加载失败时不允许编辑路由退化为新建单据', async () => {
    getTransfer.mockRejectedValueOnce(new Error('network error'))
    const wrapper = mount(TransferCreate, {
      global: {
        stubs: {
          TransferLinesEditor: { methods: { validate: () => true }, template: '<div />' },
          DepartmentSelect: { template: '<div />' },
        },
      },
    })
    await flushPromises()

    await wrapper.get('.btn-confirm').trigger('click')
    await flushPromises()

    expect(transferAsset).not.toHaveBeenCalled()
    expect(updateTransfer).not.toHaveBeenCalled()
  })
})
