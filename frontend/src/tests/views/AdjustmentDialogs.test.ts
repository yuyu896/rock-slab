import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

vi.mock('@/api/assets', () => ({
  getLedgerAdjustments: vi.fn(),
  createLedgerAdjustment: vi.fn(),
}))

vi.mock('@/api/branches', () => ({
  getBranches: vi.fn().mockResolvedValue({ data: [{ id: 'b1', name: '分公司A' }] }),
}))

vi.mock('@/api/inventories', () => ({
  getInventoryReport: vi.fn(),
}))

vi.mock('@/utils/request', async () => {
  const actual = await vi.importActual<typeof import('@/utils/request')>('@/utils/request')
  return {
    ...actual,
    handleApiError: (e: any) => e?.response?.data?.detail ?? '请求失败',
  }
})

import AdjustDialog from '@/views/assets/AdjustDialog.vue'
import AdjustRecordsDialog from '@/views/assets/AdjustRecordsDialog.vue'
import ApprovePreviewDialog from '@/views/inventory/ApprovePreviewDialog.vue'
import { createLedgerAdjustment, getLedgerAdjustments } from '@/api/assets'
import { getInventoryReport } from '@/api/inventories'
import type { AssetStock, LedgerAdjustment } from '@/types'

const stock = {
  id: 's1',
  branch: 'b1',
  branchName: '分公司A',
  item: 'i1',
  资产编号: 'A-1',
  资产名称: '办公椅',
  在库数量: 7,
  在用数量: 2,
  回收库数量: 1,
} as AssetStock

describe('AdjustDialog 行内开调整单（P3）', () => {
  beforeEach(() => vi.clearAllMocks())

  function mountDialog() {
    return mount(AdjustDialog, { props: { visible: true, stock } })
  }

  it('提交成功提示单据编号并触发 success/close', async () => {
    vi.mocked(createLedgerAdjustment).mockResolvedValue({
      data: { id: 'adj1', 单据编号: 'TZ20260824-001' } as LedgerAdjustment,
    } as any)
    const wrapper = mountDialog()

    await wrapper.find('input[type="text"]').setValue('实物校准')
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()

    expect(createLedgerAdjustment).toHaveBeenCalledWith({
      branch: 'b1',
      资产编号: 'A-1',
      目标列: '在库数量',
      变动量: 1,
      事由: '实物校准',
    })
    expect(wrapper.emitted('success')).toBeTruthy()
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('后端不足报错原样展示，不触发 success', async () => {
    vi.mocked(createLedgerAdjustment).mockRejectedValue({
      response: { data: { detail: '「分公司A × A-1」在库数量不足：当前 1，需变动 -5' } },
    })
    const wrapper = mountDialog()

    await wrapper.find('input[type="text"]').setValue('越界调整')
    await wrapper.find('input[type="number"]').setValue(-5)
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()

    expect(wrapper.find('.error-text').text()).toContain('不足')
    expect(wrapper.emitted('success')).toBeFalsy()
  })

  it('事由为空被本地拦截不发请求', async () => {
    const wrapper = mountDialog()
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()
    expect(createLedgerAdjustment).not.toHaveBeenCalled()
    expect(wrapper.find('.error-text').text()).toContain('事由')
  })
})

describe('AdjustRecordsDialog 调整记录（P3）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('打开即拉列表，来源列区分手动与盘点生成', async () => {
    vi.mocked(getLedgerAdjustments).mockResolvedValue({
      data: {
        count: 2, next: null, previous: null,
        results: [
          { id: 'a1', 单据编号: 'TZ20260824-001', branchName: '分公司A', 资产编号: 'A-1', 目标列: '在库数量', 变动量: -2, 事由: '盘点差异「8月盘点」：在库 5 → 3（盘亏2）', 经办人姓名: '管理员', 来源任务: '8月盘点', createdAt: '2026-08-24T10:00:00' },
          { id: 'a2', 单据编号: 'TZ20260824-002', branchName: '分公司A', 资产编号: 'A-2', 目标列: '在库数量', 变动量: 5, 事由: '实物校准', 经办人姓名: '管理员', 来源任务: null, createdAt: '2026-08-24T11:00:00' },
        ],
      },
    } as any)

    const wrapper = mount(AdjustRecordsDialog, { props: { visible: true } })
    await flushPromises()

    expect(getLedgerAdjustments).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }))
    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('8月盘点')
    expect(rows[1].text()).toContain('手动')
    expect(rows[0].text()).toContain('-2')
    expect(rows[1].text()).toContain('+5')
  })

  it('按编号筛选走 assetCode 参数', async () => {
    vi.mocked(getLedgerAdjustments).mockResolvedValue({
      data: { count: 0, next: null, previous: null, results: [] },
    } as any)
    const wrapper = mount(AdjustRecordsDialog, { props: { visible: true } })
    await flushPromises()

    const codeInput = wrapper.find('input[type="text"]')
    await codeInput.setValue('A-1')
    await wrapper.find('.filter-apply').trigger('click')
    await flushPromises()

    expect(getLedgerAdjustments).toHaveBeenLastCalledWith(
      expect.objectContaining({ assetCode: 'A-1', page: 1 }),
    )
  })
})

describe('ApprovePreviewDialog 审批差异预览（P3）', () => {
  beforeEach(() => vi.clearAllMocks())

  it('有差异：列出明细并明示将生成调整单数，确认触发 confirm', async () => {
    vi.mocked(getInventoryReport).mockResolvedValue({
      data: {
        task: { status: 'pending_review' },
        items: [
          { id: 'i1', assetCode: 'A-1', assetName: '办公椅', expectedQty: 5, actualQty: 3, result: 'missing' },
          { id: 'i2', assetCode: 'A-2', assetName: '显示器', expectedQty: 4, actualQty: 6, result: 'surplus' },
          { id: 'i3', assetCode: 'A-3', assetName: '键盘', expectedQty: 2, actualQty: 2, result: 'matched' },
        ],
      },
    } as any)

    const wrapper = mount(ApprovePreviewDialog, {
      props: { visible: true, taskId: 't1', taskName: '8月盘点' },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('将生成')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('盘盈 1 / 盘亏 1')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2) // matched 不入预览

    await wrapper.find('.btn-primary').trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
  })

  it('无差异：明示零单，仍可确认', async () => {
    vi.mocked(getInventoryReport).mockResolvedValue({
      data: {
        task: { status: 'pending_review' },
        items: [{ id: 'i1', assetCode: 'A-1', expectedQty: 5, actualQty: 5, result: 'matched' }],
      },
    } as any)

    const wrapper = mount(ApprovePreviewDialog, {
      props: { visible: true, taskId: 't1', taskName: '8月盘点' },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('无差异')
    expect(wrapper.text()).toContain('不生成调整单')
    await wrapper.find('.btn-primary').trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
  })
})
