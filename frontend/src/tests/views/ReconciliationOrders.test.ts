import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { computed, defineComponent, h, inject, provide, type ComputedRef } from 'vue'

const permissionState = vi.hoisted(() => ({
  can: vi.fn((_code: string) => true),
}))

const mockComposable = vi.hoisted(() => ({
  currentTask: { value: null as unknown },
  setTask: vi.fn(async (_id: string) => {}),
}))

const mockRouter = vi.hoisted(() => ({
  push: vi.fn(async (_to: string) => {}),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: mockRouter.push, replace: vi.fn() }),
}))

vi.mock('@/api/reconciliation', () => ({
  getReconciliationTasks: vi.fn(),
  getReconciliationTask: vi.fn(),
  previewReconciliationOrder: vi.fn(),
  importReconciliationOrder: vi.fn(),
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

vi.mock('@/utils/importTemplate', () => ({
  generateReconciliationTemplate: vi.fn(() => Promise.resolve()),
}))

vi.mock('@/composables/useReconciliationTask', () => ({
  useReconciliationTask: () => ({
    currentTaskId: { value: '' },
    currentTask: mockComposable.currentTask,
    taskOptions: { value: [] },
    loadTaskOptions: vi.fn(async () => {}),
    setTask: mockComposable.setTask,
    clearTask: vi.fn(),
  }),
}))

import ReconciliationOrders from '@/views/reconciliation/ReconciliationOrders.vue'
import {
  getReconciliationTasks,
  previewReconciliationOrder,
  importReconciliationOrder,
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

const InputStub = defineComponent({
  inheritAttrs: false,
  props: { modelValue: { type: String, default: '' } },
  emits: ['update:modelValue'],
  setup(props, { attrs, emit }) {
    return () => h('input', {
      ...attrs,
      value: props.modelValue,
      onInput: (event: Event) => emit('update:modelValue', (event.target as HTMLInputElement).value),
    })
  },
})

const tableRowsKey = Symbol('tableRows')

const TableColumnStub = defineComponent({
  setup(_props, { slots }) {
    const rows = inject<ComputedRef<Array<Record<string, any>>>>(tableRowsKey)!
    return () => h('div', rows.value.map((row, index) => slots.default?.({ row, $index: index })))
  },
})

const TableStub = defineComponent({
  props: { data: { type: Array, default: () => [] } },
  emits: ['row-click'],
  setup(props, { attrs, slots }) {
    provide(tableRowsKey, computed(() => props.data as Array<Record<string, any>>))
    return () => h('div', { ...attrs, class: [attrs.class, 'table-stub'] }, [
      slots.default?.(),
    ])
  },
})

const TaskSelectorStub = defineComponent({
  name: 'ReconciliationTaskSelector',
  setup() {
    return () => h('div', { class: 'recon-task-selector' }, 'task-selector-stub')
  },
})

const mountPage = () => mount(ReconciliationOrders, {
  global: {
    stubs: {
      'el-button': ButtonStub,
      'el-option': OptionStub,
      'el-select': SelectStub,
      'el-date-picker': InputStub,
      'el-table': TableStub,
      'el-table-column': TableColumnStub,
      'el-tag': true,
      ReconciliationTaskSelector: TaskSelectorStub,
    },
    directives: { loading: {} },
  },
})

const suppliers = [
  { id: 'supplier-1', name: '测试租赁商' },
  { id: 'supplier-2', name: '另一家供应商' },
]

const taskData = {
  id: 'task-1', supplierId: 'supplier-1', supplierName: '测试租赁商',
  period: '2026-09', status: 'draft', currentVersion: 1, rowCount: 3,
  totalAmount: '31.37', counts: { matched: 1 }, branchTotals: [],
  createdAt: '2026-09-20', uploadedAt: null, uploadedBy: '管理员', archivedAt: null,
}

describe('ReconciliationOrders 页1', () => {
  afterEach(() => vi.unstubAllGlobals())

  beforeEach(() => {
    vi.clearAllMocks()
    permissionState.can.mockImplementation(() => true)
    mockComposable.currentTask.value = null
    mockComposable.setTask.mockClear()
    mockRouter.push.mockClear()
    vi.mocked(getReconciliationTasks).mockResolvedValue({
      data: { suppliers, results: [taskData] },
    } as any)
  })

  it('点击导入订单打开 dialog', async () => {
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('对账 · 供应商订单')
    const importButton = wrapper.findAll('button').find((button) => button.text().includes('导入订单'))
    expect(importButton).toBeDefined()

    await importButton!.trigger('click')
    await flushPromises()

    const importModal = wrapper.find('.reconciliation-import-modal')
    expect(importModal.exists()).toBe(true)
    expect(importModal.text()).toContain('上传订单文件')
    expect(importModal.text()).toContain('对账月份')
    expect(importModal.text()).toContain('解析并预览')
    wrapper.unmount()
  })

  it('导入成功后调用 importReconciliationOrder 并 setTask 跳转页2', async () => {
    const preview = {
      supplierId: 'supplier-1', supplierName: '测试租赁商', period: '2026-09',
      branchCount: 1, orderCount: 1, rowCount: 1, totalAmount: '11.37',
      branchTotals: [], calculationWarnings: [],
    }
    vi.mocked(previewReconciliationOrder).mockResolvedValue({ data: preview } as any)
    vi.mocked(importReconciliationOrder).mockResolvedValue({ data: taskData } as any)

    const wrapper = mountPage()
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('导入订单'))!.trigger('click')
    await flushPromises()

    await wrapper.get('select').setValue('supplier-1')
    await wrapper.get('input[type="month"]').setValue('2026-09')

    const file = new File(['order'], 'order.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    Object.defineProperty(wrapper.get('#reconciliation-orders-file').element, 'files', { value: [file] })
    await wrapper.get('#reconciliation-orders-file').trigger('change')

    await wrapper.findAll('button').find((button) => button.text().includes('解析并预览'))!.trigger('click')
    await flushPromises()
    expect(previewReconciliationOrder).toHaveBeenCalledWith('supplier-1', '2026-09', file)

    // After resolveImportTargetTask finds a matching task, the button becomes "替换订单并重新对账"
    // (if no match it would be "确认导入并对账"). Either label means the submit button.
    const submitButton = wrapper.findAll('button').find((button) =>
      button.text().includes('确认导入并对账') || button.text().includes('替换订单并重新对账')
    )
    expect(submitButton).toBeDefined()
    await submitButton!.trigger('click')
    await flushPromises()

    expect(importReconciliationOrder).toHaveBeenCalledWith('supplier-1', '2026-09', file)
    expect(mockComposable.setTask).toHaveBeenCalledWith('task-1')
    expect(mockRouter.push).toHaveBeenCalledWith('/reconciliation/differences')
    wrapper.unmount()
  })

  it('缺少供应商查看权限时隐藏导入按钮', async () => {
    permissionState.can.mockImplementation((code) => code !== 'view_suppliers')
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.find('.header-actions').text()).not.toContain('导入订单')
    wrapper.unmount()
  })
})
