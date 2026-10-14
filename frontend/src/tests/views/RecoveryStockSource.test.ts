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
  getFixedAsset: vi.fn(),
  getFixedAssetTimeline: vi.fn(),
}))
vi.mock('@/api/transfers', () => ({
  getTransfer: vi.fn().mockResolvedValue({
    data: { id: 'r-1', 审批状态: '待审批', lines: [], 回收去向: 'restock' },
  }),
  getRecoveryLedger: vi.fn().mockResolvedValue({ data: {
    count: 0, disposal_income: 1500, results: [],
  } }),
  exportRecoveryLedger: vi.fn(),
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '测试分公司' }] }),
}))

import TransferLinesEditor from '@/views/transfers/components/TransferLinesEditor.vue'
import RecoveryDetail from '@/views/transfers/RecoveryDetail.vue'
import RecoveryLedger from '@/views/transfers/RecoveryLedger.vue'
import { getTransfer, getRecoveryLedger } from '@/api/transfers'
import { getFixedAsset, getFixedAssetTimeline } from '@/api/assets'

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

describe('物资处置台账处置收入合计卡', () => {
  it('按后端 snake_case 字段显示出售金额加总', async () => {
    const wrapper = mount(RecoveryLedger, {
      global: { stubs: { BasePagination: { template: '<div />' }, BranchFilterSelect: { template: '<div />' } } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('处置收入合计 ¥1500')
  })

  it('实例行打开只读档案和完整生平，数量行不提供实例入口', async () => {
    vi.mocked(getRecoveryLedger).mockResolvedValue({
      data: {
        count: 2,
        disposal_income: 500,
        results: [
          {
            日期: '2026-10-14', 单据编号: 'HS20261014-001', 分公司: '测试分公司',
            品目编号: 'DL-1', 品目名称: '电脑', 规格: '', 数量: 1, 内部编号: 'DL-1-1',
            处置方式: '出售', 处置金额: 500, 经办人: '张三', 备注: '',
            实例ID: 'fa-1', 单据ID: 'doc-1',
          },
          {
            日期: '2026-10-14', 单据编号: 'HS20261014-001', 分公司: '测试分公司',
            品目编号: 'DL-2', 品目名称: '办公桌', 规格: '', 数量: 5, 内部编号: '',
            处置方式: '报废', 处置金额: null, 经办人: '张三', 备注: '',
            实例ID: '', 单据ID: 'doc-1',
          },
        ],
      },
    } as any)
    vi.mocked(getFixedAsset).mockResolvedValue({
      data: {
        id: 'fa-1', 内部编号: 'DL-1-1', 当前状态: '退役', item_code: 'DL-1',
        item_name: '电脑', item: 'item-1', branch_name: '测试分公司',
        department_name: '测试部门', 序列号: '', createdAt: '', updatedAt: '',
      },
    } as any)
    vi.mocked(getFixedAssetTimeline).mockResolvedValue({
      data: {
        instance: {} as any, birth: null,
        timeline: [{
          transfer_id: 'doc-1', 单据编号: 'HS20261014-001', action_type: 'recovery',
          日期: '2026-10-14', 行号: 1, 品目编号: 'DL-1', 数量: 1,
          使用人: '', 部门: '', 本批规格: '', 审批状态: '已通过',
        }],
      },
    } as any)

    const wrapper = mount(RecoveryLedger, {
      global: { stubs: { BasePagination: { template: '<div />' }, BranchFilterSelect: { template: '<div />' } } },
    })
    await flushPromises()
    expect(wrapper.findAll('.asset-link')).toHaveLength(1)
    expect(wrapper.find('.asset-link').text()).toContain('查看')
    expect(wrapper.text()).toContain('DL-2')
    await wrapper.find('.asset-link').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('固定物资档案')
    expect(wrapper.text()).toContain('电脑')
    expect(wrapper.text()).toContain('测试分公司')
    expect(wrapper.text()).toContain('完整流转日志')
    expect(wrapper.text()).toContain('回收')
    expect(wrapper.text()).not.toContain('编辑实例')
    expect(wrapper.text()).not.toContain('保存')
    expect(getFixedAsset).toHaveBeenCalledWith('fa-1')
    expect(getFixedAssetTimeline).toHaveBeenCalledWith('fa-1')
  })

  it('生平读取失败时保留详情窗口并显示失败状态', async () => {
    vi.mocked(getRecoveryLedger).mockResolvedValue({
      data: {
        count: 1,
        disposal_income: 0,
        results: [{
          日期: '2026-10-14', 单据编号: 'HS20261014-002', 分公司: '测试分公司',
          品目编号: 'DL-1', 品目名称: '电脑', 规格: '', 数量: 1, 内部编号: 'DL-1-2',
          处置方式: '报废', 处置金额: null, 经办人: '张三', 备注: '',
          实例ID: 'fa-2', 单据ID: 'doc-2',
        }],
      },
    } as any)
    vi.mocked(getFixedAsset).mockResolvedValue({
      data: {
        id: 'fa-2', 内部编号: 'DL-1-2', 当前状态: '退役', item_code: 'DL-1',
        item_name: '电脑', item: 'item-1', branch_name: '测试分公司',
        序列号: '', createdAt: '', updatedAt: '',
      },
    } as any)
    vi.mocked(getFixedAssetTimeline).mockRejectedValue(new Error('生平接口暂不可用'))

    const wrapper = mount(RecoveryLedger, {
      global: { stubs: { BasePagination: { template: '<div />' }, BranchFilterSelect: { template: '<div />' } } },
    })
    await flushPromises()
    await wrapper.find('.asset-link').trigger('click')
    await flushPromises()

    expect(wrapper.find('.detail-dialog').exists()).toBe(true)
    expect(wrapper.text()).toContain('生平接口暂不可用')
    expect(wrapper.text()).toContain('生平记录未能加载')
    expect(wrapper.text()).toContain('DL-1-2')
  })
})
