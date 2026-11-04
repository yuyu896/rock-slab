import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { branchSelectStub } from '../helpers/branchSelectStub'

const state = vi.hoisted(() => ({
  permissions: [] as string[],
  query: {} as Record<string, string>,
  purchaseAsset: vi.fn().mockResolvedValue({ data: { id: 'new-1' } }),
  getTransfer: vi.fn(),
  updateTransfer: vi.fn().mockResolvedValue({ data: {} }),
  submitTransfer: vi.fn().mockResolvedValue({ data: {} }),
  resubmitTransfer: vi.fn().mockResolvedValue({ data: {} }),
  replace: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: {}, get query() { return state.query } }),
  useRouter: () => ({ replace: state.replace }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock('@/store/user', () => ({
  useUserStore: () => ({
    profile: { name: '张三' },
    can: (code: string) => state.permissions.includes(code),
  }),
}))
vi.mock('@/api/transfers', () => ({
  getTransfer: state.getTransfer,
  purchaseAsset: state.purchaseAsset,
  updateTransfer: state.updateTransfer,
  submitTransfer: state.submitTransfer,
  resubmitTransfer: state.resubmitTransfer,
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] }),
}))

import PurchaseCreate from '@/views/transfers/PurchaseCreate.vue'

const editorStub = {
  name: 'TransferLinesEditor',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  methods: { validate: () => true },
  template: '<button class="stub-editor" @click="$emit(\'update:modelValue\', drafts)" />',
  data: () => ({ drafts: [{
    key: 1,
    item: { id: 'item-1' },
    数量: 1,
    本批规格: '',
    行供应商: '',
    单价: null,
    金额: null,
    使用人: '',
    department: null,
    存放位置: '',
    instances: [],
  }] }),
}

function mountCreate() {
  return mount(PurchaseCreate, {
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
    id: 't-1', 审批状态: '草稿', canEditDraft: true, 调拨日期: '2026-09-22', lines: [],
  } })
  state.purchaseAsset.mockClear()
  state.updateTransfer.mockClear()
  state.submitTransfer.mockClear()
  state.resubmitTransfer.mockClear()
  state.replace.mockClear()
})

describe('采购入库编辑权限', () => {
  it('编辑权限需要采购查看和品目查看前置，满足后可保存草稿并提交', async () => {
    state.permissions = ['edit_purchase', 'view_purchase', 'view_categories']
    const wrapper = mountCreate()
    await flushPromises()

    expect(wrapper.find('.btn-draft').exists()).toBe(true)
    expect(wrapper.find('.btn-confirm').exists()).toBe(true)

    await wrapper.find('input[type="date"]').setValue('2026-09-23')
    await wrapper.find('select.form-select').setValue('b-1')
    await wrapper.find('.stub-editor').trigger('click')
    await wrapper.find('.btn-draft').trigger('click')
    await flushPromises()
    expect(state.purchaseAsset).toHaveBeenCalledWith(expect.objectContaining({ draft: true }))
  })

  it('编辑权限可以保存已有草稿并提交修改', async () => {
    state.permissions = ['edit_purchase', 'view_purchase', 'view_categories']
    state.query = { id: 't-1' }
    const wrapper = mountCreate()
    await flushPromises()

    expect(wrapper.find('.btn-confirm').exists()).toBe(true)
    await wrapper.find('input[type="date"]').setValue('2026-09-23')
    await wrapper.find('select.form-select').setValue('b-1')
    await wrapper.find('.stub-editor').trigger('click')
    await wrapper.find('.btn-confirm').trigger('click')
    await flushPromises()

    expect(state.updateTransfer).toHaveBeenCalledWith('t-1', expect.any(Object))
    expect(state.submitTransfer).toHaveBeenCalledWith('t-1')
    expect(state.resubmitTransfer).not.toHaveBeenCalled()
  })

  it('只有查看权限时不开放编辑或创建操作', async () => {
    state.permissions = ['view_purchase', 'view_categories']
    const wrapper = mountCreate()
    await flushPromises()

    expect(wrapper.find('.btn-draft').exists()).toBe(false)
    expect(wrapper.find('.btn-confirm').exists()).toBe(false)
    expect(state.purchaseAsset).not.toHaveBeenCalled()
  })

  it('编辑权限缺少品目查看前置时不开放采购创建操作', async () => {
    state.permissions = ['edit_purchase', 'view_purchase']
    const wrapper = mountCreate()
    await flushPromises()

    expect(wrapper.find('.btn-draft').exists()).toBe(false)
    expect(wrapper.find('.btn-confirm').exists()).toBe(false)
    expect(state.purchaseAsset).not.toHaveBeenCalled()
  })

  it('编辑权限缺少采购单查看前置时不开放采购创建操作', async () => {
    state.permissions = ['edit_purchase', 'view_categories']
    const wrapper = mountCreate()
    await flushPromises()

    expect(wrapper.find('.btn-draft').exists()).toBe(false)
    expect(wrapper.find('.btn-confirm').exists()).toBe(false)
    expect(state.purchaseAsset).not.toHaveBeenCalled()
  })
})
