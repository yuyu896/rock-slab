import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRoute: () => ({ query: {} }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ profile: { name: '张三' } }) }))
vi.mock('@/api/transfers', () => ({
  assignAsset: vi.fn().mockResolvedValue({ data: { id: 'a-1' } }),
  transferAsset: vi.fn().mockResolvedValue({ data: { id: 't-1' } }),
  getTransfers: vi.fn().mockResolvedValue({ data: { count: 0, next: null, previous: null, results: [] } }),
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [
    { id: 'b-1', name: '北京分公司' },
    { id: 'b-2', name: '上海分公司' },
  ] }),
}))

import AssignCreate from '@/views/transfers/AssignCreate.vue'
import TransferCreate from '@/views/transfers/TransferCreate.vue'
import PurchaseList from '@/views/transfers/PurchaseList.vue'
import AssignList from '@/views/transfers/AssignList.vue'
import TransferDetailLayout from '@/views/transfers/components/TransferDetailLayout.vue'
import { assignAsset, transferAsset, getTransfers } from '@/api/transfers'

const validDrafts = [{
  key: 1, item: { id: 'item-1' }, 数量: 2, 本批规格: '', 行供应商: '',
  单价: null, 金额: null, 使用人: '', department: null, 存放位置: '', instances: [],
}]

const editorStub = {
  name: 'TransferLinesEditor',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  methods: { validate: () => true },
  template: `<button class="stub-editor" @click="$emit('update:modelValue', drafts)" />`,
  data: () => ({ drafts: validDrafts }),
}

const branchFilterStub = {
  name: 'BranchFilterSelect',
  props: ['modelValue', 'options', 'allLabel'],
  emits: ['update:modelValue'],
  template: '<div class="stub-branch" />',
}

async function clickSubmit(wrapper: any) {
  await wrapper.findAll('button').find((b: any) => b.text() === '确定提交')!.trigger('click')
  await flushPromises()
}

describe('经办人统一：领用/调拨创建页预填当前登录人', () => {
  beforeEach(() => vi.clearAllMocks())

  it('AssignCreate 预填经办人且提交 payload 携带', async () => {
    const wrapper = mount(AssignCreate, {
      global: { stubs: { TransferLinesEditor: editorStub as any } },
    })
    await flushPromises()
    const handlerInput = wrapper.find('input[placeholder="默认创建人，选填"]')
    expect((handlerInput.element as HTMLInputElement).value).toBe('张三')

    await wrapper.find('input[type="date"]').setValue('2026-09-23')
    await wrapper.findAll('select.form-select').at(0)!.setValue('b-1')
    await wrapper.find('.stub-editor').trigger('click')
    await clickSubmit(wrapper)

    expect(assignAsset).toHaveBeenCalledTimes(1)
    expect(assignAsset).toHaveBeenCalledWith(expect.objectContaining({ 经办人: '张三' }))
  })

  it('TransferCreate 预填经办人且提交 payload 携带', async () => {
    const wrapper = mount(TransferCreate, {
      global: { stubs: { TransferLinesEditor: editorStub as any, DepartmentSelect: { template: '<div />' } } },
    })
    await flushPromises()
    const handlerInput = wrapper.find('input[placeholder="默认创建人，选填"]')
    expect((handlerInput.element as HTMLInputElement).value).toBe('张三')

    await wrapper.find('input[type="date"]').setValue('2026-09-23')
    const selects = wrapper.findAll('select.form-select')
    await selects.at(0)!.setValue('b-1')
    await selects.at(1)!.setValue('b-2')
    await wrapper.find('.stub-editor').trigger('click')
    await clickSubmit(wrapper)

    expect(transferAsset).toHaveBeenCalledTimes(1)
    expect(transferAsset).toHaveBeenCalledWith(expect.objectContaining({ 经办人: '张三' }))
  })
})

describe('经办人统一：列表列兜底显示（经办人空→创建人）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getTransfers).mockResolvedValue({
      data: {
        count: 2, next: null, previous: null,
        results: [
          { id: 'a', 审批状态: '待审批', 经办人: '王经办', 创建人: '李甲', lines: [] } as any,
          { id: 'b', 审批状态: '待审批', 经办人: '', 创建人: '李创建', lines: [] } as any,
        ],
      },
    } as any)
  })

  it('PurchaseList 经办人列：有值显值、空值兜底创建人', async () => {
    const wrapper = mount(PurchaseList, {
      global: { stubs: { BranchFilterSelect: branchFilterStub as any } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('王经办')
    expect(wrapper.text()).toContain('李创建')
    expect(wrapper.text()).not.toContain('李甲')
  })

  it('AssignList 经办人列：有值显值、空值兜底创建人', async () => {
    const wrapper = mount(AssignList, {
      global: { stubs: { BranchFilterSelect: branchFilterStub as any } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('王经办')
    expect(wrapper.text()).toContain('李创建')
    expect(wrapper.text()).not.toContain('李甲')
  })
})

describe('经办人统一：详情页 meta 区展示与兜底', () => {
  it('经办人空时 meta 显示创建人兜底值', () => {
    const wrapper = mount(TransferDetailLayout, {
      props: {
        title: '领用详情',
        backPath: '/transfers/assign',
        type: 'assign',
        doc: { 单据编号: 'LY001', 调拨日期: '2026-09-23', 创建人: '李创建', 审批状态: '待审批' } as any,
        loading: false,
      },
    })
    const metaRow = wrapper.find('.meta-row')
    expect(metaRow.text()).toContain('经办人')
    expect(metaRow.text()).toContain('李创建')
  })

  it('经办人有值时 meta 显示经办人', () => {
    const wrapper = mount(TransferDetailLayout, {
      props: {
        title: '领用详情',
        backPath: '/transfers/assign',
        type: 'assign',
        doc: { 单据编号: 'LY001', 调拨日期: '2026-09-23', 创建人: '李创建', 经办人: '王经办', 审批状态: '待审批' } as any,
        loading: false,
      },
    })
    const metaRow = wrapper.find('.meta-row')
    expect(metaRow.text()).toContain('王经办')
  })
})
