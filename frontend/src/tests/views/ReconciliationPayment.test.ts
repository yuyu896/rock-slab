import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { computed, defineComponent, h, inject, provide, ref, type ComputedRef } from 'vue'

const permissionState = vi.hoisted(() => ({
  can: vi.fn((_code: string) => true),
}))

// Real Vue ref created at module scope (after imports) so watch() in the component works.
const mockCurrentTaskId = ref('task-1')

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
  ElMessageBox: { confirm: vi.fn(async () => 'confirm') },
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
    currentTask: { value: { period: '2026-11', supplierName: '测试租赁商' } },
    taskOptions: { value: [] },
    loadTaskOptions: vi.fn(async () => {}),
    setTask: vi.fn(),
    clearTask: vi.fn(),
  }),
}))

vi.mock('@/api/reconciliation', () => ({
  getPaymentSummary: vi.fn(),
  exportPayment: vi.fn(),
  archiveReconciliationTask: vi.fn(),
}))

import ReconciliationPayment from '@/views/reconciliation/ReconciliationPayment.vue'
import {
  getPaymentSummary,
  exportPayment,
  archiveReconciliationTask,
} from '@/api/reconciliation'

const ButtonStub = defineComponent({
  emits: ['click'],
  setup(_props, { attrs, emit, slots }) {
    return () => h('button', { ...attrs, type: 'button', onClick: (event) => emit('click', event) }, slots.default?.())
  },
})

const TagStub = defineComponent({
  name: 'ElTag',
  props: { type: { type: String, default: '' }, size: { type: String, default: '' } },
  setup(_props, { slots }) {
    return () => h('span', { class: 'el-tag-stub' }, slots.default?.())
  },
})

