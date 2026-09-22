import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 't-1' }, query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn().mockResolvedValue('confirm'), prompt: vi.fn() },
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ profile: { name: '张三' } }) }))
vi.mock('@/api/transfers', () => ({
  purchaseAsset: vi.fn().mockResolvedValue({ data: { id: 'new-1' } }),
  getTransfer: vi.fn().mockResolvedValue({
    data: {
      id: 't-1', 审批状态: '待审批', canWithdraw: true, 创建人: '张三',
      调拨日期: '2026-09-22', lines: [],
    },
  }),
  updateTransfer: vi.fn(),
  resubmitTransfer: vi.fn(),
  submitTransfer: vi.fn(),
  withdrawTransfer: vi.fn().mockResolvedValue({ data: {} }),
  getTransfers: vi.fn(),
  exportTransfers: vi.fn(),
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] }),
}))

import PurchaseCreate from '@/views/transfers/PurchaseCreate.vue'
import PurchaseDetail from '@/views/transfers/PurchaseDetail.vue'
import PurchaseList from '@/views/transfers/PurchaseList.vue'
import { purchaseAsset, getTransfer, withdrawTransfer, getTransfers } from '@/api/transfers'

const validDrafts = [{
  key: 1, item: { id: 'item-1' }, 数量: 2, 本批规格: '', 行供应商: '甲供应商',
  单价: null, 金额: null, 使用人: '', department: null, 存放位置: '', instances: [],
}]

const editorStub = {
  name: 'TransferLinesEditor',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  methods: { validate: () => true },
  template: '<button class="stub-editor" @click="$emit(\'update:modelValue\', drafts)" />',
  data: () => ({ drafts: validDrafts }),
}

const layoutStub = {
  name: 'TransferDetailLayout',
  props: ['title', 'type', 'doc', 'loading'],
  template: '<div><slot v-if="doc" name="footer" :doc="doc" /></div>',
}

async function fillCreateForm(wrapper: any) {
  await wrapper.find('input[type="date"]').setValue('2026-09-22')
  await wrapper.findAll('select.form-select').at(-1)!.setValue('b-1')
  await wrapper.find('.stub-editor').trigger('click')
  await flushPromises()
}

describe('PurchaseCreate 存为草稿', () => {
  beforeEach(() => vi.clearAllMocks())

  it('点「存为草稿」以 draft=true 提交', async () => {
    const wrapper = mount(PurchaseCreate, {
      global: { stubs: { TransferLinesEditor: editorStub as any, DepartmentSelect: { template: '<div />' } } },
    })
    await flushPromises()
    await fillCreateForm(wrapper as any)
    await wrapper.findAll('button').find(b => b.text() === '存为草稿')!.trigger('click')
    await flushPromises()
    expect(purchaseAsset).toHaveBeenCalledWith(expect.objectContaining({ draft: true }))
  })

  it('点「提交审批」不带 draft 标志', async () => {
    const wrapper = mount(PurchaseCreate, {
      global: { stubs: { TransferLinesEditor: editorStub as any, DepartmentSelect: { template: '<div />' } } },
    })
    await flushPromises()
    await fillCreateForm(wrapper as any)
    await wrapper.findAll('button').find(b => b.text() === '确定提交')!.trigger('click')
    await flushPromises()
    const payload = vi.mocked(purchaseAsset).mock.calls[0][0] as Record<string, unknown>
    expect(payload.draft).toBeUndefined()
  })
})

describe('PurchaseDetail 撤回直达编辑', () => {
  beforeEach(() => vi.clearAllMocks())

  it('撤回成功后自动进入编辑态', async () => {
    const wrapper = mount(PurchaseDetail, {
      global: { stubs: { TransferDetailLayout: layoutStub as any, TransferLinesEditor: { template: '<div />' } } },
    })
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text() === '撤回')!.trigger('click')
    await flushPromises()
    expect(withdrawTransfer).toHaveBeenCalledWith('t-1')
    expect(getTransfer).toHaveBeenCalledTimes(2) // 初次加载 + 撤回后刷新
    expect(wrapper.text()).toContain('保存并提交')
  })
})

describe('PurchaseList 草稿统计卡', () => {
  beforeEach(() => vi.clearAllMocks())

  it('当前页草稿数显示在统计卡', async () => {
    vi.mocked(getTransfers).mockResolvedValue({
      data: {
        count: 3, next: null, previous: null,
        results: [
          { id: 'a', 审批状态: '草稿', lines: [] } as any,
          { id: 'b', 审批状态: '草稿', lines: [] } as any,
          { id: 'c', 审批状态: '已入库', lines: [] } as any,
        ],
      },
    } as any)
    const wrapper = mount(PurchaseList, {
      global: { stubs: { BranchFilterSelect: { template: '<div />' } } },
    })
    await flushPromises()
    expect(wrapper.find('.stat-card.draft .stat-value').text()).toBe('2')
  })
})
