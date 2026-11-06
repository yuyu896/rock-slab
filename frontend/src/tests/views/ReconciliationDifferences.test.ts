import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { computed, defineComponent, h, inject, onMounted, provide, ref, type ComputedRef } from 'vue'

const permissionState = vi.hoisted(() => ({
  can: vi.fn((_code: string) => true),
}))

const mockComposable = vi.hoisted(() => ({
  setTask: vi.fn(async (_id: string) => {}),
}))

// Real Vue ref created at module scope (after imports) so watch() in the component works.
const mockCurrentTaskId = ref('task-1')

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@/store/user', () => ({
  useUserStore: () => ({ isAdmin: false, can: permissionState.can }),
}))

vi.mock('@/utils/request', () => ({
  handleApiError: vi.fn((error: unknown) => {
    const msg = (error as { message?: string })?.message || '请求失败'
    return msg
  }),
}))

vi.mock('@/composables/useReconciliationTask', () => ({
  useReconciliationTask: () => ({
    currentTaskId: mockCurrentTaskId,
    currentTask: { value: null },
    taskOptions: { value: [] },
    loadTaskOptions: vi.fn(async () => {}),
    setTask: mockComposable.setTask,
    clearTask: vi.fn(),
  }),
}))

vi.mock('@/api/reconciliation', () => ({
  getBranchSummary: vi.fn(),
  rematchTask: vi.fn(),
  getReconciliationTask: vi.fn(),
}))

import ReconciliationDifferences from '@/views/reconciliation/ReconciliationDifferences.vue'
import {
  getBranchSummary,
  rematchTask,
  getReconciliationTask,
} from '@/api/reconciliation'

const ButtonStub = defineComponent({
  emits: ['click'],
  setup(_props, { attrs, emit, slots }) {
    return () => h('button', { ...attrs, type: 'button', onClick: (event) => emit('click', event) }, slots.default?.())
  },
})

const SelectStub = defineComponent({
  inheritAttrs: false,
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue', 'change'],
  setup(props, { attrs, emit, slots }) {
    return () => h('select', {
      ...attrs,
      value: props.modelValue,
      onChange: (event: Event) => {
        const value = (event.target as HTMLSelectElement).value
        emit('update:modelValue', value)
        emit('change', value)
      },
    }, slots.default?.())
  },
})

const OptionStub = defineComponent({
  props: { label: { type: String, default: '' }, value: { type: String, default: '' } },
  setup(props) {
    return () => h('option', { value: props.value }, props.label)
  },
})

const tableRowsKey = Symbol('tableRows')

const TableColumnStub = defineComponent({
  name: 'ElTableColumn',
  props: {
    type: { type: String, default: '' },
    label: { type: String, default: '' },
    prop: { type: String, default: '' },
    width: { type: [String, Number], default: '' },
    align: { type: String, default: '' },
  },
  setup(props, { slots }) {
    const rows = inject<ComputedRef<Array<Record<string, any>>>>(tableRowsKey)!
    return () => {
      if (props.type === 'expand') {
        return h('div', { class: 'expand-column' }, rows.value.map((row, index) =>
          h('div', { class: 'expand-row', key: index }, slots.default?.({ row, $index: index }))))
      }
      return h('div', { class: 'table-col' }, [
        h('span', { class: 'col-label' }, props.label || props.prop),
        ...rows.value.map((row, index) => {
          const slotContent = slots.default?.({ row, $index: index, scope: { row } })
          const hasContent = Array.isArray(slotContent) ? slotContent.some((v) => v) : !!slotContent
          return h('div', { class: 'table-cell', key: index },
            hasContent ? slotContent : (props.prop ? [String(row[props.prop] ?? '')] : []))
        }),
      ])
    }
  },
})

const TableStub = defineComponent({
  name: 'ElTable',
  props: { data: { type: Array, default: () => [] } },
  emits: ['expand-change'],
  setup(props, { attrs, slots, emit }) {
    provide(tableRowsKey, computed(() => props.data as Array<Record<string, any>>))
    // Emit expand-change for each row on mount so lazy comparison loading fires
    onMounted(() => {
      for (const row of props.data as Array<Record<string, any>>) {
        emit('expand-change', row, props.data as Array<Record<string, any>>)
      }
    })
    return () => {
      const expandCol = slots.default?.().find((vnode: any) =>
        vnode?.type?.name === 'ElTableColumn' && vnode?.props?.type === 'expand')
      if (expandCol) {
        return h('div', { ...attrs, class: [attrs.class, 'table-stub'] }, [
          slots.default?.(),
          ...(props.data as Array<Record<string, any>>).map((row) =>
            h('div', { class: 'expand-detail', key: row.branchId }, (expandCol.children as any)?.default?.({ row, scope: { row } }))),
        ])
      }
      return h('div', { ...attrs, class: [attrs.class, 'table-stub'] }, [slots.default?.()])
    }
  },
})

