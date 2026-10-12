import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { computed, defineComponent, h, inject, provide, type ComputedRef } from 'vue'
import { ElMessageBox } from 'element-plus'

vi.mock('@/api/reconciliation', () => ({
  getReconciliationTasks: vi.fn(),
  getReconciliationTask: vi.fn(),
  previewReconciliationOrder: vi.fn(),
  importReconciliationOrder: vi.fn(),
  archiveReconciliationTask: vi.fn(),
  exportReconciliationTask: vi.fn(),
  exportReconciliationDifferences: vi.fn(),
  getReconciliationIssueHistory: vi.fn(),
  updateReconciliationIssue: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: vi.fn(), success: vi.fn() },
  ElMessageBox: { confirm: vi.fn().mockResolvedValue(undefined) },
}))

import Reconciliation from '@/views/Reconciliation.vue'
import {
  archiveReconciliationTask,
  exportReconciliationDifferences,
  exportReconciliationTask,
  getReconciliationTask,
  getReconciliationTasks,
  importReconciliationOrder,
  previewReconciliationOrder,
  updateReconciliationIssue,
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
  emits: ['update:modelValue'],
  setup(props, { attrs, emit, slots }) {
    return () => h('select', {
      ...attrs,
      value: props.modelValue,
      onChange: (event: Event) => emit('update:modelValue', (event.target as HTMLSelectElement).value),
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

const DialogStub = defineComponent({
  props: { modelValue: Boolean },
  setup(props, { slots }) {
    return () => props.modelValue ? h('div', { class: 'dialog-stub' }, [slots.default?.(), slots.footer?.()]) : null
  },
})

const ContentStub = defineComponent({
  props: {
    title: { type: String, default: '' },
    description: { type: String, default: '' },
    label: { type: String, default: '' },
  },
  setup(props, { slots }) {
    return () => h('div', [props.title, props.description, props.label, slots.default?.()])
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
  setup(props, { attrs, emit, slots }) {
    provide(tableRowsKey, computed(() => props.data as Array<Record<string, any>>))
    return () => h('div', { ...attrs, class: [attrs.class, 'table-stub'] }, [
      ...(props.data as Array<Record<string, any>>).map((row) => h('button', {
        class: 'table-row', type: 'button', onClick: () => emit('row-click', row),
      }, row.supplierName || row.serial || row.branchName || 'row')),
      slots.default?.(),
    ])
  },
})

const mountPage = () => mount(Reconciliation, {
  global: {
    stubs: {
      'el-button': ButtonStub,
      'el-option': OptionStub,
      'el-select': SelectStub,
      'el-date-picker': InputStub,
      'el-input': InputStub,
      'el-table': TableStub,
      'el-table-column': TableColumnStub,
      'el-tag': true,
      'el-empty': ContentStub,
      'el-alert': ContentStub,
      'el-form-item': ContentStub,
      'el-form': ContentStub,
      'el-dialog': DialogStub,
    },
    directives: { loading: {} },
  },
})

const taskRows = [
  {
    id: 'task-1', supplierId: 'supplier-1', supplierName: '测试租赁商',
    period: '2026-09', status: 'draft', currentVersion: 1, rowCount: 3,
    comparisonCount: 6, totalAmount: '31.37', counts: { matched: 1, order_only: 1, system_only: 1, system_missing_serial: 1, branch_mismatch: 1, system_duplicate: 1 },
    branchTotals: [], createdAt: '2026-09-20', uploadedAt: null,
    uploadedBy: '管理员', archivedAt: null,
  },
  {
    id: 'task-2', supplierId: 'supplier-2', supplierName: '另一家供应商',
    period: '2026-08', status: 'archived', currentVersion: 2, rowCount: 1,
    comparisonCount: 1, totalAmount: '12.00', counts: { matched: 1 },
    branchTotals: [], createdAt: '2026-08-20', uploadedAt: null,
    uploadedBy: '管理员', archivedAt: '2026-08-25',
  },
]

describe('对账模块', () => {
  afterEach(() => vi.unstubAllGlobals())

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getReconciliationTasks).mockResolvedValue({
      data: {
        suppliers: [
          { id: 'supplier-1', name: '测试租赁商' },
          { id: 'supplier-2', name: '另一家供应商' },
        ],
        results: taskRows,
      },
    } as any)
  })

  it('通过任务工具栏筛选供应商和月份', async () => {
    const wrapper = mountPage()
    await flushPromises()

    expect(getReconciliationTasks).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('对账')
    expect(wrapper.find('.list-toolbar').exists()).toBe(true)
    expect(wrapper.text()).toContain('下载订单模板')
    expect(wrapper.find('.import-strip').exists()).toBe(false)
    expect(wrapper.findAll('.task-table .table-row')).toHaveLength(2)

    await wrapper.get('select[aria-label="按供应商筛选"]').setValue('supplier-1')
    expect(wrapper.findAll('.task-table .table-row')).toHaveLength(1)
    expect(wrapper.text()).toContain('1 项任务')

    await wrapper.get('select[aria-label="按月份筛选"]').setValue('2026-08')
    expect(wrapper.findAll('.task-table .table-row')).toHaveLength(0)
    expect(wrapper.find('.empty-filter').exists()).toBe(true)
  })

  it('在专用导入对话框中提供订单表单', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const importButton = wrapper.findAll('button').find((button) => button.text().includes('导入订单'))
    await importButton!.trigger('click')
    expect(wrapper.find('.dialog-stub').text()).toContain('供应商订单文件')
    expect(wrapper.find('.dialog-stub').text()).toContain('对账月份')
    expect(wrapper.find('.dialog-stub').text()).toContain('下载订单模板')
    expect(wrapper.find('.dialog-stub').text()).toContain('记账天数和本月金额由系统计算，可留空')
    expect(wrapper.find('.dialog-stub').text()).toContain('解析并预览')
  })

  it('先预览订单，确认时重新提交原文件到正式导入接口', async () => {
    const preview = {
      supplierId: 'supplier-1', supplierName: '测试租赁商', period: '2026-09',
      branchCount: 1, orderCount: 1, rowCount: 1, totalAmount: '11.37', branchTotals: [], calculationWarnings: [],
    }
    vi.mocked(previewReconciliationOrder).mockResolvedValue({ data: preview } as any)
    vi.mocked(importReconciliationOrder).mockResolvedValue({ data: taskRows[0] } as any)
    vi.mocked(getReconciliationTask).mockResolvedValue({
      data: { ...taskRows[0], comparisons: [], versions: [], unresolvedIssues: [], branchTotals: [] },
    } as any)
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text().includes('导入订单'))!.trigger('click')
    await wrapper.get('select').setValue('supplier-1')
    await wrapper.get('input[type="month"]').setValue('2026-09')
    const file = new File(['order'], 'order.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    Object.defineProperty(wrapper.get('#reconciliation-file').element, 'files', { value: [file] })
    await wrapper.get('#reconciliation-file').trigger('change')

    await wrapper.findAll('button').find((button) => button.text().includes('解析并预览'))!.trigger('click')
    await flushPromises()
    expect(previewReconciliationOrder).toHaveBeenCalledWith('supplier-1', '2026-09', file)
    expect(wrapper.find('.import-preview').text()).toContain('¥11.37')
    await wrapper.findAll('button').find((button) => button.text().includes('替换订单并重新对账'))!.trigger('click')
    await flushPromises()
    expect(importReconciliationOrder).toHaveBeenCalledWith('supplier-1', '2026-09', file)
  })

  it('打开任务时默认显示差异，并支持切换全部结果和序列号搜索', async () => {
    vi.mocked(getReconciliationTask).mockResolvedValue({
      data: {
        ...taskRows[0],
        comparisons: [
          { id: 'compare-1', resultType: 'matched', serial: 'MATCH-SN', normalizedSerial: 'MATCH-SN', supplierBranch: '分公司甲', supplierBranchId: 'branch-1', systemBranch: '分公司甲', systemBranchId: 'branch-1', issue: null },
          { id: 'compare-2', resultType: 'order_only', serial: 'ORDER-SN', normalizedSerial: 'ORDER-SN', supplierBranch: '分公司甲', supplierBranchId: 'branch-1', systemBranch: '', systemBranchId: null, issue: { id: 'issue-1', status: 'open', conclusion: '', note: '', firstPeriod: '2026-09', lastPeriod: '2026-09' } },
          { id: 'compare-3', resultType: 'system_only', serial: 'SYSTEM-SN', normalizedSerial: 'SYSTEM-SN', supplierBranch: '', supplierBranchId: null, systemBranch: '分公司乙', systemBranchId: 'branch-2', issue: { id: 'issue-2', status: 'open', conclusion: '', note: '', firstPeriod: '2026-09', lastPeriod: '2026-09' } },
          { id: 'compare-4', resultType: 'system_missing_serial', serial: '', normalizedSerial: '', supplierBranch: '', supplierBranchId: null, systemBranch: '', systemBranchId: null, issue: { id: 'issue-3', status: 'open', conclusion: '', note: '', firstPeriod: '2026-09', lastPeriod: '2026-09' } },
          { id: 'compare-5', resultType: 'branch_mismatch', serial: 'MISMATCH-SN', normalizedSerial: 'MISMATCH-SN', supplierBranch: '分公司甲', supplierBranchId: 'branch-1', systemBranch: '分公司乙', systemBranchId: 'branch-2', issue: { id: 'issue-4', status: 'open', conclusion: '', note: '', firstPeriod: '2026-09', lastPeriod: '2026-09' } },
          { id: 'compare-6', resultType: 'system_duplicate', serial: 'DUPLICATE-SN', normalizedSerial: 'DUPLICATE-SN', supplierBranch: '', supplierBranchId: null, systemBranch: '分公司乙', systemBranchId: 'branch-2', issue: { id: 'issue-5', status: 'open', conclusion: '', note: '', firstPeriod: '2026-09', lastPeriod: '2026-09' } },
        ],
        versions: [], unresolvedIssues: [], branchTotals: [],
      },
    } as any)
    const wrapper = mountPage()
    await flushPromises()

    await wrapper.get('.task-table .table-row').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.comparison-table .table-row')).toHaveLength(5)
    expect(wrapper.text()).toContain('未归属分公司')
    expect(wrapper.find('.result-filter.active').text()).toContain('待填写结论（5）')
    expect(wrapper.text()).toContain('本月应计金额')

    const allResults = wrapper.findAll('.result-filter').find((button) => button.text().includes('全部结果'))
    expect(allResults).toBeDefined()
    await allResults!.trigger('click')
    expect(wrapper.findAll('.comparison-table .table-row')).toHaveLength(6)
    expect(wrapper.find('.matched-records').exists()).toBe(true)
    expect(wrapper.find('.matched-records').element.hasAttribute('open')).toBe(false)

    const matchedResults = wrapper.findAll('.result-filter').find((button) => button.text().includes('匹配记录'))
    await matchedResults!.trigger('click')
    expect(wrapper.findAll('.matched-table .table-row')).toHaveLength(1)

    await allResults!.trigger('click')
    await wrapper.get('select[aria-label="按分公司筛选"]').setValue('branch-2')
    expect(wrapper.findAll('.comparison-table .table-row')).toHaveLength(3)

    await wrapper.get('input[aria-label="搜索序列号"]').setValue('SYSTEM-SN')
    expect(wrapper.findAll('.comparison-table .table-row')).toHaveLength(1)
    expect(wrapper.find('.comparison-table').text()).toContain('SYSTEM-SN')
  })

  it('按供应商和首次发现月份展示历史未决入口', async () => {
    vi.mocked(getReconciliationTasks).mockResolvedValue({
      data: {
        suppliers: [], results: [],
        unresolvedSummary: {
          totalCount: 2,
          groups: [{ supplierId: 'supplier-1', supplierName: '测试租赁商', firstPeriod: '2026-07', count: 2 }],
        },
      },
    } as any)
    const wrapper = mountPage()
    await flushPromises()

    expect(wrapper.find('.unresolved-summary').text()).toContain('2 条历史未决事项')
    expect(wrapper.find('.unresolved-link').text()).toContain('测试租赁商 · 2026-07')
  })

  it('保留导出和归档操作', async () => {
    vi.mocked(getReconciliationTask).mockResolvedValue({
      data: {
        ...taskRows[0],
        comparisons: [{
          id: 'compare-issue', resultType: 'order_only', serial: 'ORDER-SN', normalizedSerial: 'ORDER-SN',
          supplierBranch: '分公司甲', supplierBranchId: 'branch-1', systemBranch: '', systemBranchId: null,
          issue: { id: 'issue-1', status: 'open', conclusion: '已核实', note: '', firstPeriod: '2026-09', lastPeriod: '2026-09' },
        }],
        versions: [], unresolvedIssues: [{ id: 'historical-1', issueType: 'order_only', serial: 'OLD-SN', status: 'not_recurred', firstPeriod: '2026-08', lastPeriod: '2026-09', conclusion: '' }], branchTotals: [],
      },
    } as any)
    vi.mocked(exportReconciliationTask).mockResolvedValue({ data: new Blob() } as any)
    vi.mocked(exportReconciliationDifferences).mockResolvedValue({ data: new Blob() } as any)
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() })

    const wrapper = mountPage()
    await flushPromises()
    await wrapper.get('.task-table .table-row').trigger('click')
    await flushPromises()
    await wrapper.findAll('.result-filter').find((button) => button.text().includes('全部差异'))!.trigger('click')

    await wrapper.find('.comparison-table').findAll('button').find((button) => button.text().includes('处理'))!.trigger('click')
    await wrapper.findAll('button').find((button) => button.text().includes('保存记录'))!.trigger('click')
    await flushPromises()
    expect(updateReconciliationIssue).toHaveBeenCalledWith('issue-1', { conclusion: '已核实', note: '' })

    await wrapper.findAll('button').find((button) => button.text().includes('导出结果'))!.trigger('click')
    await wrapper.findAll('button').find((button) => button.text().includes('导出差异'))!.trigger('click')
    await wrapper.findAll('button').find((button) => button.text().includes('完成并归档'))!.trigger('click')
    await flushPromises()

    expect(exportReconciliationTask).toHaveBeenCalledWith('task-1')
    expect(exportReconciliationDifferences).toHaveBeenCalledWith('task-1')
    expect(archiveReconciliationTask).toHaveBeenCalledWith('task-1')
    expect(ElMessageBox.confirm).toHaveBeenCalledWith(
      expect.stringContaining('差异总数：1 条\n已有处理结论：1 条\n待填写结论：0 条\n历史未决事项：1 条'),
      '完成并归档', expect.any(Object),
    )
  })
})
