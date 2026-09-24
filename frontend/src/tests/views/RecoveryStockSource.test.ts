import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'r-1' }, query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}))
vi.mock('@/api/assets', () => ({
  getAssetStocks: vi.fn().mockResolvedValue({ data: { count: 1, results: [{
    item: 'item-1', 在库数量: 2, 在用数量: 0,
  }] } }),
}))
vi.mock('@/api/transfers', () => ({
  getTransfer: vi.fn().mockResolvedValue({
    data: { id: 'r-1', 审批状态: '待审批', lines: [], 回收去向: 'restock' },
  }),
  getRecoveryLedger: vi.fn().mockResolvedValue({ data: {
    count: 0, disposalIncome: 1500, results: [],
  } }),
  exportRecoveryLedger: vi.fn(),
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '测试分公司' }] }),
}))

import TransferLinesEditor from '@/views/transfers/components/TransferLinesEditor.vue'
import RecoveryDetail from '@/views/transfers/RecoveryDetail.vue'
import RecoveryLedger from '@/views/transfers/RecoveryLedger.vue'
import { getTransfer } from '@/api/transfers'

const qtyDraft: any = {
  key: 1, item: { id: 'item-1', asset_code: 'DESK-1', asset_name: '办公桌', managementType: 'quantity' },
  数量: 5, 本批规格: '', 行供应商: '', 单价: null, 金额: null,
  使用人: '', department: null, 存放位置: '', instances: [],
}

function mountEditor(dest: 'restock' | 'dispose', drafts: any[] = [qtyDraft]) {
  const wrapper = mount(TransferLinesEditor, {
    props: {
      modelValue: drafts,
      type: 'recovery' as any,
      branchName: '',
      recoveryDest: dest,
    },
    global: {
      stubs: {
        ItemPicker: { props: ['modelValue', 'branch', 'stockColumn'], template: '<div class="stub-item" />' },
        InstancePicker: { props: ['modelValue', 'itemCode', 'status'], template: '<div class="stub-inst" />' },
      },
    },
  })
  return wrapper.vm as any
}

describe('回收去向分流：行校验', () => {
  beforeEach(() => vi.clearAllMocks())

  it('重新入库 + 数量品行 → 拒绝并提示无重新入库概念', () => {
    const vm = mountEditor('restock')
    expect(vm.validate()).toBe(false)
    expect(vm.validateMessage).toContain('数量品物无重新入库概念')
  })

  it('处置 + 数量品行（台账缓存未知）→ 软预检放行（终检在后端）', () => {
    const vm = mountEditor('dispose')
    expect(vm.validate()).toBe(true)
  })

  it('处置 + 数量超在库 → 拒绝并提示当前在库', async () => {
    const wrapper = mount(TransferLinesEditor, {
      props: { modelValue: [qtyDraft], type: 'recovery' as any, branchName: '', recoveryDest: 'dispose' },
      global: {
        stubs: {
          ItemPicker: { props: ['modelValue'], template: '<div />' },
          InstancePicker: { props: ['modelValue'], template: '<div />' },
        },
      },
    })
    await wrapper.setProps({ branchName: '测试分公司' })
    await flushPromises()
    const vm = wrapper.vm as any
    expect(vm.validate()).toBe(false)
    expect(vm.validateMessage).toContain('超出当前在库 2')
    expect(vm.validateMessage).toContain('归还单')
  })
})

describe('回收详情去向三态展示', () => {
  beforeEach(() => vi.clearAllMocks())

  async function mountDetail(dest: string) {
    vi.mocked(getTransfer).mockResolvedValue({
      data: { id: 'r-1', 审批状态: '待审批', lines: [], 回收去向: dest } as any,
    } as any)
    const wrapper = mount(RecoveryDetail, {
      global: {
        stubs: {
          TransferDetailLayout: {
            name: 'TransferDetailLayout',
            props: ['title', 'type', 'doc', 'loading'],
            template: '<div><slot v-if="doc" name="extra-view" :doc="doc" /></div>',
          },
        },
      },
    })
    await flushPromises()
    return wrapper
  }

  it('restock 显示「重新入库」（修复前误显「入回收库」）', async () => {
    const wrapper = await mountDetail('restock')
    expect(wrapper.text()).toContain('重新入库')
    expect(wrapper.text()).not.toContain('入回收库')
  })

  it('dispose 显示「直接处置」', async () => {
    const wrapper = await mountDetail('dispose')
    expect(wrapper.text()).toContain('直接处置')
  })

  it('存量 recycle_bin 显示「入回收库」', async () => {
    const wrapper = await mountDetail('recycle_bin')
    expect(wrapper.text()).toContain('入回收库')
  })
})

describe('回收台账处置收入合计卡', () => {
  it('页头显示当前筛选口径的出售金额加总', async () => {
    const wrapper = mount(RecoveryLedger, {
      global: { stubs: { BasePagination: { template: '<div />' }, BranchFilterSelect: { template: '<div />' } } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('处置收入合计 ¥1500')
  })
})
