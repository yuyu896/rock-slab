import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { branchSelectStub } from '../helpers/branchSelectStub'

const state = vi.hoisted(() => ({
  permissions: [] as string[],
  query: {} as Record<string, string>,
  getTransfer: vi.fn(),
  recoverAsset: vi.fn().mockResolvedValue({ data: { id: 'new-1' } }),
  updateTransfer: vi.fn().mockResolvedValue({ data: {} }),
  submitTransfer: vi.fn().mockResolvedValue({ data: {} }),
  resubmitTransfer: vi.fn().mockResolvedValue({ data: {} }),
  replace: vi.fn(),
  warning: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: {}, get query() { return state.query } }),
  useRouter: () => ({ replace: state.replace }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: state.warning },
}))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    profile: { name: '张三' },
    can: (code: string) => state.permissions.includes(code),
  }),
}))
vi.mock('@/api/transfers', () => ({
  getTransfer: state.getTransfer,
  recoverAsset: state.recoverAsset,
  updateTransfer: state.updateTransfer,
  submitTransfer: state.submitTransfer,
  resubmitTransfer: state.resubmitTransfer,
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] }),
}))
vi.mock('@/api/inventories', () => ({
  getInventoryReport: vi.fn(),
}))

import RecoveryCreate from '@/views/transfers/RecoveryCreate.vue'

const editorStub = {
  name: 'TransferLinesEditor',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  methods: { validate: () => true },
  template: '<div class="stub-editor" />',
}

function mountCreate() {
  return mount(RecoveryCreate, {
    global: { stubs: {
      TransferLinesEditor: editorStub as any,
      DepartmentSelect: { template: '<div />' },
      BranchSelect: branchSelectStub as any,
    } },
  })
}

beforeEach(() => {
  state.permissions = []
  state.query = {}
  state.getTransfer.mockReset().mockResolvedValue({ data: {
    id: 'r-1', 审批状态: '草稿', canEditDraft: true,
    回收去向: 'dispose', 调拨日期: '2026-10-22', 调出分公司: '北京分公司', lines: [],
  } })
  state.recoverAsset.mockClear()
  state.updateTransfer.mockClear()
  state.submitTransfer.mockClear()
  state.resubmitTransfer.mockClear()
  state.replace.mockClear()
  state.warning.mockClear()
})

describe('recovery destination permissions', () => {
  it('allows direct disposal as a recovery destination without a separate permission', async () => {
    state.permissions = ['view_recovery', 'edit_recovery', 'view_asset_ledger']
    const wrapper = mountCreate()
    await flushPromises()

    expect(wrapper.find('input[type="radio"][value="restock"]').exists()).toBe(true)
    const disposalChoice = wrapper.find('input[type="radio"][value="dispose"]')
    expect(disposalChoice.exists()).toBe(true)
    expect((disposalChoice.element as HTMLInputElement).disabled).toBe(false)
  })

  it('edits and submits an existing direct-disposal recovery using lifecycle permissions', async () => {
    state.permissions = ['view_recovery', 'edit_recovery', 'view_asset_ledger']
    state.query = { id: 'r-1' }
    state.getTransfer.mockResolvedValue({ data: {
      id: 'r-1', 审批状态: '草稿', canEditDraft: true,
      回收去向: 'dispose', 处置方式: '报废', 调拨日期: '2026-10-22', 调出分公司: '北京分公司',
      lines: [{ item: 'item-1', itemCode: 'IT-1', itemName: '测试品目', unit: '件', 数量: 1, instances: [] }],
    } })
    const wrapper = mountCreate()
    await flushPromises()

    const disposalChoice = wrapper.find('input[type="radio"][value="dispose"]')
    expect(disposalChoice.exists()).toBe(true)
    expect((disposalChoice.element as HTMLInputElement).disabled).toBe(false)
    expect((disposalChoice.element as HTMLInputElement).checked).toBe(true)

    await wrapper.findAll('button').find(button => button.text() === '保存并提交审批')!.trigger('click')
    await flushPromises()

    expect(state.warning).not.toHaveBeenCalled()
    expect(state.updateTransfer).toHaveBeenCalledWith('r-1', expect.objectContaining({ 回收去向: 'dispose' }))
    expect(state.submitTransfer).toHaveBeenCalledWith('r-1')
    expect(state.resubmitTransfer).not.toHaveBeenCalled()
    expect(state.recoverAsset).not.toHaveBeenCalled()
  })
})