const TooltipStub = defineComponent({
  name: 'ElTooltip',
  props: { content: { type: String, default: '' }, disabled: { type: Boolean, default: false } },
  setup(props, { slots }) {
    return () => h('div', { class: 'el-tooltip-stub' }, [
      h('span', { class: 'tooltip-content', 'data-content': props.content, 'data-disabled': String(props.disabled) }, props.content),
      slots.default?.(),
    ])
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
  setup(props, { attrs, slots }) {
    provide(tableRowsKey, computed(() => props.data as Array<Record<string, any>>))
    return () => h('div', { ...attrs, class: [attrs.class, 'table-stub'] }, [slots.default?.()])
  },
})

const TaskSelectorStub = defineComponent({
  name: 'ReconciliationTaskSelector',
  setup() {
    return () => h('div', { class: 'recon-task-selector' }, 'task-selector-stub')
  },
})

const mountPage = () => mount(ReconciliationPayment, {
  global: {
    stubs: {
      'el-button': ButtonStub,
      'el-table': TableStub,
      'el-table-column': TableColumnStub,
      'el-tag': TagStub,
      'el-tooltip': TooltipStub,
      ReconciliationTaskSelector: TaskSelectorStub,
    },
    directives: { loading: {} },
  },
})

const mockRows = [
  {
    serial: 'ABC001',
    branch: '杭州分公司',
    internalCode: 'IC-1',
    leaseStartDate: '2026-01-01',
    accountingDate: '2026-11-01',
    billingDays: 30,
    monthlyRent: '1000.00',
    monthAmount: '1000.00',
    billingStatus: 'billable' as const,
    conclusionType: '',
  },
  {
    serial: 'ABC002',
    branch: '上海分公司',
    internalCode: 'IC-2',
    leaseStartDate: null,
    accountingDate: null,
    billingDays: null,
    monthlyRent: null,
    monthAmount: '500.00',
    billingStatus: 'not_started' as const,
    conclusionType: 'supplier_overbilled',
  },
  {
    serial: 'ABC003',
    branch: '杭州分公司',
    internalCode: 'IC-3',
    leaseStartDate: '2026-03-01',
    accountingDate: '2026-11-01',
    billingDays: 30,
    monthlyRent: '2000.00',
    monthAmount: '2000.00',
    billingStatus: 'billable' as const,
    conclusionType: 'serial_corrected',
  },
]

function makeSummary(canArchive: boolean) {
  return {
    confirmedAmount: '2500.00',
    pendingAmount: '1000.00',
    totalAmount: '3500.00',
    canArchive,
    rows: mockRows,
  }
}

describe('ReconciliationPayment 页3', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    permissionState.can.mockImplementation(() => true)
    mockCurrentTaskId.value = 'task-1'
  })

  afterEach(() => vi.unstubAllGlobals())

  it('渲染金额汇总（已确认/待确认/本月应计）', async () => {
    vi.mocked(getPaymentSummary).mockResolvedValue({ data: makeSummary(true) } as any)

    const wrapper = mountPage()
    await flushPromises()

    expect(getPaymentSummary).toHaveBeenCalledWith('task-1')

    const cards = wrapper.findAll('.amount-card')
    expect(cards).toHaveLength(3)

    expect(cards[0].text()).toContain('已确认')
    expect(cards[0].text()).toContain('¥2,500.00')

    expect(cards[1].text()).toContain('待确认')
    expect(cards[1].text()).toContain('¥1,000.00')

    expect(cards[2].text()).toContain('本月应计')
    expect(cards[2].text()).toContain('¥3,500.00')

    wrapper.unmount()
  })

  it('canArchive=false 时归档按钮禁用且 tooltip 显示未处理差异数', async () => {
    // 1 row with conclusionType === '' => pendingRowCount = 1
    vi.mocked(getPaymentSummary).mockResolvedValue({ data: makeSummary(false) } as any)

    const wrapper = mountPage()
    await flushPromises()

    const tooltip = wrapper.findComponent(TooltipStub)
    expect(tooltip.exists()).toBe(true)
    expect(tooltip.props('disabled')).toBe(false)
    expect(tooltip.props('content')).toBe('仍有 1 条差异未处理')

    const buttons = wrapper.findAll('button')
    const archiveBtn = buttons.find((b) => b.text().includes('归档'))
    expect(archiveBtn).toBeDefined()
    // The button should be disabled (summary.canArchive is false)
    expect(archiveBtn!.attributes('disabled')).toBeDefined()

    wrapper.unmount()
  })

  it('明细表行数与 mock 数据一致', async () => {
    vi.mocked(getPaymentSummary).mockResolvedValue({ data: makeSummary(true) } as any)

    const wrapper = mountPage()
    await flushPromises()

    // The table stub renders rows based on the data prop; check that all 3 rows' serials appear
    const text = wrapper.text()
    expect(text).toContain('ABC001')
    expect(text).toContain('ABC002')
    expect(text).toContain('ABC003')
    expect(text).toContain('杭州分公司')
    expect(text).toContain('上海分公司')

    wrapper.unmount()
  })

  it('导出按钮触发 blob 下载', async () => {
    vi.mocked(getPaymentSummary).mockResolvedValue({ data: makeSummary(true) } as any)
    const mockBlob = new Blob(['test'], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    vi.mocked(exportPayment).mockResolvedValue({ data: mockBlob } as any)

    // Stub URL.createObjectURL and DOM anchor methods
    const createObjectURLSpy = vi.fn(() => 'blob:test-url')
    const revokeObjectURLSpy = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL: createObjectURLSpy, revokeObjectURL: revokeObjectURLSpy })

    const wrapper = mountPage()
    await flushPromises()

    const exportBtn = wrapper.findAll('button').find((b) => b.text().includes('导出'))
    expect(exportBtn).toBeDefined()

    await exportBtn!.trigger('click')
    await flushPromises()

    expect(exportPayment).toHaveBeenCalledWith('task-1')
    expect(createObjectURLSpy).toHaveBeenCalledTimes(1)

    wrapper.unmount()
  })
})