const TagStub = defineComponent({
  name: 'ElTag',
  props: { type: { type: String, default: '' }, size: { type: String, default: '' } },
  setup(_props, { slots }) {
    return () => h('span', { class: 'el-tag-stub' }, slots.default?.())
  },
})

const TaskSelectorStub = defineComponent({
  name: 'ReconciliationTaskSelector',
  setup() {
    return () => h('div', { class: 'recon-task-selector' }, 'task-selector-stub')
  },
})

const mountPage = () => mount(ReconciliationDifferences, {
  global: {
    stubs: {
      'el-button': ButtonStub,
      'el-option': OptionStub,
      'el-select': SelectStub,
      'el-table': TableStub,
      'el-table-column': TableColumnStub,
      'el-tag': TagStub,
      ReconciliationTaskSelector: TaskSelectorStub,
    },
    directives: { loading: {} },
  },
})

const branchSummary = [
  { branchId: 'b1', branchName: '杭州分公司', orderCount: 5, matchedCount: 3, diffCount: 2, monthAmount: '1234.56' },
  { branchId: 'b2', branchName: '上海分公司', orderCount: 4, matchedCount: 4, diffCount: 0, monthAmount: '5678.90' },
]

const comparisonDetail = {
  id: 'task-1',
  supplierId: 's1',
  supplierName: '测试租赁商',
  period: '2026-11',
  status: 'draft' as const,
  currentVersion: 1,
  rowCount: 9,
  totalAmount: '6913.46',
  counts: {},
  branchTotals: [],
  createdAt: '2026-11-01',
  uploadedAt: null,
  uploadedBy: null,
  archivedAt: null,
  comparisons: [
    {
      id: 'c1', resultType: 'serial_diff', serial: 'ABC123', normalizedSerial: 'abc123',
      orderNumber: 'ORD-1', supplierBranch: '杭州', supplierBranchId: 'b1',
      systemBranch: '杭州', systemBranchId: 'b1', internalCode: 'IC-1',
      systemStatus: 'active', itemCode: 'IC', itemName: '电脑',
      leaseStartDate: null, accountingDate: null, billingDays: null,
      monthlyRent: null, monthAmount: '100.00', uploadedBillingDays: null,
      uploadedMonthAmount: null, billingStatus: null,
      issue: { id: 'issue-1', firstPeriod: '', lastPeriod: '' },
    },
  ],
  versions: [],
  unresolvedIssues: [],
}

describe('ReconciliationDifferences 页2', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    permissionState.can.mockImplementation(() => true)
    mockCurrentTaskId.value = 'task-1'
    mockComposable.setTask.mockClear()
    vi.mocked(getBranchSummary).mockResolvedValue({ data: branchSummary } as any)
    vi.mocked(rematchTask).mockResolvedValue({ data: { version: 2 } } as any)
    vi.mocked(getReconciliationTask).mockResolvedValue({ data: comparisonDetail } as any)
  })

  afterEach(() => vi.unstubAllGlobals())

  it('加载分公司汇总后渲染 KPI 条与分公司列表', async () => {
    const wrapper = mountPage()
    await flushPromises()

    expect(getBranchSummary).toHaveBeenCalledWith('task-1')
    // KPI bar
    const kpi = wrapper.find('.kpi-bar')
    expect(kpi.exists()).toBe(true)
    expect(kpi.text()).toContain('总差异数')
    expect(kpi.text()).toContain('2')
    expect(kpi.text()).toContain('匹配率')
    // matchRate = matched(7)/orders(9) * 100 = 77.8%
    expect(kpi.text()).toContain('77.8%')
    // Branch list
    expect(wrapper.text()).toContain('杭州分公司')
    expect(wrapper.text()).toContain('上海分公司')
    wrapper.unmount()
  })

  it('点击重新对账调用 rematchTask 后刷新汇总', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const rematchBtn = wrapper.findAll('button').find((b) => b.text().includes('重新对账'))
    expect(rematchBtn).toBeDefined()

    await rematchBtn!.trigger('click')
    await flushPromises()

    expect(rematchTask).toHaveBeenCalledWith('task-1')
    // ElMessage.success called with version
    const { ElMessage } = await import('element-plus')
    expect(ElMessage.success).toHaveBeenCalledWith('已重新对账，版本 2')
    // reload summary
    expect(getBranchSummary).toHaveBeenCalledTimes(2)
    // setTask called to refresh currentTask
    expect(mockComposable.setTask).toHaveBeenCalledWith('task-1')
    wrapper.unmount()
  })

  it('展开行加载明细比对，仅读不写入', async () => {
    const wrapper = mountPage()
    await flushPromises()

    // Manually trigger expand for the first branch
    const firstBranch = branchSummary[0]
    const vm = wrapper.vm as any
    vm.handleExpandChange(firstBranch, [firstBranch])
    await flushPromises()

    // Expand triggers getReconciliationTask with branch param, filtered to differences only
    expect(getReconciliationTask).toHaveBeenCalledWith('task-1', { branch: 'b1', result: 'differences' })
    wrapper.unmount()
  })
})
