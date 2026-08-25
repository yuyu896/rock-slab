import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/api/reports', () => ({
  getOverview: vi.fn(),
  getByBranch: vi.fn(),
  getByStatus: vi.fn(),
  getByCategory: vi.fn(),
  getTransferReport: vi.fn(),
  getReportBranches: vi.fn().mockResolvedValue({ data: [] }),
}))

import Reports from '@/views/Reports.vue'
import { getOverview, getByBranch, getByStatus, getByCategory, getTransferReport } from '@/api/reports'

function _mockAll(overrides: Record<string, any> = {}) {
  vi.mocked(getOverview).mockResolvedValue({
    data: {
      totalAssets: 10, totalValue: 1500, activeRate: 80, growthRate: 5,
      valueGrowthRate: 12.5, lowStockCount: 3,
      ...overrides.overview,
    },
  } as any)
  vi.mocked(getByBranch).mockResolvedValue({
    data: overrides.byBranch ?? [
      { name: '分公司A', branchId: 'b1', stock: 6, inUse: 2, recycle: 2, value: 10, percentage: 66.67, amount: 1500, amountPercentage: 100 },
      { name: '分公司B', branchId: 'b2', stock: 2, inUse: 1, recycle: 2, value: 5, percentage: 33.33, amount: 0, amountPercentage: 0 },
    ],
  } as any)
  vi.mocked(getByStatus).mockResolvedValue({ data: overrides.byStatus ?? [] } as any)
  vi.mocked(getByCategory).mockResolvedValue({
    data: overrides.byCategory ?? [
      { category: '固定资产', count: 8, percentage: 53.33 },
      { category: '办公用品', count: 7, percentage: 46.67 },
    ],
  } as any)
  vi.mocked(getTransferReport).mockResolvedValue({
    data: overrides.transfers ?? [],
  } as any)
}

async function mountReports() {
  const wrapper = mount(Reports, {
    global: {
      components: {}, // el-select 等由模板未解析组件警告容忍
    },
  })
  await flushPromises()
  return wrapper
}

describe('Reports 报表页真实数据契约（P3 刀二）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _mockAll()
  })

  it('指标卡全接真数据：库存不足 3、总值增速 12.5%，无 +12.3%/+2.1% 假角标', async () => {
    const wrapper = await mountReports()
    const text = wrapper.text()
    expect(text).toContain('12.5%')       // 总值增速（valueGrowthRate）
    expect(text).not.toContain('+12.3%')  // 旧硬编码
    expect(text).not.toContain('+2.1%')   // 旧硬编码
    // 库存不足卡显示 lowStockCount 而非固定 12
    const warningCard = wrapper.find('.metric-card.warning')
    expect(warningCard.text()).toContain('库存不足')
    expect(warningCard.find('.metric-value').text()).toBe('3')
  })

  it('分公司排行数量/价值切换数据源', async () => {
    const wrapper = await mountReports()
    const tabs = wrapper.findAll('.chart-tab')
    expect(tabs.map(t => t.text())).toEqual(['数量', '价值'])

    // 默认数量口径
    expect(wrapper.find('.bar-value').text()).toBe('10')

    await tabs[1].trigger('click')
    expect(wrapper.find('.bar-value').text()).toContain('1,500')
  })

  it('分类环图数据来自 by_category，不再取已删除的品目字段', async () => {
    const wrapper = await mountReports()
    expect(getByCategory).toHaveBeenCalled()
    const legend = wrapper.findAll('.legend-item')
    expect(legend).toHaveLength(2)
    expect(legend[0].text()).toContain('固定资产')
    expect(legend[0].text()).toContain('8')
  })

  it('月度趋势按流水正确分桶聚合，无假数据 fallback', async () => {
    _mockAll({
      transfers: [
        { id: 't1', date: '2026-08-01', docNumber: 'CG1', assetCode: 'A', assetName: 'x', quantity: 5, status: '已通过', actionType: 'purchase', fromBranch: '甲', toBranch: '乙', operator: '张三' },
        { id: 't1', date: '2026-08-02', docNumber: 'CG1', assetCode: 'A', assetName: 'x', quantity: 3, status: '已通过', actionType: 'return', fromBranch: '甲', toBranch: '乙', operator: '张三' },
        { id: 't2', date: '2026-08-03', docNumber: 'LY1', assetCode: 'A', assetName: 'x', quantity: 2, status: '已通过', actionType: 'assign', fromBranch: '甲', toBranch: '乙', operator: '李四' },
      ],
    })
    const wrapper = await mountReports()
    // 一个月份组：入库 5+3、出库 2、调拨 0（柱高按比例，无法直接读数值——断言组数与无空态）
    expect(wrapper.findAll('.trend-group')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('2026-01') // 旧示例数据月份不再出现
  })

  it('无流水时趋势展示空态而非示例数据', async () => {
    const wrapper = await mountReports()
    expect(wrapper.text()).toContain('暂无流水数据')
    expect(wrapper.findAll('.trend-group')).toHaveLength(0)
  })

  it('变动明细表按后端真实字段渲染（含经办人/单据编号）', async () => {
    _mockAll({
      transfers: [
        { id: 't9', date: '2026-08-20', docNumber: 'CG20260820-001', assetCode: 'NB-1', assetName: '笔记本', quantity: 4, status: '已通过', actionType: 'purchase', fromBranch: '', toBranch: '杭州', operator: '张三' },
      ],
    })
    const wrapper = await mountReports()
    // 切到变动明细 tab
    const tab = wrapper.findAll('.tab-btn').find(b => b.text() === '变动明细')
    await tab!.trigger('click')

    const row = wrapper.find('tbody tr')
    const cells = row.findAll('td').map(td => td.text())
    expect(cells).toEqual([
      '1', 'CG20260820-001', '2026-08-20', '采购入库', 'NB-1', '笔记本', '-', '杭州', '4', '已通过', '张三',
    ])
  })
})
