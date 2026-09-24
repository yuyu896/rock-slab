import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
  ElDialog: {
    name: 'ElDialog',
    props: ['modelValue', 'title', 'width', 'top', 'closeOnClickModal'],
    template: '<div v-if="modelValue" class="el-dialog-stub"><slot /><template #footer><slot name="footer" /></template></div>',
  },
  ElButton: { name: 'ElButton', props: ['type', 'loading', 'size'], template: '<button class="el-btn-stub"><slot /></button>' },
}))
vi.mock('@/hooks/usePermission', () => ({ usePermission: () => ({ can: () => true, canSupplement: { value: true } }) }))
vi.mock('@/api/assets', () => ({
  getFixedAssets: vi.fn().mockResolvedValue({ data: { count: 3, next: null, previous: null, results: [
    { id: 'i-1', 内部编号: 'X-1', 序列号: 'S1', branchName: '北京分公司', 当前状态: '在库', itemCode: 'X', itemName: '笔记本', createdAt: '', updatedAt: '' },
    { id: 'i-2', 内部编号: 'X-2', 序列号: '', branchName: '北京分公司', 当前状态: '在库', itemCode: 'X', itemName: '笔记本', createdAt: '', updatedAt: '' },
    { id: 'i-3', 内部编号: 'X-3', 序列号: 'S3', branchName: '北京分公司', 当前状态: '在库', itemCode: 'X', itemName: '笔记本', createdAt: '', updatedAt: '' },
  ] } }),
  exportFixedAssets: vi.fn(),
  getFixedAssetTimeline: vi.fn().mockResolvedValue({ data: {
    birth: { 供应商: '甲', 采购日期: '2026-01-01' },
    timeline: [
      { transferId: 't-1', 行号: 1, 日期: '2026-02-01', 单据编号: 'LY001', actionType: 'assign', 使用人: '张三', 审批状态: '已通过' },
      { transferId: 't-2', 行号: 1, 日期: '2026-03-01', 单据编号: 'HS001', actionType: 'weird_legacy', 使用人: '', 审批状态: '已通过' },
    ],
  } }),
  uploadFixedAssetImage: vi.fn(),
  deleteFixedAssetImage: vi.fn(),
  batchUpdateFixedAssets: vi.fn(),
}))
vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b-1', name: '北京分公司' }] }),
}))
vi.mock('@/api/suppliers', () => ({
  getSuppliers: vi.fn().mockResolvedValue({ data: [] }),
}))
vi.mock('@/utils/request', () => ({ handleApiError: (e: unknown) => String(e) }))

import InstancePicker from '@/components/InstancePicker.vue'
import TransferLinesEditor from '@/views/transfers/components/TransferLinesEditor.vue'
import BranchFilterSelect from '@/components/BranchFilterSelect.vue'
import { TRANSFER_TYPES } from '@/constants'

const instItem: any = {
  id: 'item-1', asset_code: 'X', asset_name: '笔记本电脑', managementType: 'instance',
}

describe('InstancePicker 单选模式（点选即定）', () => {
  beforeEach(() => vi.clearAllMocks())

  async function mountPicker(modelValue: string[] = [], excludedIds: string[] = []) {
    const wrapper = mount(InstancePicker, {
      props: {
        itemCode: 'X', status: '在库', branchName: '北京分公司',
        modelValue, excludedIds,
        expanded: false,
      },
    })
    await wrapper.setProps({ expanded: true }) // 切换触发加载（组件靠父级切换驱动）
    await flushPromises()
    return wrapper
  }

  it('无勾选框与「完成」按钮（多选退役）', async () => {
    const wrapper = await mountPicker()
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false)
    expect(wrapper.find('.picker-done').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('完成')
  })

  it('点选即定：单台上行并收起面板', async () => {
    const wrapper = await mountPicker()
    await wrapper.findAll('.picker-row')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')![0]).toEqual([['i-1']])
    const expandedCalls = wrapper.emitted('update:expanded')!
    expect(expandedCalls[expandedCalls.length - 1]).toEqual([false])
  })

  it('跨行去重：他行已选实例不在候选，本行已选保留高亮', async () => {
    const wrapper = await mountPicker(['i-1'], ['i-2'])
    const codes = wrapper.findAll('.row-code').map((r) => r.text())
    expect(codes).toContain('X-1')  // 本行已选保留（高亮回显）
    expect(codes).not.toContain('X-2')  // 他行已选剔除
    expect(wrapper.findAll('.picker-row.picked').length).toBe(1)
  })

  it('已选高亮回显（本行已选保留在候选）', async () => {
    const wrapper = await mountPicker(['i-1'], ['i-1'])
    expect(wrapper.findAll('.picker-row.picked').length).toBe(1)
  })
})

describe('TransferLinesEditor 一行一台', () => {
  it('单选回调后实例 1 台、数量 1；single 属性已退役', async () => {
    const draft: any = {
      key: 1, item: instItem, 数量: 1, 本批规格: '', 行供应商: '',
      单价: null, 金额: null, 使用人: '', department: null, 存放位置: '', instances: [],
    }
    const wrapper = mount(TransferLinesEditor, {
      props: { modelValue: [draft], type: 'recovery' as any, branchName: '北京分公司', recoveryDest: 'dispose' },
      global: { stubs: { ItemPicker: { props: ['modelValue'], template: '<div />' } } },
    })
    await flushPromises()
    const picker = wrapper.findComponent({ name: 'InstancePicker' })
    expect(picker.exists()).toBe(true)
    expect(picker.props('single')).toBeUndefined()
    picker.vm.$emit('change', [{ id: 'i-2', 内部编号: 'X-2' }])
    await flushPromises()
    expect(draft.instances.length).toBe(1)
    expect(draft.数量).toBe(1)
    expect(draft.instances[0].code).toBe('X-2')
  })
})

describe('生平类型中文标签', () => {
  it('TRANSFER_TYPES 五类中文标签齐备（映射源）', () => {
    const labels = Object.values(TRANSFER_TYPES).map((t) => t.label)
    expect(labels).toEqual(['采购入库', '领用出库', '归还入库', '调拨', '回收'])
  })
})
